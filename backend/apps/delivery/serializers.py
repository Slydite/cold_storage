from rest_framework import serializers
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
    status = serializers.ChoiceField(choices=DeliveryNote.Status.choices, default=DeliveryNote.Status.DRAFT)
    lines = DeliveryLineInputSerializer(many=True, required=False, default=list)


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
    lines = DeliveryLineOutputSerializer(many=True, read_only=True)

    class Meta:
        model = DeliveryNote
        fields = [
            'id',
            'facility_id',
            'dn_number',
            'party_id',
            'party_name',
            'party_code',
            'dispatch_date',
            'vehicle_number',
            'driver_name',
            'transporter',
            'remarks',
            'status',
            'lines',
            'created_at',
            'updated_at'
        ]
