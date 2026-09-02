from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MockEndpointViewSet, MockServeView

router = DefaultRouter()
router.register(r'endpoints', MockEndpointViewSet, basename='mock-endpoint')

urlpatterns = [
    # CRUD management (authenticated)
    # /api/v1/mock/endpoints/
] + router.urls

# The catch-all mock serving URL is registered in the root urls.py:
#   path('mock/<path:mock_path>', MockServeView.as_view())
