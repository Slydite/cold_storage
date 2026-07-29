from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Role

User = get_user_model()


class LoginInputSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class CurrentUserOutputSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role')

    def get_role(self, obj):
        return getattr(getattr(obj, 'profile', None), 'role', 'ADMIN')


class UserListOutputSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'role', 'date_joined', 'last_login'
        )

    def get_role(self, obj):
        return getattr(getattr(obj, 'profile', None), 'role', 'ADMIN')


class UserCreateInputSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    role = serializers.ChoiceField(choices=Role.choices, default=Role.ADMIN)
    is_active = serializers.BooleanField(default=True)


class UserUpdateInputSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=Role.choices, required=False)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True, style={'input_type': 'password'})
    # NOTE: is_active is deliberately NOT accepted here. DRF's BooleanField
    # coerces an ABSENT value to False for HTML-form/multipart input, so a
    # PUT that only changed a name silently arrived with is_active=False and
    # deactivated the account. Activation state changes go through the
    # explicit activate/deactivate actions instead.


class TokenAuthOutputSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = CurrentUserOutputSerializer()


