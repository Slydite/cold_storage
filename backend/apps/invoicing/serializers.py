from rest_framework import serializers
from .models import Invoice, InvoiceLine


class InvoiceLineOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            'id',
            'description',
            'amount',
            'rent_run_line_id',
        ]


class InvoiceOutputSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source='party.name', read_only=True)
    lines = InvoiceLineOutputSerializer(many=True, read_only=True)

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
            'rent_run_id',
            'invoice_date',
            'status',
            'subtotal',
            'gst_rate',
            'gst_amount',
            'total_amount',
            'lines',
            'created_at',
            'updated_at',
        ]


class GenerateInvoicesInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    rent_run_id = serializers.IntegerField()
