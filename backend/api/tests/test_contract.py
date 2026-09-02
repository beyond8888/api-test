"""Contract tests guarding frontend/backend API shape agreements.

These prevent regressions where the backend response shape drifts from what
the frontend services expect (e.g. paginated wrappers, flat vs nested lists).
"""
import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import HistoryEntry
from api.serializers import HistoryEntrySerializer
from schedule.models import Assignment, Project


class HistoryContractTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='histuser', password='pw')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_list_is_paginated_and_enveloped(self):
        # HistoryViewSet now uses UnifiedCRUDMixin, so list() wraps the native
        # StandardResultsSetPagination dict inside the unified envelope — exactly
        # like the schedule app. The frontend's response interceptor unwraps the
        # envelope, then fetchHistory() reads `.results`/`.count`/`.next`.
        for i in range(3):
            HistoryEntry.objects.create(
                owner=self.user,
                request={'method': 'GET', 'url': f'/x/{i}'},
                response={'status': 200, 'body': 'ok'},
            )
        resp = self.client.get('/api/v1/history/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Unified envelope wraps the paginated payload.
        self.assertEqual(data['code'], 0)
        payload = data['data']
        self.assertIn('results', payload)
        self.assertIn('count', payload)
        self.assertIsInstance(payload['results'], list)
        self.assertEqual(payload['count'], 3)
        self.assertIsInstance(payload['results'][0], dict)
        self.assertIn('id', payload['results'][0])

    def test_serializer_truncates_oversized_body(self):
        big = 'x' * (2 * 1024 * 1024)  # 2 MB
        ser = HistoryEntrySerializer(data={
            'request': {'method': 'GET', 'url': '/'},
            'response': {'status': 200, 'body': big},
        })
        self.assertTrue(ser.is_valid(), ser.errors)
        body = ser.validated_data['response']['body']
        self.assertIn('truncated', ser.validated_data['response'])
        self.assertLessEqual(len(body), 1_000_000 + 32)


class ProxyContractTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='proxyuser', password='pw')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_invalid_payload_returns_400_not_500_coroutine(self):
        # Regression: ProxyView.post was async in a DRF build whose
        # APIView.dispatch is sync, so it returned a <coroutine> that
        # finalize_response rejected with a 500 AssertionError. After the fix
        # the view is sync and must return a real Response (here a 400 because
        # the URL fails validation).
        resp = self.client.post('/api/v1/proxy/', {'url': ''}, format='json')
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        # Unified envelope — proves a real Response object was produced.
        self.assertIn('code', data)
        self.assertNotEqual(data['code'], 0)


class AssigneesContractTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='asuser', password='pw')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_assignees_returns_flat_list_in_envelope(self):
        project = Project.objects.create(owner=self.user, name='P', color='red')
        Assignment.objects.create(
            owner=self.user, project=project, title='T',
            start_date='2026-01-01', end_date='2026-01-02',
            assignee='alice', role='dev',
        )
        resp = self.client.get('/api/v1/schedule/assignees/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['code'], 0)
        # AssigneeViewSet returns a flat list of strings, not {usernames: [...]}
        self.assertIsInstance(data['data'], list)
        self.assertIn('alice', data['data'])


class AuthContractTests(TestCase):
    def test_login_returns_envelope(self):
        # P2: login must speak the unified envelope, not raw simplejwt {access,refresh}.
        User.objects.create_user(username='authuser', password='pw12345')
        resp = self.client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'username': 'authuser', 'password': 'pw12345'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['code'], 0)
        self.assertIn('access', data['data'])
        self.assertIn('refresh', data['data'])

    def test_refresh_path_and_envelope(self):
        # P1: refresh must live at /api/v1/auth/refresh/ (not /auth/token/refresh/).
        User.objects.create_user(username='authuser2', password='pw12345')
        login = self.client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'username': 'authuser2', 'password': 'pw12345'}),
            content_type='application/json')
        refresh = login.json()['data']['refresh']

        resp = self.client.post(
            '/api/v1/auth/refresh/',
            data=json.dumps({'refresh': refresh}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['code'], 0)
        self.assertIn('access', data['data'])

        # The old, broken path must not exist.
        bad = self.client.post(
            '/api/v1/auth/token/refresh/',
            data=json.dumps({'refresh': refresh}),
            content_type='application/json')
        self.assertEqual(bad.status_code, 404)


class AssignmentOwnerIsolationTests(TestCase):
    """Regression: an assignment may only target the requester's own projects.

    Guards against an IDOR where a logged-in user could attach an assignment to
    another user's project by guessing its id.
    """

    def setUp(self):
        self.victim = User.objects.create_user(username='victim', password='pw')
        self.attacker = User.objects.create_user(username='attacker', password='pw')
        self.victim_project = Project.objects.create(
            owner=self.victim, name='victim-proj', color='#e53935'
        )
        self.client = APIClient()

    def test_cannot_attach_assignment_to_other_users_project(self):
        self.client.force_authenticate(self.attacker)
        resp = self.client.post('/api/v1/schedule/assignments/', data={
            'project': self.victim_project.id,
            'title': 'hijack attempt',
            'start_date': '2026-01-01',
            'end_date': '2026-01-02',
        }, format='json')
        # Project FK is not selectable by this user → 400 validation error.
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(
            Assignment.objects.filter(project=self.victim_project).exists()
        )

    def test_can_attach_assignment_to_own_project(self):
        own = Project.objects.create(owner=self.attacker, name='mine', color='#1e88e5')
        self.client.force_authenticate(self.attacker)
        resp = self.client.post('/api/v1/schedule/assignments/', data={
            'project': own.id,
            'title': 'legit',
            'start_date': '2026-01-01',
            'end_date': '2026-01-02',
        }, format='json')
        self.assertIn(resp.status_code, (200, 201), resp.content)
        self.assertTrue(Assignment.objects.filter(project=own).exists())
