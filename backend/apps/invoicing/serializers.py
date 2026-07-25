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
    pdf_url = serializers.SerializerMethodField()
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
            'rent_run_id',
            'invoice_date',
            'status',
            'subtotal',
            'gst_rate',
            'gst_amount',
            'total_amount',
            'pdf_url',
            'lines',
            'created_at',
            'updated_at',
        ]

    def get_pdf_url(self, obj) -> str | None:
        return obj.pdf_file.url if obj.pdf_file else None


class GenerateInvoicesInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    rent_run_id = serializers.IntegerField()
