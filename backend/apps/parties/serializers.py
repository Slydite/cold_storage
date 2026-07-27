from rest_framework import serializers
from .models import Party

class PartyOutputSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Party
        fields = (
            'id',
            'facility',
            'facility_name',
            'name',
            'code',
            'type',
            'type_display',
            'phone',
            'email',
            'address',
            'gstin',
            'is_active',
            'created_at',
            'updated_at'
        )

class PartyInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(choices=Party.PartyType.choices)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    address = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    gstin = serializers.CharField(max_length=15, required=False, allow_blank=True, default="")
    is_active = serializers.BooleanField(required=False, default=True)

