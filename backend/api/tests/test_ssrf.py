"""Security-critical edge-case tests for SSRF validation and proxy error codes.

Exercises the pure logic of ``api.ssrf`` (no network) and the structured
``error_code`` returned by ``ProxyService.execute``, so these run fast and
offline — exactly the paths that must never silently regress.

Note: the *blocking* branch depends on ``allow_private``. To keep the tests
independent of the deployment's ``API_PROXY_ALLOW_PRIVATE`` setting, we pass
``allow_private=False`` explicitly wherever we expect a private range to be
rejected.
"""
import asyncio
from unittest import mock

import httpx
from django.test import TestCase

from api.ssrf import UnsafeUrlError, assert_safe_redirect, assert_safe_target
from api.services import ProxyService


class SsrfValidationTests(TestCase):
    def test_private_ip_literal_blocked(self):
        with self.assertRaises(UnsafeUrlError):
            assert_safe_target('http://127.0.0.1/', allow_private=False)

    def test_private_class_a_blocked(self):
        with self.assertRaises(UnsafeUrlError):
            assert_safe_target('http://10.0.0.1/', allow_private=False)

    def test_link_local_metadata_blocked(self):
        # Blocked by the explicit host blocklist regardless of allow_private.
        with self.assertRaises(UnsafeUrlError):
            assert_safe_target('http://169.254.169.254/latest/meta-data/')

    def test_public_ip_literal_allowed_and_pins_ip(self):
        url, ips, chosen = assert_safe_target('http://8.8.8.8/', allow_private=False)
        self.assertEqual(chosen, '8.8.8.8')
        self.assertIn('8.8.8.8', ips)
        # Return shape is the 3-tuple (url, ips, chosen_ip) used to pin connect.
        self.assertEqual(len((url, ips, chosen)), 3)

    def test_embedded_credentials_blocked(self):
        # Credential rejection happens before the private-range check.
        with self.assertRaises(UnsafeUrlError):
            assert_safe_target('http://user:secret@8.8.8.8/')

    def test_redirect_to_private_blocked(self):
        with self.assertRaises(UnsafeUrlError):
            assert_safe_redirect('http://8.8.8.8/x', 'http://127.0.0.1/', allow_private=False)


class ProxyErrorCodeTests(TestCase):
    def _run_execute(self, client):
        with mock.patch('api.services.assert_safe_target', lambda u: (u, [], None)):
            with mock.patch('api.services.httpx.AsyncClient', return_value=client):
                svc = ProxyService(
                    url='http://8.8.8.8/', method='GET', headers={},
                    body='', body_type='none', form_fields={},
                    files_payload={}, timeout=1,
                )
                return asyncio.run(svc.execute())

    def test_timeout_returns_structured_code(self):
        class TimeoutClient:
            def build_request(self, *a, **k):
                return mock.MagicMock()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def send(self, req):
                raise httpx.TimeoutException('timed out')

        result = self._run_execute(TimeoutClient())
        self.assertEqual(result['error_code'], 'TIMEOUT')
        self.assertIn('timed out', result['error'].lower())

    def test_error_result_carries_code(self):
        r = ProxyService._error_result(0.0, 'boom', 'CONNECT')
        self.assertEqual(r['error_code'], 'CONNECT')
        self.assertEqual(r['error'], 'boom')
