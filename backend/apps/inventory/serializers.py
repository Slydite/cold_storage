from rest_framework import serializers
from libs.choices import ChargeMode
from .models import Commodity, GRN, Lot, StockAdjustment, CommodityAlias, LotRateChange

class CommodityAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommodityAlias
        fields = ['id', 'name', 'created_at']

class CommodityInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    unit = serializers.CharField(max_length=50, default='BAGS')
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True, default='')
    is_active = serializers.BooleanField(default=True)



class CommodityOutputSerializer(serializers.ModelSerializer):
    aliases = CommodityAliasSerializer(many=True, read_only=True)

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
            'aliases',
            'created_at',
            'updated_at'
        ]


class LotItemInputSerializer(serializers.Serializer):
    commodity_id = serializers.IntegerField()
    lot_number = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    chamber = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    floor = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    rack = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    chamber_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    floor_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    block_id = serializers.IntegerField(required=True)
    special_remarks = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    initial_qty = serializers.IntegerField(min_value=1)
    unit = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    unit_weight = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    rent_rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)

    def to_internal_value(self, data):
        if 'block_id' not in data or data['block_id'] is None or data['block_id'] == '':
            commodity_id = data.get('commodity_id')
            commodity_name = "Unknown"
            if commodity_id:
                try:
                    commodity_name = Commodity.objects.get(pk=commodity_id).name
                except Commodity.DoesNotExist:
                    pass
            raise serializers.ValidationError({
                'block_id': f"Storage location (block) is required for commodity '{commodity_name}'."
            })
        return super().to_internal_value(data)


class StockAdjustmentSerializer(serializers.ModelSerializer):
    adjusted_by_username = serializers.CharField(source='adjusted_by.username', read_only=True, allow_null=True)

    class Meta:
        model = StockAdjustment
        fields = [
            'id',
            'lot_id',
            'qty_delta',
            'qty_before',
            'qty_after',
            'reason',
            'note',
            'adjustment_date',
            'adjusted_by_id',
            'adjusted_by_username',
            'created_at'
        ]


class LotRateChangeSerializer(serializers.ModelSerializer):
    entered_by_username = serializers.CharField(source='entered_by.username', read_only=True, allow_null=True)

    class Meta:
        model = LotRateChange
        fields = [
            'id',
            'lot_id',
            'rate_per_unit',
            'effective_from',
            'note',
            'entered_by_id',
            'entered_by_username',
            'created_at'
        ]


class LotOutputSerializer(serializers.ModelSerializer):
    commodity_name = serializers.CharField(source='commodity.name', read_only=True)
    commodity_code = serializers.CharField(source='commodity.code', read_only=True)
    commodity_unit = serializers.CharField(source='commodity.unit', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    grn_number = serializers.CharField(source='grn.grn_number', read_only=True)
    party_id = serializers.IntegerField(source='grn.party_id', read_only=True)
    party_name = serializers.CharField(source='grn.party.name', read_only=True)
    party_code = serializers.CharField(source='grn.party.code', read_only=True)
    chamber_ref_id = serializers.IntegerField(source='chamber_ref.id', read_only=True, allow_null=True)
    chamber_name = serializers.SerializerMethodField()
    floor_ref_id = serializers.IntegerField(source='floor_ref.id', read_only=True, allow_null=True)
    floor_name = serializers.SerializerMethodField()
    block_ref_id = serializers.IntegerField(source='block_ref.id', read_only=True, allow_null=True)
    block_name = serializers.SerializerMethodField()
    location_display = serializers.CharField(read_only=True)
    legacy_ref = serializers.CharField(read_only=True)
    adjustments = StockAdjustmentSerializer(many=True, read_only=True)

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
            'legacy_ref',
            'chamber',
            'floor',
            'rack',
            'chamber_ref_id',
            'chamber_name',
            'floor_ref_id',
            'floor_name',
            'block_ref_id',
            'block_name',
            'location_display',
            'special_remarks',
            'initial_qty',
            'remaining_qty',
            'unit',
            'unit_weight',
            'rent_rate_per_unit',
            'inward_date',
            'adjustments',
            'rate_changes',
            'created_at',
            'updated_at'
        ]

    rate_changes = LotRateChangeSerializer(many=True, read_only=True)

    def get_chamber_name(self, obj):
        return obj.chamber_ref.name if obj.chamber_ref else (obj.chamber or None)

    def get_floor_name(self, obj):
        return obj.floor_ref.name if obj.floor_ref else (obj.floor or None)

    def get_block_name(self, obj):
        return obj.block_ref.name if obj.block_ref else (obj.rack or None)


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
    loading_charge_mode = serializers.ChoiceField(choices=ChargeMode.choices, default=ChargeMode.FLAT)
    inward_time = serializers.TimeField(required=False, allow_null=True, default=None)
    status = serializers.ChoiceField(choices=GRN.Status.choices, default=GRN.Status.POSTED)
    items = LotItemInputSerializer(many=True, required=False, default=list)


class GRNOutputSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_code = serializers.CharField(source='party.code', read_only=True)
    party_email = serializers.CharField(source='party.email', read_only=True)
    lots = LotOutputSerializer(many=True, read_only=True)
    computed_loading_charge = serializers.SerializerMethodField()
    legacy_ref = serializers.CharField(read_only=True)

    class Meta:
        model = GRN
        fields = [
            'id',
            'facility_id',
            'grn_number',
            'legacy_ref',
            'party_id',
            'party_name',
            'party_code',
            'party_email',
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
            'loading_charge_mode',
            'computed_loading_charge',
            'inward_time',
            'status',
            'last_emailed_at',
            'lots',
            'created_at',
            'updated_at'
        ]

    def get_computed_loading_charge(self, obj):
        return obj.computed_loading_charge()


class LotWithdrawalInputSerializer(serializers.Serializer):
    qty = serializers.IntegerField(min_value=1)


class LotReserveNumberInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()


class LotReserveNumberOutputSerializer(serializers.Serializer):
    lot_number = serializers.CharField()


class LotAdjustmentInputSerializer(serializers.Serializer):
    new_qty = serializers.IntegerField(required=False, allow_null=True, default=None)
    qty_delta = serializers.IntegerField(required=False, allow_null=True, default=None)
    reason = serializers.ChoiceField(choices=StockAdjustment.Reason.choices)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    adjustment_date = serializers.DateField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        new_qty = attrs.get('new_qty')
        qty_delta = attrs.get('qty_delta')
        if new_qty is not None and qty_delta is not None:
            raise serializers.ValidationError("Cannot provide both new_qty and qty_delta.")
        if new_qty is None and qty_delta is None:
            raise serializers.ValidationError("Specify either new_qty or qty_delta.")

        reason = attrs.get('reason')
        note = attrs.get('note', '')
        if reason == StockAdjustment.Reason.OTHER and not note.strip():
            raise serializers.ValidationError({"note": "Note is mandatory when reason is OTHER."})

        return attrs


class CommodityAliasInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class CommodityMergeInputSerializer(serializers.Serializer):
    source_commodity_id = serializers.IntegerField()


class LotRateChangeInputSerializer(serializers.Serializer):
    rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)
    effective_from = serializers.DateField()
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class LotBulkRateChangeInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)
    effective_from = serializers.DateField()
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    lot_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True, default=None)
    commodity_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    party_id = serializers.IntegerField(required=False, allow_null=True, default=None)




