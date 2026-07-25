from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from typing import Any

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


def _safe_pdf_text(val: Any) -> str:
    if val is None:
        return ""
    s = str(val)
    return s.encode('latin-1', errors='replace').decode('latin-1')


UNITS = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen"
]
TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
]


def _number_to_words(n: int) -> str:
    if n == 0:
        return ""
    elif n < 20:
        return UNITS[n]
    elif n < 100:
        rem = n % 10
        return TENS[n // 10] + (f" {UNITS[rem]}" if rem != 0 else "")
    elif n < 1000:
        rem = n % 100
        return UNITS[n // 100] + " Hundred" + (f" and {_number_to_words(rem)}" if rem != 0 else "")
    elif n < 100000:
        rem = n % 1000
        return _number_to_words(n // 1000) + " Thousand" + (f" {_number_to_words(rem)}" if rem != 0 else "")
    elif n < 10000000:
        rem = n % 100000
        return _number_to_words(n // 100000) + " Lakh" + (f" {_number_to_words(rem)}" if rem != 0 else "")
    else:
        rem = n % 10000000
        return _number_to_words(n // 10000000) + " Crore" + (f" {_number_to_words(rem)}" if rem != 0 else "")


def _amount_in_words(amount: Decimal) -> str:
    """
    Convert a Decimal amount to words using the Indian numbering system.
    e.g. 145200 -> "Rupees One Lakh Forty Five Thousand Two Hundred only"
    """
    if amount is None:
        return "Rupees Zero only"

    dec_amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    rupees = int(dec_amount)
    paise = int((dec_amount - Decimal(rupees)) * 100)

    if rupees == 0 and paise == 0:
        return "Rupees Zero only"

    rupee_words = _number_to_words(rupees) if rupees > 0 else ""
    paise_words = _number_to_words(paise) if paise > 0 else ""

    parts = []
    if rupee_words:
        parts.append(f"Rupees {rupee_words}")
    if paise_words:
        parts.append(f"{paise_words} Paise")

    return " and ".join(parts) + " only"


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

    fac_name = _safe_pdf_text(facility.name)
    fac_addr = _safe_pdf_text(facility.address or facility.code)
    fac_gstin = _safe_pdf_text(getattr(facility, 'gstin', ''))
    fac_phone = _safe_pdf_text(getattr(facility, 'phone', ''))
    fac_factory = _safe_pdf_text(getattr(facility, 'factory_phone', ''))
    fac_bank = _safe_pdf_text(getattr(facility, 'bank_account_no', ''))
    fac_ifsc = _safe_pdf_text(getattr(facility, 'bank_ifsc', ''))

    header_left = f"<b>{fac_name}</b><br/>{fac_addr}"
    contact_parts = []
    if fac_gstin: contact_parts.append(f"<b>GSTIN:</b> {fac_gstin}")
    if fac_phone: contact_parts.append(f"<b>Mob:</b> {fac_phone}")
    if fac_factory: contact_parts.append(f"<b>Factory:</b> {fac_factory}")
    if fac_bank: contact_parts.append(f"<b>Bank A/c:</b> {fac_bank}")
    if fac_ifsc: contact_parts.append(f"<b>IFSC:</b> {fac_ifsc}")
    if contact_parts:
        header_left += "<br/>" + " | ".join(contact_parts)

    header_right = (
        f"<b>TAX INVOICE</b><br/>"
        f"<b>Invoice No:</b> {_safe_pdf_text(invoice.invoice_number)}<br/>"
        f"<b>Date:</b> {invoice.invoice_date}<br/>"
        f"<b>Status:</b> {invoice.status}"
    )

    header_table = Table([[Paragraph(header_left, styles['Normal']), Paragraph(header_right, styles['Normal'])]], colWidths=[310, 230])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # Bill-To block
    # NOTE: party_gstin_snapshot is the legally-correct snapshot of party GSTIN at issue time;
    # do NOT read live party.gstin directly for the tax invoice line.
    gstin_display = _safe_pdf_text(invoice.party_gstin_snapshot) if invoice.party_gstin_snapshot else "Not provided"
    party_name = _safe_pdf_text(party.name)
    party_addr = _safe_pdf_text(getattr(party, 'address', ''))

    bill_to_text = (
        f"<b>Billed To:</b><br/>"
        f"<b>{party_name}</b><br/>"
    )
    if party_addr:
        bill_to_text += f"{party_addr}<br/>"
    bill_to_text += f"<b>GSTIN:</b> {gstin_display}"

    if invoice.rent_run:
        bill_to_text += f"<br/><b>Billed Period:</b> {invoice.rent_run.period_start} to {invoice.rent_run.period_end}"

    bill_to_table = Table([[Paragraph(bill_to_text, styles['Normal'])]], colWidths=[540])
    bill_to_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(bill_to_table)
    elements.append(Spacer(1, 12))

    lines = invoice.lines.all()
    table_data = [["S.No.", "Description", "Amount (₹)"]]
    for idx, line in enumerate(lines, start=1):
        table_data.append([
            str(idx),
            Paragraph(_safe_pdf_text(line.description), styles['Normal']),
            f"{line.amount:.2f}"
        ])

    table_data.append(["", "Subtotal", f"{invoice.subtotal:.2f}"])
    table_data.append(["", f"GST ({invoice.gst_rate}%)", f"{invoice.gst_amount:.2f}"])
    table_data.append(["", "Total Amount", f"{invoice.total_amount:.2f}"])

    items_table = Table(table_data, colWidths=[40, 360, 140])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -4), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -4), 0.5, colors.grey),
        ('GRID', (1, -3), (2, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, -3), (1, -1), 'RIGHT'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10))

    words_text = _amount_in_words(invoice.total_amount)
    elements.append(Paragraph(f"<b>Amount in Words:</b> {words_text}", styles['Normal']))
    elements.append(Spacer(1, 16))

    footer_right = f"<b>For: {fac_name}</b><br/><br/><br/><b>Authorised Signatory</b>"
    footer_table = Table([["", Paragraph(footer_right, styles['Normal'])]], colWidths=[270, 270])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(footer_table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"{invoice.invoice_number}.pdf"
    with transaction.atomic():
        invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    return invoice.pdf_file.url
