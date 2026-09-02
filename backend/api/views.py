import asyncio
import logging
from datetime import timedelta

from django.db import connections, transaction
from django.db.models import Subquery
from django.db.utils import OperationalError
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import AuthenticationFailed, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apitester.api_response import CODE_UNAUTHORIZED, fail, server_error, success
from apitester.crud_mixin import OwnerScopedMixin, UnifiedCRUDMixin
from common.pagination import StandardResultsSetPagination
from common.utils import first_error

from .curl_parser.exceptions import CurlParseError
from .models import Collection, Environment, HistoryEntry
from .serializers import (
    CollectionSerializer,
    CurlParseRequestSerializer,
    EnvironmentSerializer,
    HistoryEntrySerializer,
    KafkaSendSerializer,
    ProxyRequestSerializer,
    RegisterSerializer,
    RocketMQSendSerializer,
)
from .services import CurlParseService, KafkaService, ProxyService, RocketMQService
from .ssrf import UnsafeUrlError

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  Health (public — no auth)
# ═══════════════════════════════════════════════════════════════════

class HealthView(APIView):
    """GET /api/v1/health/ — liveness + DB check."""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        db_ok = True
        try:
            connections['default'].cursor()
        except OperationalError:
            db_ok = False
        return success({
            'status': 'ok' if db_ok else 'degraded',
            'database': 'ok' if db_ok else 'error',
        })


# ═══════════════════════════════════════════════════════════════════
#  Auth
# ═══════════════════════════════════════════════════════════════════

class RegisterView(APIView):
    """POST /api/v1/auth/register/ — create a new user account."""
    permission_classes = []
    authentication_classes = []
    throttle_scope = 'auth_register'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(first_error(serializer.errors))

        user = serializer.save()
        return success({
            'id': user.id,
            'username': user.username,
        }, message='Registration successful')


class MeView(APIView):
    """GET /api/v1/auth/me/ — get current authenticated user."""

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return fail('Not authenticated', status=401)
        return success({
            'id': request.user.id,
            'username': request.user.username,
        })


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — wrap simplejwt's raw {access,refresh} in the
    unified envelope so every endpoint speaks the same contract. Invalid
    credentials are surfaced as a unified { code, message } envelope (instead of
    the raw DRF 401 detail) so the frontend can show a friendly message."""
    throttle_scope = 'auth_login'

    def post(self, request, *args, **kwargs):
        try:
            resp = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            return fail('用户名或密码错误', code=CODE_UNAUTHORIZED, status=401)
        return success(resp.data)


class RefreshView(TokenRefreshView):
    """POST /api/v1/auth/refresh/ — same envelope wrapping as LoginView."""
    throttle_scope = 'auth_refresh'

    def post(self, request, *args, **kwargs):
        try:
            resp = super().post(request, *args, **kwargs)
        except TokenError:
            return fail('登录已过期，请重新登录', code=CODE_UNAUTHORIZED, status=401)
        return success(resp.data)


# ═══════════════════════════════════════════════════════════════════
#  Curl Parse + Proxy (authenticated)
# ═══════════════════════════════════════════════════════════════════

class CurlParseView(APIView):
    """POST /api/v1/parse-curl/ — parse a curl command string."""
    throttle_scope = 'curl'

    def post(self, request):
        serializer = CurlParseRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(first_error(serializer.errors))

        raw_curl = serializer.validated_data['curl_command']

        try:
            result = CurlParseService.parse(raw_curl)
        except CurlParseError as e:
            return fail(f'Parse error: {e}')

        return success(result)


class ProxyView(APIView):
    """POST /api/v1/proxy/ — forward HTTP request via backend.

    The request is executed by the async `ProxyService.execute()` (httpx async
    client). To stay correct under BOTH runtimes this view is a plain sync method
    that drives the coroutine via a small `_run` helper:
      * ASGI (uvicorn) — there is already a running event loop, so we await inside
        it and keep the true concurrency benefit (the loop serves other requests
        while a slow upstream call is in flight).
      * WSGI (runserver / gunicorn sync) — no loop is running, so we spin one up
        with `asyncio.run`. It still works, just occupies that worker for the
        call (same as the old behaviour).

    This replaces the earlier native `async def` view, which crashed under WSGI
    because DRF's sync request handler never awaited the coroutine.
    """

    throttle_scope = 'proxy'

    def post(self, request):
        serializer = ProxyRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(first_error(serializer.errors))

        valid = serializer.validated_data
        try:
            service = ProxyService(
                url=valid['url'],
                method=valid['method'],
                headers=valid['headers'],
                query_params=valid.get('query_params', {}),
                body=valid['body'],
                body_type=valid['body_type'],
                form_fields=valid['form_fields'],
                files_payload=valid['files'],
                timeout=valid['timeout'],
            )
        except UnsafeUrlError as e:
            return server_error(str(e.messages[0] if e.messages else e), status=400)

        try:
            result = _run(service.execute())
        except Exception as exc:  # noqa: BLE001
            logger.exception('Proxy execution failed')
            return server_error(f'Proxy error: {exc}')

        if result.get('error'):
            # Map to HTTP semantics via a structured error code (not string matching):
            #   TIMEOUT -> 504, BLOCKED (policy) -> 400, everything else -> 502.
            code = result.get('error_code')
            if code == 'TIMEOUT':
                status = 504
            elif code == 'BLOCKED':
                status = 400
            else:
                status = 502
            return server_error(result['error'], data=result, status=status)

        return success(result)


class KafkaSendView(APIView):
    """POST /api/v1/kafka/send/ — produce a single message to a Kafka topic.

    `KafkaService.execute()` blocks on the producer flush (up to 60s), so under
    ASGI it is offloaded to a worker thread via `asyncio.to_thread` to keep the
    event loop responsive. The view itself is a plain sync method (see
    `ProxyView` for the rationale) and drives the coroutine through `_run`, so it
    works identically under WSGI.
    """
    throttle_scope = 'kafka'

    def post(self, request):
        serializer = KafkaSendSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(first_error(serializer.errors))

        valid = serializer.validated_data
        service = KafkaService(
            broker=valid['broker'],
            topic=valid['topic'],
            value=valid['value'],
            key=valid.get('key') or None,
            headers=valid.get('headers', {}),
            timeout=valid.get('timeout', 10),
        )
        result = _run(_kafka_execute(service))

        if result.get('error'):
            return server_error(result['error'], data=result)

        return success(result)


async def _kafka_execute(service: KafkaService) -> dict:
    """Wrap the blocking `KafkaService.execute` so it yields to the event loop
    (offloaded to a thread) under ASGI, while remaining callable via `_run`."""
    return await asyncio.to_thread(service.execute)


class RocketMQSendView(APIView):
    """POST /api/v1/rocketmq/send/ — send a single message to a RocketMQ 5.x topic.

    Mirrors `KafkaSendView`: the blocking gRPC round-trip is offloaded to a
    thread via `asyncio.to_thread` so the event loop stays responsive. Credentials
    (access key / secret key) never leave the server.
    """
    throttle_scope = 'rocketmq'

    def post(self, request):
        serializer = RocketMQSendSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(first_error(serializer.errors))

        valid = serializer.validated_data
        service = RocketMQService(
            endpoint=valid['endpoint'],
            instance_id=valid['instance_id'],
            access_key=valid['access_key'],
            secret_key=valid['secret_key'],
            topic=valid['topic'],
            body=valid['body'],
            message_type=valid.get('message_type', 'NORMAL'),
            message_group=valid.get('message_group', '') or '',
            delay_time=valid.get('delay_time', 0) or 0,
            tag=valid.get('tag', '') or '',
            keys=valid.get('keys', []) or [],
        )
        result = _run(_rocketmq_execute(service))

        if result.get('error'):
            return server_error(result['error'], data=result)

        return success(result)


async def _rocketmq_execute(service: RocketMQService) -> dict:
    """Offload the blocking `RocketMQService.execute` (gRPC) to a worker thread."""
    return await asyncio.to_thread(service.execute)


def _run(coro):
    """Drive an async coroutine to completion regardless of runtime.

    The view methods are plain sync methods (so DRF's sync request handler
    always gets a real `HttpResponse`). We just run the coroutine to completion
    on a dedicated event loop. Under WSGI this is a throwaway loop in the worker
    thread; under ASGI DRF wraps the sync view in `sync_to_async`, so each call
    still executes correctly. The async `ProxyService`/`KafkaService` keep their
    real httpx/thread concurrency internally.
    """
    return asyncio.run(coro)


# ═════════════════════════════════════════════════════════════════
#  Collection CRUD
# ═══════════════════════════════════════════════════════════════════

class CollectionViewSet(OwnerScopedMixin, UnifiedCRUDMixin, viewsets.ModelViewSet):
    """CRUD for request collections — user-scoped."""
    queryset = Collection.objects.all()
    lookup_field = 'pk'
    throttle_scope = 'collections'
    pagination_class = StandardResultsSetPagination

    serializer_class = CollectionSerializer


# ═══════════════════════════════════════════════════════════════════
#  Environment CRUD
# ═══════════════════════════════════════════════════════════════════

class EnvironmentViewSet(OwnerScopedMixin, UnifiedCRUDMixin, viewsets.ModelViewSet):
    """CRUD for environments — user-scoped, auto-manages is_active."""
    queryset = Environment.objects.all()
    serializer_class = EnvironmentSerializer
    throttle_scope = 'environments'
    pagination_class = StandardResultsSetPagination

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """POST /api/v1/environments/{id}/activate/ — set as active env."""
        env = self.get_object()
        # Deactivate all others, activate this one. Lock the owner's rows so two
        # concurrent activations cannot briefly leave multiple active environments.
        with transaction.atomic():
            Environment.objects.filter(owner=request.user).select_for_update().update(is_active=False)
            env.is_active = True
            env.save(update_fields=['is_active'])
        return success(EnvironmentSerializer(env).data)

    def destroy(self, request, *args, **kwargs):
        """DELETE — prevent deleting the active environment without deactivating."""
        instance = self.get_object()
        if instance.is_active:
            instance.is_active = False
            instance.save(update_fields=['is_active'])
        super().destroy(request, *args, **kwargs)
        return success(None, message='Environment deleted')


# ═══════════════════════════════════════════════════════════════════
#  History
# ═══════════════════════════════════════════════════════════════════

MAX_HISTORY_ENTRIES = 300
MAX_HISTORY_AGE_DAYS = 90


class HistoryViewSet(OwnerScopedMixin, UnifiedCRUDMixin, viewsets.ModelViewSet):
    """List + Create + Delete for request history — user-scoped, newest first."""
    queryset = HistoryEntry.objects.all()
    serializer_class = HistoryEntrySerializer
    pagination_class = StandardResultsSetPagination
    throttle_scope = 'history'

    def perform_create(self, serializer):
        """Persist the entry and clean up excess / stale records:
        - Keep only the most recent MAX_HISTORY_ENTRIES per user (FIFO).
        - Delete entries older than MAX_HISTORY_AGE_DAYS.
        Both run inline on every write — no separate cron required."""
        entry = serializer.save(owner=self.request.user)
        owner = self.request.user

        # 1) Time-based: delete entries older than N days
        cutoff = timezone.now() - timedelta(days=MAX_HISTORY_AGE_DAYS)
        HistoryEntry.objects.filter(owner=owner, timestamp__lt=cutoff).delete()

        # 2) Count cap: keep only the latest MAX_HISTORY_ENTRIES
        keeper_ids = (
            HistoryEntry.objects.filter(owner=owner)
            .order_by('-timestamp')
            .values('id')[:MAX_HISTORY_ENTRIES]
        )
        HistoryEntry.objects.filter(owner=owner).exclude(
            id__in=Subquery(keeper_ids)
        ).delete()

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """DELETE /api/v1/history/clear/ — delete all history entries."""
        deleted, _ = HistoryEntry.objects.filter(owner=request.user).delete()
        return success({'deleted': deleted})
