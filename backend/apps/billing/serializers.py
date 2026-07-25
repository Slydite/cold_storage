from decimal import Decimal
from rest_framework import serializers
from .models import RateCard, RentRun, RentRunLine


class RateCardInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    commodity_id = serializers.IntegerField()
    party_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    weight_category = serializers.ChoiceField(choices=RateCard.WeightCategory.choices)
    rate_per_bag_per_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    effective_from = serializers.DateField()
    is_active = serializers.BooleanField(default=True)


class RateCardOutputSerializer(serializers.ModelSerializer):
    commodity_name = serializers.CharField(source='commodity.name', read_only=True)
    commodity_code = serializers.CharField(source='commodity.code', read_only=True)
    party_name = serializers.CharField(source='party.name', read_only=True, allow_null=True, default=None)
    weight_category_display = serializers.CharField(source='get_weight_category_display', read_only=True)
    is_default = serializers.SerializerMethodField()

    class Meta:
        model = RateCard
        fields = [
            'id',
            'facility_id',
            'party_id',
            'party_name',
            'is_default',
            'commodity_id',
            'commodity_name',
            'commodity_code',
            'weight_category',
            'weight_category_display',
            'rate_per_bag_per_month',
            'effective_from',
            'is_active',
            'created_at',
            'updated_at'
        ]

    def get_is_default(self, obj) -> bool:
        return obj.party_id is None


class RentRunCreateInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    party_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    commodity_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    chamber = serializers.CharField(required=False, allow_blank=True, default='')
    min_billing_days = serializers.IntegerField(required=False, min_value=0, default=0)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class RentRunPreviewInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    party_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    commodity_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    chamber = serializers.CharField(required=False, allow_blank=True, default='')
    min_billing_days = serializers.IntegerField(required=False, min_value=0, default=0)


class RentRunPreviewLineSerializer(serializers.Serializer):
    lot_id = serializers.IntegerField()
    lot_number = serializers.CharField()
    commodity_id = serializers.IntegerField()
    commodity_name = serializers.CharField()
    party_id = serializers.IntegerField()
    party_name = serializers.CharField()
    qty = serializers.IntegerField()
    weight_category = serializers.CharField()
    rate_per_bag_per_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    days_stored = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    rate_source = serializers.CharField()


class MissingRateCardSerializer(serializers.Serializer):
    commodity_id = serializers.IntegerField()
    commodity_name = serializers.CharField()
    weight_category = serializers.CharField()
    lot_number = serializers.CharField()


class RentRunPreviewOutputSerializer(serializers.Serializer):
    lines = RentRunPreviewLineSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    missing_rate_cards = MissingRateCardSerializer(many=True)


class RentRunLineOutputSerializer(serializers.ModelSerializer):
    lot_number = serializers.CharField(source='lot.lot_number', read_only=True)
    commodity_name = serializers.CharField(source='lot.commodity.name', read_only=True)
    party_name = serializers.CharField(source='party.name', read_only=True)

    class Meta:
        model = RentRunLine
        fields = [
            'id',
            'lot_id',
            'lot_number',
            'commodity_name',
            'party_id',
            'party_name',
            'qty',
            'weight_category',
            'rate_per_bag_per_month',
            'days_stored',
            'amount'
        ]


class RentRunOutputSerializer(serializers.ModelSerializer):
    lines = RentRunLineOutputSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    party_name = serializers.CharField(source='party.name', read_only=True, allow_null=True, default=None)
    commodity_name = serializers.CharField(source='commodity.name', read_only=True, allow_null=True, default=None)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = RentRun
        fields = [
            'id',
            'facility_id',
            'period_start',
            'period_end',
            'party_id',
            'party_name',
            'commodity_id',
            'commodity_name',
            'chamber',
            'min_billing_days',
            'notes',
            'status',
            'run_date',
            'lines',
            'total_amount',
            'pdf_url',
            'created_at',
            'updated_at'
        ]

    def get_total_amount(self, obj) -> Decimal:
        return sum((l.amount for l in obj.lines.all()), Decimal('0.00'))

    def get_pdf_url(self, obj) -> str | None:
        return obj.pdf_file.url if obj.pdf_file else None

