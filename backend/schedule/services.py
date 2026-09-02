import logging
import time
from typing import Any

import requests as http
from django.db import transaction

from .models import PROJECT_COLORS, Holiday

logger = logging.getLogger(__name__)

HOLIDAY_SOURCE = 'https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{year}.json'


class HolidayService:
    """Fetches Chinese public holidays from remote source, caches in DB."""

    @staticmethod
    def get_or_fetch(year: int) -> list[dict[str, Any]]:
        """Return holiday list for a year; fetch from network on cache miss."""
        holidays = Holiday.objects.filter(date__year=year)
        if holidays.exists():
            return [
                {'date': str(h.date), 'name': h.name, 'is_off_day': h.is_off_day}
                for h in holidays
            ]

        # Fetch from remote with retries
        data = HolidayService._fetch_with_retry(year)

        # Batch create with transaction + get_or_create (safe under multi-process)
        created: list[dict[str, Any]] = []
        with transaction.atomic():
            for d in data.get('days', []):
                if d.get('isOffDay'):
                    holiday, _ = Holiday.objects.get_or_create(
                        date=d['date'],
                        defaults={
                            'name': d.get('name', ''),
                            'is_off_day': True,
                        },
                    )
                    created.append({
                        'date': str(holiday.date),
                        'name': holiday.name,
                        'is_off_day': True,
                    })

        logger.info('Fetched %d holidays for year %s', len(created), year)
        return created

    @staticmethod
    def _fetch_with_retry(year: int, max_retries: int = 2) -> dict:
        """Fetch holiday data from remote with exponential backoff retries."""
        url = HOLIDAY_SOURCE.format(year=year)
        for attempt in range(max_retries + 1):
            try:
                if attempt == 0:
                    logger.info('Fetching holidays for %s from %s', year, url)
                else:
                    logger.info('Retrying holiday fetch for %s (attempt %d/%d)', year, attempt + 1, max_retries + 1)
                resp = http.get(url, timeout=15)
                resp.raise_for_status()
                return resp.json()

            except http.Timeout as e:
                if attempt < max_retries:
                    delay = 2 ** attempt
                    logger.warning('Holiday fetch timeout (attempt %d/%d), retrying in %ds', attempt + 1, max_retries + 1, delay)
                    time.sleep(delay)
                else:
                    logger.error('Timeout fetching holidays for year %s', year)
                    raise TimeoutError('Upstream timeout') from e

            except http.HTTPError as e:
                if attempt < max_retries and e.response is not None and e.response.status_code >= 500:
                    delay = 2 ** attempt
                    logger.warning('Holiday source returned %d (attempt %d/%d), retrying in %ds', e.response.status_code, attempt + 1, max_retries + 1, delay)
                    time.sleep(delay)
                else:
                    logger.error('Upstream returned %s for year %s', e.response.status_code if e.response else '?', year)
                    raise

            except Exception as e:
                logger.exception('Failed to fetch holidays for year %s', year)
                raise RuntimeError(f'Failed to fetch holidays for year {year}') from e

        # Should not reach here, but satisfy type checker
        raise RuntimeError(f'Failed to fetch holidays for year {year}')


class ProjectService:
    """Business logic for project color assignment."""

    @staticmethod
    def pick_color(exclude_color: str = '#10b981') -> str:
        from .models import Project
        used = list(Project.objects.exclude(
            color__in=['', exclude_color]
        ).values_list('color', flat=True))
        usage = {c: used.count(c) for c in PROJECT_COLORS}
        return min(PROJECT_COLORS, key=lambda c: usage.get(c, 0))
