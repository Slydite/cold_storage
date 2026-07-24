from rest_framework import serializers
from .models import Facility

class FacilityOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ('id', 'name', 'code', 'address', 'created_at', 'updated_at')

class FacilityInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=50)
    address = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
