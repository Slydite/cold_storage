from rest_framework import serializers
from .models import Invoice, InvoiceLine, Payment


class InvoiceLineOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            'id',
            'description',
            'amount',
            'quantity',
            'unit',
            'rate_per_unit',
            'charge_type',
            'sac_code',
            'period_from',
            'period_to',
        ]


class PaymentOutputSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'invoice_id',
            'amount',
            'payment_date',
            'method',
            'method_display',
            'reference',
            'notes',
            'created_at',
        ]


class PaymentInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_date = serializers.DateField()
    method = serializers.ChoiceField(choices=Payment.Method.choices, default=Payment.Method.CASH)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class InvoiceOutputSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_email = serializers.CharField(source='party.email', read_only=True)
    lines = InvoiceLineOutputSerializer(many=True, read_only=True)
    amount_paid = serializers.SerializerMethodField()
    amount_due = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payments = PaymentOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'facility_id',
            'invoice_number',
            'party_id',
            'party_name',
            'party_email',
            'party_gstin_snapshot',
            'party_name_snapshot',
            'party_address_snapshot',
            'facility_name_snapshot',
            'facility_address_snapshot',
            'facility_gstin_snapshot',
            'invoice_date',
            'status',
            # Read-only derived fields
            'financial_year',
            'subtotal',
            'taxable_value',
            'gst_rate',
            'gst_amount',
            'cgst_amount',
            'sgst_amount',
            'igst_amount',
            'total_amount',
            # Writable fields
            'discount_amount',
            'discount_reason',
            'cgst_rate',
            'sgst_rate',
            'igst_rate',
            'place_of_supply',
            'document_type',
            'is_reverse_charge',
            'exemption_reason',
            # Payment info
            'amount_paid',
            'amount_due',
            'payment_status',
            'payments',
            'lines',
            'last_emailed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'financial_year',
            'subtotal',
            'taxable_value',
            'gst_amount',
            'cgst_amount',
            'sgst_amount',
            'igst_amount',
        ]

    def get_amount_paid(self, obj) -> str:
        return str(obj.amount_paid)

    def get_amount_due(self, obj) -> str:
        return str(obj.amount_due)

    def get_payment_status(self, obj) -> str:
        return obj.payment_status


class GenerateInvoicesInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    party_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    # Optional manual overrides. When all three rates are omitted the
    # facility's default_gst_rate is used, split intra-state.
    cgst_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None, min_value=0
    )
    sgst_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None, min_value=0
    )
    igst_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None, min_value=0
    )
    discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, default=None, min_value=0
    )


class AdjustInvoiceInputSerializer(serializers.Serializer):
    """
    Manual tax and discount controls for a DRAFT invoice. Every field is
    optional; whatever is supplied is applied and the totals are recomputed.
    """
    discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    discount_reason = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    cgst_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    sgst_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    igst_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    place_of_supply = serializers.CharField(
        max_length=2, required=False, allow_blank=True
    )
    document_type = serializers.ChoiceField(
        choices=Invoice.DocumentType.choices, required=False, allow_null=True
    )
    is_reverse_charge = serializers.BooleanField(required=False)
    exemption_reason = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )


class InvoicePreviewLineOutputSerializer(serializers.Serializer):
    description = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    lot_number = serializers.CharField(allow_null=True, required=False, default=None)
    commodity_name = serializers.CharField(allow_null=True, required=False, default=None)
    qty = serializers.IntegerField(allow_null=True, required=False, default=None)
    inward_date = serializers.DateField(allow_null=True, required=False, default=None)
    dispatch_date = serializers.DateField(allow_null=True, required=False, default=None)
    days_stored = serializers.IntegerField(allow_null=True, required=False, default=None)
    quantity = serializers.IntegerField(allow_null=True, required=False, default=None)
    unit = serializers.CharField(allow_blank=True, required=False, default='')
    rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False, default=None)


class InvoicePreviewPartyOutputSerializer(serializers.Serializer):
    party_id = serializers.IntegerField()
    party_name = serializers.CharField()
    party_code = serializers.CharField()
    lines = InvoicePreviewLineOutputSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    gst_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    gst_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
