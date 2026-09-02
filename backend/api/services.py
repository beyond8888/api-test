import asyncio
import base64
import io
import logging
import os
import ssl
import time
from contextlib import suppress
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from .curl_parser.parser import CurlParser
from .ssrf import UnsafeUrlError, assert_safe_redirect, assert_safe_target

logger = logging.getLogger(__name__)

STRIP_REQUEST_HEADERS = {
    'host', 'origin', 'referer', 'connection', 'accept-encoding',
}
STRIP_RESPONSE_HEADERS = {
    'transfer-encoding', 'content-encoding', 'connection',
}

# Hard cap on the response body we buffer in memory (prevents OOM on huge
# responses / malicious payloads). Bodies larger than this are truncated.
MAX_BODY_BYTES = 5 * 1024 * 1024
# Maximum number of redirect hops we will follow (each re-validated for SSRF).
MAX_REDIRECTS = 5

# ── Proxy timeout / concurrency guards ────────────────────────────────────────
# Hard ceiling on the user-supplied timeout — a single slow upstream must never
# be allowed to tie up a worker indefinitely.
MAX_PROXY_TIMEOUT = int(os.environ.get('PROXY_MAX_TIMEOUT', '60'))
# Split timeout so a *connection* stall fails fast (5s) while a slow-but-alive
# upstream can still stream for up to MAX_PROXY_TIMEOUT seconds on the read side.
PROXY_CONNECT_TIMEOUT = int(os.environ.get('PROXY_CONNECT_TIMEOUT', '5'))
# Cap the number of in-flight proxy requests per worker process. Without this a
# handful of slow targets could occupy every event-loop slot and starve the rest
# of the app (the proxy is the only path that talks to arbitrary external hosts).
#
# NOTE: This is a **per-process** semaphore. Under multi-worker Uvicorn
# (--workers N) the global in-flight cap is N × PROXY_MAX_CONCURRENCY, not
# PROXY_MAX_CONCURRENCY itself. The cross-worker safety net is the `proxy`
# DRF throttle scope (60/min per user, see DEFAULT_THROTTLE_RATES in settings),
# which — when backed by a shared cache (Redis) — is enforced globally.
PROXY_MAX_CONCURRENCY = int(os.environ.get('PROXY_MAX_CONCURRENCY', '20'))
_PROXY_SEM = asyncio.Semaphore(PROXY_MAX_CONCURRENCY)


class ProxyService:
    """Async service that forwards HTTP requests server-side, bypassing CORS.

    Uses httpx (async) so a single event loop can serve many in-flight proxy
    requests concurrently — unlike the old blocking `requests` call, which tied
    up a whole worker thread for the full (up-to-60s) duration.
    """

    def __init__(self, url: str, method: str = 'GET', headers: dict | None = None,
                 query_params: dict | None = None,
                 body: str = '', body_type: str = '', form_fields: dict | None = None,
                 files_payload: list | None = None, timeout: int = 30):
        # assert_safe_target validates scheme + resolves/blocks unsafe hosts and
        # returns the pre-validated IP to connect to (pinning defeats DNS
        # rebinding — httpx would otherwise re-resolve the hostname on connect).
        self.url, _, self.resolved_ip = assert_safe_target(
            self._merge_query_params(url, query_params or {})
        )
        self.method = method.upper()
        self.headers = headers or {}
        self.body = body
        self.body_type = body_type
        self.form_fields = form_fields or {}
        self.files_payload = files_payload or []
        # Split timeout: connect must fail fast (bounded by PROXY_CONNECT_TIMEOUT),
        # read may run up to the user-supplied value but never past MAX_PROXY_TIMEOUT.
        self.timeout = min(timeout, MAX_PROXY_TIMEOUT)
        self._connect_timeout = PROXY_CONNECT_TIMEOUT
        self._read_timeout = self.timeout

    @staticmethod
    def _merge_query_params(url: str, params: dict) -> str:
        """Append query params dict to URL, preserving existing query string."""
        if not params:
            return url
        parsed = urlparse(url)
        existing = parse_qs(parsed.query, keep_blank_values=True)
        # Flatten existing (parse_qs returns lists) and merge new params
        flat = {k: v[0] if v else '' for k, v in existing.items()}
        flat.update(params)
        new_query = urlencode(flat)
        return urlunparse(parsed._replace(query=new_query))

    async def execute(self) -> dict:
        """Execute the proxied request and return a unified result dict.

        Returns a dict with keys: status, statusText, headers, body, size, timing
        On errors also includes: error
        """
        # Bound the number of concurrently in-flight proxy requests per worker so
        # a few slow upstreams cannot starve the rest of the app.
        async with _PROXY_SEM:
            return await self._execute_locked()

    async def _execute_locked(self) -> dict:
        t0 = time.perf_counter()
        current_url = self.url
        clean_headers = self._clean_request_headers()
        if self.body_type == 'multipart':
            clean_headers.pop('Content-Type', None)
            clean_headers.pop('content-type', None)

        # follow_redirects=False so we can re-validate every redirect target
        # against the SSRF policy.
        # trust_env=False prevents HTTP(S)_PROXY environment variables from
        # routing traffic through an untrusted proxy; verify=True enforces TLS.
        async with self._make_client(current_url) as client:
            for _ in range(MAX_REDIRECTS + 1):
                pinned_url, pinned_headers = self._pin_url(current_url)
                headers = {**clean_headers, **pinned_headers}
                try:
                    req = self._build_request(client, pinned_url, headers)
                    resp = await client.send(req)
                except UnsafeUrlError as e:
                    return self._error_result(t0, f'Blocked by proxy policy: {e.messages[0] if e.messages else e}', 'BLOCKED')
                except httpx.TimeoutException:
                    return self._error_result(t0, f'Request timed out after {self.timeout}s', 'TIMEOUT')
                except httpx.ConnectError as e:
                    return self._error_result(t0, f'Connection failed: {e}', 'CONNECT')
                except httpx.HTTPError as e:
                    return self._error_result(t0, str(e), 'HTTP')

                if resp.is_redirect and resp.headers.get('location'):
                    try:
                        current_url, _, self.resolved_ip = assert_safe_redirect(
                            current_url, resp.headers['location']
                        )
                    except UnsafeUrlError as e:
                        return self._error_result(t0, f'Redirect blocked by proxy policy: {e.messages[0] if e.messages else e}', 'BLOCKED')
                    continue

                body, truncated = await self._read_body(resp)
                elapsed_ms = round((time.perf_counter() - t0) * 1000)
                return {
                    'status': resp.status_code,
                    'statusText': resp.reason_phrase,
                    'headers': self._clean_response_headers(resp.headers),
                    'body': body,
                    'size': len(body),
                    'timing': elapsed_ms,
                    'truncated': truncated,
                }

        return self._error_result(t0, f'Too many redirects (> {MAX_REDIRECTS})', 'REDIRECT_LIMIT')

    # ---- private ----

    def _pin_url(self, url: str) -> tuple[str, dict[str, str]]:
        """Rewrite ``url`` to connect via the pre-validated IP.

        Prevents DNS rebinding: instead of letting httpx re-resolve the hostname
        at connect time (a TOCTOU window that could point at an internal host),
        we connect straight to the already-checked IP. The original hostname is
        carried in the ``Host`` header so virtual-host routing still works.
        """
        parsed = urlparse(url)
        scheme = (parsed.scheme or 'http').lower()
        host = parsed.hostname or ''
        port = parsed.port or (443 if scheme == 'https' else 80)
        ip = self.resolved_ip or host
        if ':' in ip:  # IPv6 literal needs brackets in the authority
            netloc = f'[{ip}]:{port}'
        else:
            netloc = f'{ip}:{port}'
        pinned = urlunparse(parsed._replace(netloc=netloc))
        headers = {'Host': host} if host else {}
        return pinned, headers

    def _make_client(self, url: str) -> httpx.AsyncClient:
        """Build an AsyncClient; for HTTPS keep CA verification but skip
        hostname/SAN matching since we connect by IP (the egress firewall remains
        the primary rebinding defense — see ssrf.py module docstring)."""
        kwargs: dict = {
            'follow_redirects': False,
            'timeout': httpx.Timeout(
                connect=self._connect_timeout,
                read=self._read_timeout,
                write=self._read_timeout,
                pool=self._connect_timeout,
            ),
            'trust_env': False,
        }
        if (urlparse(url).scheme or 'http').lower() == 'https':
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            kwargs['verify'] = ctx
        return httpx.AsyncClient(**kwargs)

    def _clean_request_headers(self) -> dict:
        return {k: v for k, v in self.headers.items()
                if k.lower() not in STRIP_REQUEST_HEADERS}

    @staticmethod
    def _clean_response_headers(headers) -> dict:
        return {k: v for k, v in headers.items()
                if k.lower() not in STRIP_RESPONSE_HEADERS}

    def _build_request(self, client: httpx.AsyncClient, url: str, headers: dict):
        if self.body_type == 'multipart':
            files_param = []
            for f in self.files_payload:
                raw = base64.b64decode(f.get('content_base64', '') or '')
                files_param.append((
                    f.get('field', f.get('name', 'file')),
                    (f.get('name', 'file'), io.BytesIO(raw), f.get('type', '')),
                ))
            return client.build_request(
                self.method, url,
                headers=headers,
                data=self.form_fields, files=files_param,
            )
        data = self.body if self.method not in ('GET', 'HEAD') else None
        return client.build_request(self.method, url, headers=headers, data=data)

    async def _read_body(self, resp: httpx.Response) -> tuple[str, bool]:
        """Stream the response body, capped at MAX_BODY_BYTES.

        Returns (body_text, truncated). Excess bytes are drained so the
        connection closes cleanly, but never buffered in full.
        """
        chunks: list[bytes] = []
        total = 0
        truncated = False
        async for chunk in resp.aiter_bytes(chunk_size=65536):
            total += len(chunk)
            if total > MAX_BODY_BYTES:
                truncated = True
                # Drain remaining bytes without buffering them.
                async for _ in resp.aiter_bytes(chunk_size=65536):
                    pass
                break
            chunks.append(chunk)
        return b''.join(chunks).decode('utf-8', errors='replace'), truncated

    @staticmethod
    def _error_result(t0: float, message: str, code: str = 'ERROR') -> dict:
        return {
            'status': 0,
            'statusText': 'Error',
            'headers': {},
            'body': '',
            'size': 0,
            'timing': round((time.perf_counter() - t0) * 1000),
            'error': message,
            'error_code': code,
        }


class KafkaService:
    """Produce (send) a single message to a Kafka topic via the backend.

    The connection is performed server-side so the browser is never exposed to
    broker credentials. confluent-kafka is imported lazily inside execute() so a
    missing dependency only fails the send call, not Django startup.
    """

    def __init__(self, broker: str, topic: str, value: str, key: str | None = None,
                 headers: dict | None = None, timeout: int = 10):
        self.broker = broker
        self.topic = topic
        self.value = value
        self.key = key or None
        self.headers = headers or {}
        self.timeout = min(timeout, 60)

    def execute(self) -> dict:
        """Send the message and return a unified result dict.

        Success: {topic, partition, offset}
        Failure: {error}
        """
        try:
            from confluent_kafka import Producer
        except ImportError:
            return {'error': 'confluent-kafka is not installed on the server'}

        try:
            producer = Producer({
                'bootstrap.servers': self.broker,
                'message.timeout.ms': int(self.timeout * 1000),
                'delivery.timeout.ms': int(self.timeout * 1000),
            })
        except Exception as e:
            logger.exception('Failed to create Kafka Producer for %s', self.broker)
            return {'error': f'Failed to connect to broker: {e}'}

        delivered: dict = {}
        result: dict | None = None

        def delivery_cb(err, msg):
            if err:
                delivered['error'] = str(err)
            else:
                delivered['topic'] = msg.topic()
                delivered['partition'] = msg.partition()
                delivered['offset'] = msg.offset()

        try:
            kafka_headers = [
                (k, v.encode('utf-8')) for k, v in self.headers.items() if k is not None
            ]
            producer.produce(
                self.topic,
                key=self.key.encode('utf-8') if self.key else None,
                value=self.value.encode('utf-8'),
                headers=kafka_headers,
                on_delivery=delivery_cb,
            )
            remaining = producer.flush(self.timeout)
            if remaining and remaining > 0:
                result = {'error': f'Flush timed out, {remaining} message(s) not delivered'}
            elif delivered.get('error'):
                result = {'error': delivered['error']}
            else:
                result = {
                    'topic': delivered['topic'],
                    'partition': delivered['partition'],
                    'offset': delivered['offset'],
                }
        except Exception as e:
            logger.exception('Kafka send failed to topic %s', self.topic)
            result = {'error': str(e)}
        finally:
            with suppress(Exception):
                producer.flush(0)

        return result or {'error': 'Unknown Kafka error'}


class RocketMQService:
    """Send a message to an Alibaba Cloud RocketMQ 5.x instance over gRPC.

    Uses the pure-Python ``rocketmq-client`` protobuf/gRPC stubs (no native
    library needed). The blocking gRPC round-trip runs inside ``asyncio.to_thread``
    so it never ties up the event loop. Credentials stay server-side.

    Implements the 5.x gRPC handshake:
      1. QueryRoute  -> resolve broker endpoints for the topic
      2. SendMessage -> deliver the message (with Ak/Sk signature in metadata)
    """

    def __init__(self, endpoint: str, instance_id: str, access_key: str,
                 secret_key: str, topic: str, body: str,
                 message_type: str = 'NORMAL', message_group: str = '',
                 delay_time: int = 0, tag: str = '', keys: list | None = None):
        self.endpoint = endpoint
        self.instance_id = instance_id
        self.access_key = access_key
        self.secret_key = secret_key
        self.topic = topic
        self.body = body
        self.message_type = message_type
        self.message_group = message_group
        self.delay_time = delay_time
        self.tag = tag
        self.keys = keys or []

    def execute(self) -> dict:
        """Send the message and return a unified result dict.

        Success: {message_id, topic}
        Failure: {error}
        """
        try:
            import sys, types, hashlib, hmac, base64 as _b64
            import time as _time
            import grpc

            # The protobuf package ships its modules under rocketmq_client/apache
            # but imports them as top-level `apache`; expose it on sys.modules.
            pkg_dir = None
            import rocketmq_client
            _base = rocketmq_client.__path__[0]
            apache_dir = _base if _base.endswith('apache') else (
                _base.rstrip('/') + '/apache')
            if 'apache' not in sys.modules:
                _m = types.ModuleType('apache')
                _m.__path__ = [apache_dir]
                sys.modules['apache'] = _m
            from apache.rocketmq.v2 import service_pb2, service_pb2_grpc, definition_pb2
            from apache.rocketmq.v2.definition_pb2 import Address, AddressScheme
        except ImportError as e:
            logger.exception('RocketMQ 5.x dependencies missing')
            return {'error': f'RocketMQ 5.x client is not installed on the server: {e}'}

        try:
            # --- build auth metadata (Alibaba Cloud 5.x Ak/Sk signature) ---
            # 5.x gRPC auth: metadata key `authorization` with value
            #   'algorithm=AkSk&signature=<base64(HMAC-SHA1(secret, date))>&ak=<accessKey>&date=<date>'
            date_str = _time.strftime('%a, %d %b %Y %H:%M:%S GMT', _time.gmtime())
            sign_body = f'{date_str}'.encode('utf-8')
            signature = _b64.b64encode(
                hmac.new(self.secret_key.encode('utf-8'), sign_body, hashlib.sha1).digest()
            ).decode('ascii')
            authorization = (
                f'algorithm=AkSk&'
                f'signature={signature}&'
                f'ak={self.access_key}&'
                f'date={date_str}'
            )
            metadata = [('authorization', authorization)]

            # --- channel (TLS, no host verification needed for aliyuncs endpoint) ---
            channel = grpc.secure_channel(
                self.endpoint, grpc.ssl_channel_credentials()
            )
            stub = service_pb2_grpc.MessagingServiceStub(channel)

            # --- 1. QueryRoute ---
            topic_resource = definition_pb2.Resource(
                resource_namespace=self.instance_id,
                name=self.topic,
            )
            host = self.endpoint.split(':')[0]
            port = int(self.endpoint.split(':')[1]) if ':' in self.endpoint else 8080
            route_req = service_pb2.QueryRouteRequest(
                topic=topic_resource,
                endpoints=definition_pb2.Endpoints(
                    scheme=AddressScheme.IPv4,
                    addresses=[Address(host=host, port=port)],
                ),
            )
            route_resp = stub.QueryRoute(route_req, metadata=metadata, timeout=10)
            if not route_resp.message_queues:
                channel.close()
                return {'error': 'QueryRoute returned no brokers for the topic'}

            # Pick first broker endpoint for SendMessage.
            mq = route_resp.message_queues[0]
            broker_endpoints = mq.broker.endpoints
            broker_target = f'{broker_endpoints.addresses[0].host}:{broker_endpoints.addresses[0].port}'
            broker_channel = grpc.secure_channel(
                broker_target, grpc.ssl_channel_credentials()
            )
            broker_stub = service_pb2_grpc.MessagingServiceStub(broker_channel)

            # --- 2. build & send message ---
            from google.protobuf.timestamp_pb2 import Timestamp
            sys_props = definition_pb2.SystemProperties(
                message_type=getattr(definition_pb2, self.message_type),
                body_encoding=definition_pb2.ENCODING_AUTO,
            )
            if self.tag:
                sys_props.tag = self.tag
            for k in self.keys:
                sys_props.keys.append(k)
            if self.message_type == 'FIFO' and self.message_group:
                sys_props.message_group = self.message_group
            if self.message_type == 'DELAY' and self.delay_time > 0:
                delivery = Timestamp()
                delivery.FromSeconds(int(_time.time()) + self.delay_time)
                sys_props.delivery_timestamp.CopyFrom(delivery)

            msg = definition_pb2.Message(
                topic=topic_resource,
                body=self.body.encode('utf-8'),
                system_properties=sys_props,
            )
            send_req = service_pb2.SendMessageRequest(messages=[msg])
            send_resp = broker_stub.SendMessage(send_req, metadata=metadata, timeout=10)

            message_id = ''
            if send_resp.entries:
                message_id = send_resp.entries[0].message_id
            broker_channel.close()
            channel.close()
            if not message_id:
                return {'error': 'SendMessage returned empty result'}
            return {'message_id': message_id, 'topic': self.topic}
        except Exception as e:
            logger.exception('RocketMQ 5.x send failed to topic %s', self.topic)
            return {'error': str(e)}


class CurlParseService:
    """Parse curl command strings into structured request configs.

    Stateless by design: parsing is a one-shot conversion, so nothing is
    persisted. Raw curl commands routinely carry credentials
    (Authorization / Cookie headers), and storing them served no reader —
    the old CurlParseRecord audit table had no API surface at all.
    """

    @staticmethod
    def parse(raw_curl: str) -> dict:
        """Parse a curl command into a structured result dict.

        Raises CurlParseError on invalid input.
        """
        parser = CurlParser(raw_curl)
        ast = parser.parse()

        return {
            'method': ast['method'],
            'url': ast['url'],
            'headers': ast['headers'],
            'query_params': ast['query_params'],
            'cookies': ast['cookies'] or {},
            'body': {
                'type': ast['body_type'] or 'none',
                'content': ast['raw_body'] or '',
                'form_fields': [
                    {'field': k, 'value': v} for k, v in (ast['form_fields'] or {}).items()
                ],
            },
            'body_type': ast['body_type'] or 'none',
        }
