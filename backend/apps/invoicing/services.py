from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.core.exceptions import ValidationError

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
        party_name_snapshot = party.name if party.name else ''
        party_address_snapshot = party.address if party.address else ''
        facility_name_snapshot = facility.name if facility.name else ''
        facility_address_snapshot = facility.address if facility.address else ''
        facility_gstin_snapshot = facility.gstin if facility.gstin else ''

        invoice = Invoice(
            facility=facility,
            invoice_number=inv_number,
            party=party,
            rent_run=rent_run,
            invoice_date=date.today(),
            status=Invoice.Status.DRAFT,
            party_gstin_snapshot=party_gstin_snapshot,
            party_name_snapshot=party_name_snapshot,
            party_address_snapshot=party_address_snapshot,
            facility_name_snapshot=facility_name_snapshot,
            facility_address_snapshot=facility_address_snapshot,
            facility_gstin_snapshot=facility_gstin_snapshot,
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


def build_invoice_pdf(*, invoice_id: int) -> bytes:
    """
    Generate PDF bytes for an invoice on the fly using WeasyPrint.
    Performs no file I/O and no model save.

    Precedence: Snapshot values (party_name_snapshot, party_address_snapshot, party_gstin_snapshot,
    facility_name_snapshot, facility_address_snapshot, facility_gstin_snapshot) take precedence
    over live relations to ensure reprinted legal documents accurately reflect historical issue state.
    If a snapshot field is blank (e.g. for older invoices), it falls back to the live relation.
    """
    try:
        invoice = get_invoice_by_id(invoice_id)
    except Invoice.DoesNotExist:
        raise ValidationError(f"Invoice with ID {invoice_id} does not exist.")

    facility = invoice.facility
    party = invoice.party
    amount_in_words_str = _amount_in_words(invoice.total_amount)

    party_name = invoice.party_name_snapshot or (party.name if party else '')
    party_address = invoice.party_address_snapshot or (party.address if party else '')
    party_gstin = invoice.party_gstin_snapshot or (party.gstin if party else '')

    facility_display = {
        'name': invoice.facility_name_snapshot or (facility.name if facility else ''),
        'address': invoice.facility_address_snapshot or (facility.address if facility else ''),
        'gstin': invoice.facility_gstin_snapshot or (facility.gstin if facility else ''),
        'code': facility.code if facility else '',
        'phone': facility.phone if facility else '',
        'factory_phone': facility.factory_phone if facility else '',
        'bank_account_no': facility.bank_account_no if facility else '',
        'bank_ifsc': facility.bank_ifsc if facility else '',
    }

    context = {
        'invoice': invoice,
        'facility': facility_display,
        'party': party,
        'party_name': party_name,
        'party_address': party_address,
        'party_gstin': party_gstin,
        'amount_in_words': amount_in_words_str,
    }
    return render_pdf('pdf/invoice.html', context)


