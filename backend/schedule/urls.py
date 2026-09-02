from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssigneeViewSet,
    AssignmentViewSet,
    HolidayViewSet,
    ProjectViewSet,
)

router = DefaultRouter()
router.register('projects', ProjectViewSet)
router.register('assignments', AssignmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('assignees/', AssigneeViewSet.as_view({'get': 'list'}), name='assignees'),
    path('holidays/', HolidayViewSet.as_view({'get': 'list'}), name='holidays'),
]
