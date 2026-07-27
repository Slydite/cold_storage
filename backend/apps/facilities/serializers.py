from rest_framework import serializers
from .models import Facility

class FacilityOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = (
            'id', 'name', 'code', 'address', 'gstin', 'phone', 'factory_phone',
            'bank_account_no', 'bank_ifsc', 'terms_and_conditions', 'created_at', 'updated_at'
        )

class FacilityInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    address = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    gstin = serializers.CharField(max_length=15, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    factory_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    bank_account_no = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    bank_ifsc = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    terms_and_conditions = serializers.CharField(required=False, allow_blank=True, default="")


