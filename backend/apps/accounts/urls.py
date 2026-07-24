from django.urls import path
from .views import CurrentUserView, CsrfView, LoginView, LogoutView

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', CurrentUserView.as_view(), name='auth-me'),
    path('auth/csrf/', CsrfView.as_view(), name='auth-csrf'),
]
