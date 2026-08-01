"""
Data migration: backfill Invoice fields added in 0008.

For existing invoices:
- financial_year: derived from invoice_date using the FY label (1 Apr – 31 Mar).
- taxable_value: equal to subtotal (discount_amount defaults to 0.00, so taxable_value = subtotal – 0).
- cgst_amount / sgst_amount: treat existing invoices as intra-state, split gst_amount evenly.
  Odd paisa goes to CGST so that cgst_amount + sgst_amount == gst_amount exactly.
- igst_amount remains 0.00 (default, not touched).
- cgst_rate / sgst_rate: gst_rate / 2 (the legacy default was 18.00, so 9.00 each).

NOTE: document_type is not backfilled here — the column default ('TAX_INVOICE') is applied
by the AddField migration and is acceptable for historical rows where gst_amount > 0.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.db import migrations


def _fy_label(invoice_date):
    """Return FY label string e.g. '2026-27' for a given date."""
    if invoice_date.month >= 4:
        start_year = invoice_date.year
    else:
        start_year = invoice_date.year - 1
    end_year = start_year + 1
    return f"{start_year}-{end_year % 100:02d}"


def backfill_invoice_fields(apps, schema_editor):
    Invoice = apps.get_model('invoicing', 'Invoice')

    invoices = Invoice.objects.all()
    for inv in invoices:
        # 1. financial_year
        if inv.invoice_date:
            inv.financial_year = _fy_label(inv.invoice_date)
        else:
            inv.financial_year = ''

        # 2. taxable_value = subtotal (discount defaults 0.00)
        inv.taxable_value = inv.subtotal

        # 3. CGST / SGST: treat as intra-state, split evenly.
        #    Odd paisa goes to CGST so the sum reconciles exactly to gst_amount.
        half = (inv.gst_amount / Decimal('2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        remainder = inv.gst_amount - (half * 2)  # 0.00 or 0.01
        inv.cgst_amount = half + remainder        # odd paisa to CGST
        inv.sgst_amount = half
        # igst_amount left at default 0.00

        # 4. Component rates from legacy gst_rate
        if inv.gst_rate and inv.gst_rate > Decimal('0.00'):
            inv.cgst_rate = (inv.gst_rate / Decimal('2')).quantize(Decimal('0.01'))
            inv.sgst_rate = (inv.gst_rate / Decimal('2')).quantize(Decimal('0.01'))
        # igst_rate left at default 0.00

    Invoice.objects.bulk_update(
        invoices,
        ['financial_year', 'taxable_value', 'cgst_amount', 'sgst_amount',
         'cgst_rate', 'sgst_rate'],
    )


def reverse_backfill(apps, schema_editor):
    # Reversal clears the backfilled data; the AddField migration handles
    # column removal on full reversal.
    Invoice = apps.get_model('invoicing', 'Invoice')
    Invoice.objects.all().update(
        financial_year='',
        taxable_value=Decimal('0.00'),
        cgst_amount=Decimal('0.00'),
        sgst_amount=Decimal('0.00'),
        cgst_rate=Decimal('0.00'),
        sgst_rate=Decimal('0.00'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing', '0008_historicalinvoice_cgst_amount_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_invoice_fields, reverse_backfill),
    ]
