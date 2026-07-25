from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from libs.lookups import get_facility_or_raise
from libs.pdf import render_pdf
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

    This is business logic, not a rendering concern -- it stayed behind when PDF
    generation moved from reportlab to WeasyPrint templates.
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
    Generate a PDF for an invoice using WeasyPrint and store it in invoice.pdf_file.
    Returns invoice.pdf_file.url as a string.
    """
    try:
        invoice = get_invoice_by_id(invoice_id)
    except Invoice.DoesNotExist:
        raise ValidationError(f"Invoice with ID {invoice_id} does not exist.")

    facility = invoice.facility
    party = invoice.party
    amount_in_words_str = _amount_in_words(invoice.total_amount)

    context = {
        'invoice': invoice,
        'facility': facility,
        'party': party,
        'amount_in_words': amount_in_words_str,
    }
    pdf_bytes = render_pdf('pdf/invoice.html', context)

    filename = f"{invoice.invoice_number}.pdf"
    with transaction.atomic():
        invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    return invoice.pdf_file.url

