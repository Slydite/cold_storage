from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

from libs.lookups import get_facility_or_raise
from libs.sequences import get_next_sequence_number
from apps.billing.models import RentRun
from .models import Invoice, InvoiceLine
from .selectors import get_invoice_by_id


@transaction.atomic
def generate_invoices_for_rent_run(*, facility_id: int, rent_run_id: int) -> list[Invoice]:
    """
    Generate one Invoice per party for all lines in a POSTED RentRun.
    """
    facility = get_facility_or_raise(facility_id)

    try:
        rent_run = RentRun.objects.select_for_update().get(pk=rent_run_id, facility=facility)
    except RentRun.DoesNotExist:
        raise ValidationError(f"RentRun with ID {rent_run_id} does not exist in facility {facility_id}.")

    if rent_run.status != RentRun.Status.POSTED:
        raise ValidationError(f"Cannot generate invoices: RentRun current status is '{rent_run.status}', must be POSTED.")

    if Invoice.objects.filter(rent_run=rent_run).exists():
        raise ValidationError("An invoice has already been generated for this rent run.")

    rent_run_lines = rent_run.lines.select_related('party', 'lot', 'lot__commodity').all()

    # Group lines by party
    party_lines_map = {}
    for line in rent_run_lines:
        party_lines_map.setdefault(line.party, []).append(line)

    created_invoices = []
    for party, lines in sorted(party_lines_map.items(), key=lambda item: item[0].id):
        inv_number = get_next_sequence_number(facility=facility, sequence_type='INV')
        subtotal = sum((Decimal(line.amount) for line in lines), Decimal('0.00')).quantize(Decimal('0.01'))
        gst_rate = Decimal('18.00')
        gst_amount = (subtotal * gst_rate / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_amount = subtotal + gst_amount
        party_gstin_snapshot = party.gstin if party.gstin else ''

        invoice = Invoice(
            facility=facility,
            invoice_number=inv_number,
            party=party,
            rent_run=rent_run,
            invoice_date=date.today(),
            status=Invoice.Status.DRAFT,
            party_gstin_snapshot=party_gstin_snapshot,
            subtotal=subtotal,
            gst_rate=gst_rate,
            gst_amount=gst_amount,
            total_amount=total_amount
        )
        invoice.full_clean()
        invoice.save()

        for line in lines:
            inv_line = InvoiceLine(
                invoice=invoice,
                description=f"Rent - {line.lot.lot_number} ({line.lot.commodity.name}) - {line.days_stored} days",
                rent_run_line=line,
                amount=line.amount
            )
            inv_line.full_clean()
            inv_line.save()

        created_invoices.append(get_invoice_by_id(invoice.id))

    return created_invoices


@transaction.atomic
def post_invoice(*, invoice_id: int) -> Invoice:
    """
    Transition an Invoice from DRAFT to POSTED using row lock.
    """
    try:
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    except Invoice.DoesNotExist:
        raise ValidationError(f"Invoice with ID {invoice_id} does not exist.")

    if invoice.status != Invoice.Status.DRAFT:
        raise ValidationError(f"Cannot post Invoice: current status is '{invoice.status}', must be DRAFT.")

    invoice.status = Invoice.Status.POSTED
    invoice.full_clean()
    invoice.save()
    return get_invoice_by_id(invoice.id)


@transaction.atomic
def cancel_invoice(*, invoice_id: int) -> Invoice:
    """
    Transition an Invoice from DRAFT to CANCELLED using row lock.
    """
    try:
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    except Invoice.DoesNotExist:
        raise ValidationError(f"Invoice with ID {invoice_id} does not exist.")

    if invoice.status != Invoice.Status.DRAFT:
        raise ValidationError(f"Cannot cancel Invoice: current status is '{invoice.status}', must be DRAFT.")

    invoice.status = Invoice.Status.CANCELLED
    invoice.full_clean()
    invoice.save()
    return get_invoice_by_id(invoice.id)


def generate_invoice_pdf(*, invoice_id: int) -> str:
    """
    Generate a PDF for an invoice using ReportLab and store it in invoice.pdf_file.
    Returns invoice.pdf_file.url as a string.
    """
    try:
        invoice = get_invoice_by_id(invoice_id)
    except Invoice.DoesNotExist:
        raise ValidationError(f"Invoice with ID {invoice_id} does not exist.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    elements = []

    facility = invoice.facility
    party = invoice.party

    # Title
    elements.append(Paragraph("<b>TAX INVOICE</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # Header section
    header_data = [
        [
            Paragraph(f"<b>{facility.name}</b><br/>{facility.address or facility.code}", styles['Normal']),
            Paragraph(
                f"<b>Invoice No:</b> {invoice.invoice_number}<br/>"
                f"<b>Date:</b> {invoice.invoice_date}<br/>"
                f"<b>Status:</b> {invoice.status}",
                styles['Normal']
            )
        ]
    ]
    header_table = Table(header_data, colWidths=[270, 270])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 16))

    # Bill-to block
    gstin_display = invoice.party_gstin_snapshot if invoice.party_gstin_snapshot else "Not provided"
    bill_to_data = [
        [
            Paragraph(
                f"<b>Billed To:</b><br/>"
                f"{party.name}<br/>"
                f"{party.address or ''}<br/>"
                f"<b>GSTIN:</b> {gstin_display}",
                styles['Normal']
            )
        ]
    ]
    bill_to_table = Table(bill_to_data, colWidths=[540])
    bill_to_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(bill_to_table)
    elements.append(Spacer(1, 16))

    # Line items
    lines = invoice.lines.all()
    table_data = [["Description", "Amount (₹)"]]
    for line in lines:
        table_data.append([
            Paragraph(line.description, styles['Normal']),
            f"{line.amount:.2f}"
        ])

    table_data.append(["Subtotal", f"{invoice.subtotal:.2f}"])
    table_data.append([f"GST ({invoice.gst_rate}%)", f"{invoice.gst_amount:.2f}"])
    table_data.append(["Total Amount", f"{invoice.total_amount:.2f}"])

    items_table = Table(table_data, colWidths=[400, 140])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(items_table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"{invoice.invoice_number}.pdf"
    with transaction.atomic():
        invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    return invoice.pdf_file.url
