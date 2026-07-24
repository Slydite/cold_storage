from django.contrib.auth import get_user_model
from rest_framework import serializers

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
