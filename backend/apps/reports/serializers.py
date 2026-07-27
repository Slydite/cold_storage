from rest_framework import serializers
from apps.invoicing.models import Payment


class PaymentRegisterOutputSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    invoice_id = serializers.IntegerField(source='invoice.id', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    invoice_total = serializers.DecimalField(source='invoice.total_amount', max_digits=12, decimal_places=2, read_only=True)
    party_id = serializers.IntegerField(source='invoice.party.id', read_only=True)
    party_name = serializers.CharField(source='invoice.party.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_date',
            'amount',
            'method',
            'method_display',
            'reference',
            'notes',
            'invoice_id',
            'invoice_number',
            'invoice_total',
            'party_id',
            'party_name',
        ]


class PaymentRegisterResponseSerializer(serializers.Serializer):
    results = PaymentRegisterOutputSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
