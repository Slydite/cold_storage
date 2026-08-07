from rest_framework import serializers
from libs.choices import ChargeMode
from .models import DeliveryNote, DeliveryLine


class DeliveryLineInputSerializer(serializers.Serializer):
    lot_id = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1)


class DeliveryNoteCreateInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    party_id = serializers.IntegerField()
    dispatch_date = serializers.DateField()
    vehicle_number = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    driver_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    transporter = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    remarks = serializers.CharField(max_length=1000, required=False, allow_blank=True, default='')
    loading_charge = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    loading_unloading_rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    loading_charge_mode = serializers.ChoiceField(choices=ChargeMode.choices, default=ChargeMode.FLAT)
    status = serializers.ChoiceField(choices=DeliveryNote.Status.choices, default=DeliveryNote.Status.DRAFT)
    lines = DeliveryLineInputSerializer(many=True, required=False, default=list)


class DeliveryNoteUpdateInputSerializer(serializers.Serializer):
    party_id = serializers.IntegerField(required=False)
    dispatch_date = serializers.DateField(required=False)
    vehicle_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    driver_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    transporter = serializers.CharField(max_length=255, required=False, allow_blank=True)
    remarks = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    loading_charge = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    loading_unloading_rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    loading_charge_mode = serializers.ChoiceField(choices=ChargeMode.choices, required=False)
    lines = DeliveryLineInputSerializer(many=True, required=False)


class DeliveryLineOutputSerializer(serializers.ModelSerializer):
    lot_number = serializers.CharField(source='lot.lot_number', read_only=True)
    commodity_name = serializers.CharField(source='lot.commodity.name', read_only=True)
    commodity_code = serializers.CharField(source='lot.commodity.code', read_only=True)

    class Meta:
        model = DeliveryLine
        fields = [
            'id',
            'facility_id',
            'delivery_note_id',
            'lot_id',
            'lot_number',
            'commodity_name',
            'commodity_code',
            'qty',
            'balance_after',
            'created_at',
            'updated_at'
        ]


class DeliveryNoteOutputSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_code = serializers.CharField(source='party.code', read_only=True)
    party_email = serializers.CharField(source='party.email', read_only=True)
    lines = DeliveryLineOutputSerializer(many=True, read_only=True)
    computed_loading_charge = serializers.SerializerMethodField()
    legacy_ref = serializers.CharField(read_only=True)

    class Meta:
        model = DeliveryNote
        fields = [
            'id',
            'facility_id',
            'dn_number',
            'legacy_ref',
            'party_id',
            'party_name',
            'party_code',
            'party_email',
            'dispatch_date',
            'vehicle_number',
            'driver_name',
            'transporter',
            'remarks',
            'loading_charge',
            'loading_unloading_rate_per_unit',
            'loading_charge_mode',
            'computed_loading_charge',
            'status',
            'last_emailed_at',
            'lines',
            'created_at',
            'updated_at'
        ]

    def get_computed_loading_charge(self, obj):
        return obj.computed_loading_charge()
