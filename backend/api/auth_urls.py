"""Auth API routes — login, register, refresh, me."""
from django.urls import path

from .views import LoginView, MeView, RefreshView, RegisterView

urlpatterns = [
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('refresh/', RefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
]
