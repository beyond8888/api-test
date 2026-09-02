"""
Mock views — CRUD management + mock serving endpoint.
"""
import logging
import time

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apitester.api_response import fail, server_error, success
from apitester.crud_mixin import OwnerScopedMixin, UnifiedCRUDMixin
from common.pagination import StandardResultsSetPagination

from .models import MockEndpoint
from .serializers import MockEndpointSerializer
from .services import MockRequest, execute_script, match_path

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  CRUD ViewSet (authenticated)
# ═══════════════════════════════════════════════════════════════════


class MockEndpointViewSet(OwnerScopedMixin, UnifiedCRUDMixin, viewsets.ModelViewSet):
    """CRUD for Mock endpoints — user-scoped, authenticated."""

    model_label = 'MockEndpoint'
    queryset = MockEndpoint.objects.all()
    serializer_class = MockEndpointSerializer
    throttle_scope = 'mock'
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'path']

    def get_serializer_class(self):
        # Create/update use the same serializer (owner is auto-set via
        # OwnerScopedMixin); delay_ms bounds are enforced by the serializer
        # and model validators.
        return MockEndpointSerializer

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """POST /api/v1/mock/endpoints/{id}/test/ — test-run a mock script."""
        endpoint = self.get_object()

        # Build a mock request from user-provided test params
        mock_req = MockRequest(
            method=endpoint.method,
            path=endpoint.path,
            query_params=request.data.get('query_params', {}),
            headers=request.data.get('headers', {}),
            body=request.data.get('body', ''),
            path_params=request.data.get('path_params', {}),
        )

        start = time.monotonic()
        result = execute_script(endpoint.python_script, mock_req)
        elapsed = (time.monotonic() - start) * 1000

        # Include error info in a way the frontend can display
        if result.get('status_code', 200) >= 500:
            logger.warning(
                'Mock test for endpoint %s returned status %d',
                endpoint.name, result.get('status_code'),
            )

        return success({
            'response': result,
            'timing_ms': round(elapsed, 1),
        })


# ═══════════════════════════════════════════════════════════════════
#  Mock Serve View (no auth — this is what callers hit)
# ═══════════════════════════════════════════════════════════════════


class MockServeView(APIView):
    """Serve mock responses — no authentication.

    Matches incoming requests against enabled MockEndpoint records
    and executes their Python scripts to generate dynamic responses.

    Note: path+method is globally unique (see MockEndpoint.unique_together),
    so a single enabled endpoint owns any given path — there is no
    cross-tenant path hijacking even though this endpoint is public.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'mock_serve'

    def _dispatch(self, request, mock_path: str):
        # Normalise the path
        mock_path = mock_path.strip('/')
        method = request.method.upper()

        if not mock_path:
            return fail('Mock path is required', status=400)

        # Find matching endpoints (path+method is globally unique, so no
        # cross-tenant hijacking is possible even on this public endpoint).
        candidates = MockEndpoint.objects.filter(enabled=True).order_by('-updated_at')

        for endpoint in candidates:
            if endpoint.method.upper() != method:
                continue

            path_params = match_path(endpoint.path, mock_path)
            if path_params is None:
                continue

            # ---- We have a match ----
            logger.info(
                'Mock match: [%s] %s -> endpoint #%s (%s)',
                method, mock_path, endpoint.id, endpoint.name,
            )

            # Simulate delay (hard-cap to avoid a single request hogging a
            # worker even if a bad delay_ms value slipped past validation).
            if endpoint.delay_ms > 0:
                delay = min(endpoint.delay_ms, 60_000) / 1000.0
                time.sleep(delay)

            # Build request context for the script (unified path)
            mock_req = MockRequest.from_django(request, mock_path, path_params)

            # Execute the script
            result = execute_script(endpoint.python_script, mock_req)

            # Build response
            status = result.get('status_code', 200)
            resp_headers = result.get('headers', {})
            body = result.get('body', '')

            from django.http import HttpResponse
            response = HttpResponse(
                body,
                status=status,
                content_type=resp_headers.pop('Content-Type', 'application/json'),
            )
            for key, val in resp_headers.items():
                response[key] = val
            response['X-Mock-Endpoint'] = str(endpoint.id)
            response['X-Mock-Name'] = endpoint.name
            return response

        # No match found
        return fail(
            f'No enabled mock endpoint matches [{method}] {mock_path}',
            status=404,
        )

    def get(self, request, mock_path=''):
        return self._dispatch(request, mock_path)

    def post(self, request, mock_path=''):
        return self._dispatch(request, mock_path)

    def put(self, request, mock_path=''):
        return self._dispatch(request, mock_path)

    def patch(self, request, mock_path=''):
        return self._dispatch(request, mock_path)

    def delete(self, request, mock_path=''):
        return self._dispatch(request, mock_path)

    def head(self, request, mock_path=''):
        return self._dispatch(request, mock_path)

    def options(self, request, mock_path=''):
        return self._dispatch(request, mock_path)
