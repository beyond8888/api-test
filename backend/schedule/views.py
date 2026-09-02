import calendar
import logging
from contextlib import suppress
from datetime import date

from rest_framework import filters, viewsets

from apitester.api_response import fail, success
from apitester.crud_mixin import OwnerScopedMixin, UnifiedCRUDMixin
from common.pagination import StandardResultsSetPagination
from common.utils import first_error

from .models import Assignment, Project
from .serializers import (
    AssigneeQuerySerializer,
    AssignmentSerializer,
    HolidayQuerySerializer,
    ProjectSerializer,
)
from .services import HolidayService, ProjectService

logger = logging.getLogger(__name__)


class ProjectViewSet(OwnerScopedMixin, UnifiedCRUDMixin, viewsets.ModelViewSet):
    model_label = 'Project'
    throttle_scope = 'schedule'

    queryset = Project.objects.all().prefetch_related('assignments').order_by('-created_at')
    serializer_class = ProjectSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        color = self.request.data.get('color') or ProjectService.pick_color()
        serializer.save(owner=self.request.user, color=color)


class AssignmentViewSet(OwnerScopedMixin, UnifiedCRUDMixin, viewsets.ModelViewSet):
    model_label = 'Assignment'
    throttle_scope = 'schedule'

    queryset = Assignment.objects.select_related('project').all().order_by('start_date')
    serializer_class = AssignmentSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'assignee']

    def get_queryset(self):
        """Support year/month/assignee/project_id query filtering."""
        qs = super().get_queryset()
        params = self.request.query_params

        year = params.get('year')
        month = params.get('month')
        if year and month:
            # Return every assignment that overlaps the requested month,
            # not only the ones whose *start_date* falls in that month.
            with suppress(TypeError, ValueError):
                y = int(year)
                m = int(month)
                _, last_day = calendar.monthrange(y, m)
                start_of_month = date(y, m, 1)
                end_of_month = date(y, m, last_day)
                qs = qs.filter(start_date__lte=end_of_month, end_date__gte=start_of_month)
        elif year:
            with suppress(TypeError, ValueError):
                qs = qs.filter(start_date__year=int(year))

        assignee = params.get('assignee')
        if assignee:
            # Support comma-separated multiple assignees
            assignees = [a.strip() for a in assignee.split(',') if a.strip()]
            if assignees:
                qs = qs.filter(assignee__in=assignees)

        project_id = params.get('project_id')
        if project_id:
            with suppress(TypeError, ValueError):
                qs = qs.filter(project_id=int(project_id))

        return qs

    def perform_update(self, serializer):
        serializer.save(owner=self.request.user)


class HolidayViewSet(viewsets.ViewSet):
    """Fetch holidays from GitHub holiday-cn repo, cache in DB."""

    def list(self, request):
        serializer = HolidayQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return fail(first_error(serializer.errors))

        year_int = serializer.validated_data['year']

        try:
            holidays = HolidayService.get_or_fetch(year_int)
            return success(holidays)
        except TimeoutError:
            return fail('Upstream timeout', status=504)
        except RuntimeError as e:
            logger.error('Holiday fetch failed: %s', e)
            return fail(str(e), status=502)


class AssigneeViewSet(viewsets.ViewSet):
    """Return distinct assignees across projects, per project, or per role."""

    def list(self, request):
        serializer = AssigneeQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return fail(first_error(serializer.errors))

        validated = serializer.validated_data
        qs = Assignment.objects.select_related('project').filter(owner=self.request.user)
        if validated.get('project_id'):
            qs = qs.filter(project_id=validated['project_id'])
        if validated.get('role'):
            qs = qs.filter(role=validated['role'])

        assignees = list(
            qs.exclude(assignee__exact='')
            .values_list('assignee', flat=True)
            .distinct()
            .order_by('assignee')
        )
        return success(assignees)
