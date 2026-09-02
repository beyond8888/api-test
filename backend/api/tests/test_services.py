"""
Tests for api/services.py — ProxyService (async, httpx-based).
"""
import asyncio
from unittest.mock import MagicMock, patch

import httpx
from django.test import SimpleTestCase


def run(coro):
    return asyncio.run(coro)


class FakeResponse:
    def __init__(self, status_code=200, reason_phrase='OK', headers=None,
                 body=b'', is_redirect=False):
        self.status_code = status_code
        self.reason_phrase = reason_phrase
        self.headers = headers or {}
        self._body = body
        self.is_redirect = is_redirect

    async def aiter_bytes(self, chunk_size=65536):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]


class FakeAsyncClient:
    """Minimal stand-in for httpx.AsyncClient used by ProxyService.execute."""

    def __init__(self, response=None, raise_exc=None, **kwargs):
        self._response = response
        self._raise = raise_exc
        self.last_req = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def build_request(self, method, url, headers=None, data=None, files=None):
        self.last_req = {
            'method': method, 'url': url,
            'headers': headers, 'data': data, 'files': files,
        }
        return MagicMock()

    async def send(self, req, **kwargs):
        if self._raise is not None:
            raise self._raise
        return self._response


class ProxyServiceInitTests(SimpleTestCase):
    """Test constructor defaults and parameter handling."""

    def test_default_values(self):
        from api.services import ProxyService as PS
        self.assertTrue(hasattr(PS, 'execute'))

    def test_timeout_capped_at_60(self):
        from api.services import ProxyService
        with patch('api.services.assert_safe_target', lambda u: (u, [], None)):
            svc = ProxyService('http://example.com', timeout=999)
        self.assertEqual(svc.timeout, 60)

    def test_method_upper(self):
        from api.services import ProxyService
        with patch('api.services.assert_safe_target', lambda u: (u, [], None)):
            svc = ProxyService('http://example.com', method='post')
        self.assertEqual(svc.method, 'POST')


class ProxyServiceCleanHeadersTests(SimpleTestCase):
    """Test request/response header cleaning."""

    def test_strips_request_headers(self):
        from api.services import ProxyService
        with patch('api.services.assert_safe_target', lambda u: (u, [], None)):
            svc = ProxyService('http://example.com', headers={
                'Authorization': 'Bearer x',
                'Host': 'evil.com',
                'Referer': 'http://spam.com',
                'Content-Type': 'application/json',
            })
        cleaned = svc._clean_request_headers()
        self.assertIn('Authorization', cleaned)
        self.assertIn('Content-Type', cleaned)
        self.assertNotIn('Host', cleaned)
        self.assertNotIn('Referer', cleaned)

    def test_clean_response_headers(self):
        from api.services import ProxyService
        result = ProxyService._clean_response_headers({
            'Content-Type': 'application/json',
            'Transfer-Encoding': 'chunked',
            'Connection': 'keep-alive',
        })
        self.assertIn('Content-Type', result)
        self.assertNotIn('Transfer-Encoding', result)
        self.assertNotIn('Connection', result)


class ProxyServiceExecuteTests(SimpleTestCase):
    """Test async execute() with mocked httpx.AsyncClient."""

    def test_execute_get_success(self):
        from api.services import ProxyService
        resp = FakeResponse(
            status_code=200, reason_phrase='OK',
            headers={'Content-Type': 'application/json'},
            body=b'{"ok": true}',
        )
        fake = FakeAsyncClient(response=resp)
        with patch('api.services.assert_safe_target', lambda u: (u, [], None)), \
                patch('api.services.httpx.AsyncClient', return_value=fake):
            result = run(ProxyService('http://example.com/api', method='GET',
                                       headers={'Accept': 'application/json'}).execute())

        self.assertEqual(result['status'], 200)
        self.assertEqual(result['statusText'], 'OK')
        self.assertEqual(result['body'], '{"ok": true}')
        self.assertEqual(result['size'], len('{"ok": true}'))
        self.assertGreaterEqual(result['timing'], 0)

    def test_execute_timeout(self):
        from api.services import ProxyService
        fake = FakeAsyncClient(raise_exc=httpx.TimeoutException('timed out'))
        with patch('api.services.assert_safe_target', lambda u: (u, [], None)), \
                patch('api.services.httpx.AsyncClient', return_value=fake):
            result = run(ProxyService('http://example.com', timeout=5).execute())
        self.assertEqual(result['status'], 0)
        self.assertIn('error', result)
        self.assertIn('timed out', result['error'].lower())

    def test_execute_connection_error(self):
        from api.services import ProxyService
        fake = FakeAsyncClient(raise_exc=httpx.ConnectError('Refused'))
        with patch('api.services.assert_safe_target', lambda u: (u, [], None)), \
                patch('api.services.httpx.AsyncClient', return_value=fake):
            result = run(ProxyService('http://down.example.com').execute())
        self.assertEqual(result['status'], 0)
        self.assertIn('error', result)
        self.assertIn('Connection failed', result['error'])

    def test_execute_post_with_body(self):
        from api.services import ProxyService
        resp = FakeResponse(status_code=201, reason_phrase='Created', headers={}, body=b'{"id": 1}')
        fake = FakeAsyncClient(response=resp)
        with patch('api.services.assert_safe_target', lambda u: (u, [], None)), \
                patch('api.services.httpx.AsyncClient', return_value=fake):
            result = run(ProxyService(
                'http://example.com/api', method='POST',
                body='{"name":"test"}', body_type='json',
                headers={'Content-Type': 'application/json'}).execute())
        self.assertEqual(result['status'], 201)
        self.assertEqual(fake.last_req['method'], 'POST')
        self.assertEqual(fake.last_req['data'], '{"name":"test"}')

    def test_execute_get_strips_body(self):
        from api.services import ProxyService
        resp = FakeResponse(status_code=200, reason_phrase='OK', headers={}, body=b'')
        fake = FakeAsyncClient(response=resp)
        with patch('api.services.assert_safe_target', lambda u: (u, [], None)), \
                patch('api.services.httpx.AsyncClient', return_value=fake):
            run(ProxyService('http://example.com', method='GET',
                              body='should-be-ignored').execute())
        self.assertIsNone(fake.last_req['data'])

    def test_execute_caps_body_size(self):
        from api.services import ProxyService
        # 6 MB body (> 5 MB cap) → truncated, body returned is capped.
        big = b'x' * (6 * 1024 * 1024)
        resp = FakeResponse(status_code=200, reason_phrase='OK', headers={}, body=big)
        fake = FakeAsyncClient(response=resp)
        with patch('api.services.assert_safe_target', lambda u: (u, [], None)), \
                patch('api.services.httpx.AsyncClient', return_value=fake):
            result = run(ProxyService('http://example.com/big').execute())
        self.assertTrue(result.get('truncated'))
        self.assertLessEqual(result['size'], 5 * 1024 * 1024 + 65536)
