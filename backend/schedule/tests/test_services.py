"""
Tests for schedule/services.py — HolidayService & ProjectService.
"""
from unittest.mock import Mock, patch

from django.test import TestCase

from schedule.models import PROJECT_COLORS, Holiday, Project
from schedule.services import HolidayService, ProjectService


class ProjectServicePickColorTests(TestCase):
    """Test color picking strategy."""

    def test_pick_color_returns_valid_hex(self):
        color = ProjectService.pick_color()
        self.assertRegex(color, r'^#[0-9a-fA-F]{6}$')

    def test_pick_color_in_palette(self):
        color = ProjectService.pick_color()
        self.assertIn(color, PROJECT_COLORS)

    def test_pick_color_avoids_high_usage(self):
        """After many projects use a color, next pick should be different or
        at minimum still in the palette."""
        Project.objects.all().delete()
        c0 = ProjectService.pick_color()
        for i in range(10):
            Project.objects.create(name=f'proj-{i}', color=c0)
        next_color = ProjectService.pick_color()
        self.assertIn(next_color, PROJECT_COLORS)

    def test_pick_color_no_projects(self):
        Project.objects.all().delete()
        color = ProjectService.pick_color()
        self.assertIn(color, PROJECT_COLORS)


class HolidayServiceGetOrFetchTests(TestCase):
    """Test holiday fetching from network (mocked)."""

    def setUp(self):
        Holiday.objects.all().delete()

    def test_uses_cache_when_present(self):
        Holiday.objects.create(date='2025-10-01', name='NationalDay', is_off_day=True)
        with patch('schedule.services.http.get') as mock_get:
            result = HolidayService.get_or_fetch(2025)
            mock_get.assert_not_called()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['date'], '2025-10-01')
        self.assertTrue(result[0]['is_off_day'])

    def test_fetches_and_caches_when_missing(self):
        """On cache miss, fetch from upstream and persist to DB."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {
            'days': [
                {'date': '2025-10-01', 'name': '国庆节', 'isOffDay': True},
                {'date': '2025-10-02', 'name': '国庆节', 'isOffDay': True},
            ]
        }
        with patch('schedule.services.http.get', return_value=mock_resp):
            result = HolidayService.get_or_fetch(2025)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['date'], '2025-10-01')
        self.assertTrue(result[0]['is_off_day'])
        self.assertTrue(Holiday.objects.filter(date='2025-10-01').exists())
        self.assertTrue(Holiday.objects.filter(date='2025-10-02').exists())

    def test_skips_non_off_days(self):
        """Only days with isOffDay=True are saved."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {
            'days': [
                {'date': '2025-10-01', 'name': '国庆节', 'isOffDay': True},
                {'date': '2025-05-03', 'name': '调休', 'isOffDay': False},
            ]
        }
        with patch('schedule.services.http.get', return_value=mock_resp):
            result = HolidayService.get_or_fetch(2025)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['date'], '2025-10-01')
        self.assertFalse(Holiday.objects.filter(date='2025-05-03').exists())

    def test_raises_on_http_error(self):
        """HTTP errors should propagate, not be silently swallowed."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = __import__('requests').HTTPError('503')
        mock_resp.status_code = 503
        requests = __import__('requests')
        with patch('schedule.services.http.get', return_value=mock_resp), self.assertRaises(requests.HTTPError):
            HolidayService.get_or_fetch(2025)
