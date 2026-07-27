from rest_framework import serializers
from .models import Invoice, InvoiceLine, Payment


class InvoiceLineOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            'id',
            'description',
            'amount',
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
            'party_gstin_snapshot',
            'party_name_snapshot',
            'party_address_snapshot',
            'facility_name_snapshot',
            'facility_address_snapshot',
            'facility_gstin_snapshot',
            'invoice_date',
            'status',
            'subtotal',
            'gst_rate',
            'gst_amount',
            'total_amount',
            'amount_paid',
            'amount_due',
            'payment_status',
            'payments',
            'lines',
            'created_at',
            'updated_at',
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

