from rest_framework import serializers
from .models import Commodity, GRN, Lot

class CommodityInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=50)
    unit = serializers.CharField(max_length=50, default='BAGS')
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True, default='')
    is_active = serializers.BooleanField(default=True)


class CommodityOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commodity
        fields = [
            'id',
            'facility_id',
            'name',
            'code',
            'unit',
            'description',
            'is_active',
            'created_at',
            'updated_at'
        ]


class LotItemInputSerializer(serializers.Serializer):
    commodity_id = serializers.IntegerField()
    lot_number = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    chamber = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    floor = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    rack = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    floor_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    chamber_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    special_remarks = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    initial_qty = serializers.IntegerField(min_value=1)
    unit_weight = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    rent_rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)


class LotOutputSerializer(serializers.ModelSerializer):
    commodity_name = serializers.CharField(source='commodity.name', read_only=True)
    commodity_code = serializers.CharField(source='commodity.code', read_only=True)
    commodity_unit = serializers.CharField(source='commodity.unit', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    grn_number = serializers.CharField(source='grn.grn_number', read_only=True)
    party_id = serializers.IntegerField(source='grn.party_id', read_only=True)
    party_name = serializers.CharField(source='grn.party.name', read_only=True)
    party_code = serializers.CharField(source='grn.party.code', read_only=True)
    floor_ref_id = serializers.IntegerField(source='floor_ref.id', read_only=True, allow_null=True)
    chamber_ref_id = serializers.IntegerField(source='chamber_ref.id', read_only=True, allow_null=True)
    floor_name = serializers.CharField(source='floor_ref.name', read_only=True, allow_null=True)
    chamber_name = serializers.CharField(source='chamber_ref.name', read_only=True, allow_null=True)

    class Meta:
        model = Lot
        fields = [
            'id',
            'facility_id',
            'facility_name',
            'grn_id',
            'grn_number',
            'party_id',
            'party_name',
            'party_code',
            'commodity_id',
            'commodity_name',
            'commodity_code',
            'commodity_unit',
            'lot_number',
            'chamber',
            'floor',
            'rack',
            'floor_ref_id',
            'chamber_ref_id',
            'floor_name',
            'chamber_name',
            'special_remarks',
            'initial_qty',
            'remaining_qty',
            'unit_weight',
            'rent_rate_per_unit',
            'inward_date',
            'created_at',
            'updated_at'
        ]



class GRNCreateInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    party_id = serializers.IntegerField()
    receipt_date = serializers.DateField()
    vehicle_number = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    driver_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    remarks = serializers.CharField(max_length=1000, required=False, allow_blank=True, default='')
    loading_charge = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    bill_no = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    bilty_no = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    transporter = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    preservation_rate_per_bag_per_month = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    loading_unloading_rate_per_bag = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    inward_time = serializers.TimeField(required=False, allow_null=True, default=None)
    status = serializers.ChoiceField(choices=GRN.Status.choices, default=GRN.Status.POSTED)
    items = LotItemInputSerializer(many=True, required=False, default=list)


class GRNOutputSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_code = serializers.CharField(source='party.code', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    lots = LotOutputSerializer(many=True, read_only=True)

    class Meta:
        model = GRN
        fields = [
            'id',
            'facility_id',
            'grn_number',
            'party_id',
            'party_name',
            'party_code',
            'receipt_date',
            'vehicle_number',
            'driver_name',
            'remarks',
            'loading_charge',
            'bill_no',
            'bilty_no',
            'transporter',
            'preservation_rate_per_bag_per_month',
            'loading_unloading_rate_per_bag',
            'inward_time',
            'status',
            'pdf_url',
            'lots',
            'created_at',
            'updated_at'
        ]

    def get_pdf_url(self, obj) -> str | None:
        return obj.pdf_file.url if obj.pdf_file else None


class LotWithdrawalInputSerializer(serializers.Serializer):
    qty = serializers.IntegerField(min_value=1)
