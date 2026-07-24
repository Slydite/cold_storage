from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from .serializers import CurrentUserOutputSerializer, LoginInputSerializer
from .services import login_user, logout_user


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginInputSerializer,
        responses={200: CurrentUserOutputSerializer, 400: None},
        summary="Log in user and establish session"
    )
    def post(self, request):
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            login_user(
                request=request,
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CurrentUserOutputSerializer(request.user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={204: None},
        summary="Log out current user"
    )
    def post(self, request):
        logout_user(request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: CurrentUserOutputSerializer},
        summary="Get current authenticated user"
    )
    def get(self, request):
        return Response(CurrentUserOutputSerializer(request.user).data, status=status.HTTP_200_OK)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={204: None},
        summary="Get CSRF token cookie"
    )
    def get(self, request):
        get_token(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
