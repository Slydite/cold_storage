from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    CurrentUserView, CsrfView, LoginView, LogoutView, UserViewSet,
    TokenLoginView, TokenRevokeView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', CurrentUserView.as_view(), name='auth-me'),
    path('auth/csrf/', CsrfView.as_view(), name='auth-csrf'),
    path('auth/token/', TokenLoginView.as_view(), name='auth-token'),
    path('auth/token/revoke/', TokenRevokeView.as_view(), name='auth-token-revoke'),
] + router.urls

