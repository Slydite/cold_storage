from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from django.contrib.auth import get_user_model
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .selectors import get_users_list, get_user_by_id
from .serializers import (
    CurrentUserOutputSerializer,
    LoginInputSerializer,
    UserListOutputSerializer,
    UserCreateInputSerializer,
    UserUpdateInputSerializer,
    TokenAuthOutputSerializer
)
from .services import (
    login_user,
    logout_user,
    create_user_account,
    update_user_account,
    deactivate_user,
    activate_user,
    get_or_create_user_token,
    revoke_user_token
)

User = get_user_model()


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


class TokenLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginInputSerializer,
        responses={200: TokenAuthOutputSerializer, 400: None},
        summary="Obtain auth token using username and password"
    )
    def post(self, request):
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token_key, user = get_or_create_user_token(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "token": token_key,
            "user": CurrentUserOutputSerializer(user).data
        }, status=status.HTTP_200_OK)


class TokenRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={204: None},
        summary="Revoke token for current authenticated user"
    )
    def post(self, request):
        revoke_user_token(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(ViewSet):
    """
    User management endpoints.
    NOTE: Currently protected by permission_classes = [IsAuthenticated] in accordance with standing.md §9.
    Because 'ADMIN' is the only role today, any authenticated user can manage users.
    Must be revisited when role-based access control (RBAC) is expanded.
    """
    permission_classes = [IsAuthenticated]
    queryset = User.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False, description="Filter by active status"),
        ],
        responses={200: UserListOutputSerializer(many=True)},
        summary="List user accounts"
    )
    def list(self, request):
        is_active_param = request.query_params.get('is_active')
        is_active_filter = None
        if is_active_param is not None:
            is_active_filter = is_active_param.lower() in ['true', '1', 'yes']

        users = get_users_list(is_active=is_active_filter)
        serializer = UserListOutputSerializer(users, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: UserListOutputSerializer, 404: None},
        summary="Retrieve a user account by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            user = get_user_by_id(pk)
        except (User.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserListOutputSerializer(user)
        return Response(serializer.data)

    @extend_schema(
        request=UserCreateInputSerializer,
        responses={201: UserListOutputSerializer, 400: None},
        summary="Create a new user account"
    )
    def create(self, request):
        serializer = UserCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = create_user_account(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password'],
                email=serializer.validated_data.get('email', ''),
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', ''),
                role=serializer.validated_data.get('role'),
                is_active=serializer.validated_data.get('is_active', True)
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = UserListOutputSerializer(user)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=UserUpdateInputSerializer,
        responses={200: UserListOutputSerializer, 400: None},
        summary="Update an existing user account"
    )
    def update(self, request, pk=None):
        serializer = UserUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = update_user_account(
                user_id=pk,
                **serializer.validated_data
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = UserListOutputSerializer(user)
        return Response(output_serializer.data)

    @extend_schema(
        responses={200: UserListOutputSerializer, 400: None},
        summary="Deactivate a user account"
    )
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        try:
            user = deactivate_user(user_id=pk)
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = UserListOutputSerializer(user)
        return Response(output_serializer.data)

    @extend_schema(
        responses={200: UserListOutputSerializer, 400: None},
        summary="Re-activate a user account"
    )
    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        try:
            user = activate_user(user_id=pk)
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = UserListOutputSerializer(user)
        return Response(output_serializer.data)

