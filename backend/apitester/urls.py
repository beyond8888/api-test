from django.contrib import admin
from django.urls import include, path

from mock.views import MockServeView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Mock service (no auth — public) — must be before API routes
    path('mock/<path:mock_path>', MockServeView.as_view(), name='mock-serve'),

    path('api/v1/', include('api.urls')),
    path('api/v1/auth/', include('api.auth_urls')),
    path('api/v1/schedule/', include('schedule.urls')),
    path('api/v1/mock/', include('mock.urls')),
]
