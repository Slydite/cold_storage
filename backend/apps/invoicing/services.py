from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from libs.lookups import get_facility_or_raise
from libs.pdf import render_pdf
from libs.sequences import get_next_sequence_number
from apps.billing.services import compute_delivery_line_rent, days_stored
from apps.delivery.selectors import get_uninvoiced_delivery_lines
from .models import Invoice, InvoiceLine, Payment
from .selectors import get_invoice_by_id


@transaction.atomic
def generate_invoices_for_uninvoiced_deliveries(
    *,
    facility_id: int,
    party_id: int | None = None
) -> list[Invoice]:
    """
    Generate one Invoice per party for uninvoiced delivery lines (withdrawals).
    
    Implements Rule 3 (Only withdrawn stock is invoiced) and Anti-double-billing Invariant:
    - Queries uninvoiced delivery lines from POSTED delivery notes via get_uninvoiced_delivery_lines.
    - Computes rent using compute_delivery_line_rent pure calculator.
    - Bills GRN one-time receiving charge IN FULL on the FIRST invoice that includes any withdrawal
      from that GRN (if loading_charge_invoiced_at IS NULL).
    - Bills DN one-time loading charge on the invoice that includes that DN's lines (if loading_charge_invoiced_at IS NULL).
    - Marks DeliveryLine.invoiced_at and links DeliveryLine.invoice_line.
    """
    facility = get_facility_or_raise(facility_id)
    now = timezone.now()

    lines = list(get_uninvoiced_delivery_lines(facility_id=facility_id, party_id=party_id))
    if not lines:
        return []

    # Group delivery lines by party
    party_lines_map = {}
    for line in lines:
        party = line.delivery_note.party
        party_lines_map.setdefault(party, []).append(line)

    created_invoices = []
    for party, line_list in sorted(party_lines_map.items(), key=lambda item: item[0].id):
        inv_number = get_next_sequence_number(facility=facility, sequence_type='INV')
        
        # Prepare invoice items: list of tuples (description, amount, delivery_line_ref, grn_ref, dn_ref)
        invoice_items = []

        # 1. Rent for each delivery line
        for line in line_list:
            rent_amount = compute_delivery_line_rent(line)
            d_count = days_stored(line.lot.inward_date, line.delivery_note.dispatch_date)
            desc = f"Rent - Lot {line.lot.lot_number} ({line.lot.commodity.name}) - Qty: {line.qty} ({d_count} days)"
            invoice_items.append({
                'description': desc,
                'amount': rent_amount,
                'delivery_line': line
            })

        # 2. GRN receiving charges (billed once on first withdrawal)
        processed_grns = set()
        for line in line_list:
            grn = line.lot.grn
            if grn.id not in processed_grns and grn.loading_charge_invoiced_at is None:
                processed_grns.add(grn.id)
                charge = grn.computed_loading_charge()
                if charge > Decimal('0.00'):
                    invoice_items.append({
                        'description': f"Receiving Charge - GRN #{grn.grn_number}",
                        'amount': charge,
                        'grn': grn
                    })

        # 3. DN loading charges (billed once on invoice containing DN's lines)
        processed_dns = set()
        for line in line_list:
            dn = line.delivery_note
            if dn.id not in processed_dns and dn.loading_charge_invoiced_at is None:
                processed_dns.add(dn.id)
                charge = dn.computed_loading_charge()
                if charge > Decimal('0.00'):
                    invoice_items.append({
                        'description': f"Delivery Charge - DN #{dn.dn_number}",
                        'amount': charge,
                        'dn': dn
                    })

        subtotal = sum((item['amount'] for item in invoice_items), Decimal('0.00')).quantize(Decimal('0.01'))
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

        # Create InvoiceLine objects and mark DeliveryLine, GRN, DN as invoiced
        for item in invoice_items:
            inv_line = InvoiceLine(
                invoice=invoice,
                description=item['description'],
                amount=item['amount']
            )
            inv_line.full_clean()
            inv_line.save()

            if 'delivery_line' in item:
                dl = item['delivery_line']
                dl.invoiced_at = now
                dl.invoice_line = inv_line
                dl.save(update_fields=['invoiced_at', 'invoice_line'])

            if 'grn' in item:
                g = item['grn']
                g.loading_charge_invoiced_at = now
                g.save(update_fields=['loading_charge_invoiced_at'])

            if 'dn' in item:
                d = item['dn']
                d.loading_charge_invoiced_at = now
                d.save(update_fields=['loading_charge_invoiced_at'])

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


@transaction.atomic
def record_payment(
    *,
    invoice_id: int,
    amount: Decimal,
    payment_date: date,
    method: str = Payment.Method.CASH,
    reference: str = '',
    notes: str = ''
) -> Payment:
    """
    Record a payment against an invoice using row locking (select_for_update).

    Overpayment Decision & Reasoning:
    In real cold storage operations, customers frequently make payments in round figures or pay advances
    that may exceed individual invoice totals. Overpayment is allowed (amount_paid > total_amount) to preserve
    exact financial auditability of funds received. The invoice payment_status evaluates to 'PAID' and amount_due
    is clamped to Decimal('0.00'), while the Payment model stores the exact received amount.
    """
    try:
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    except Invoice.DoesNotExist:
        raise ValidationError(f"Invoice with ID {invoice_id} does not exist.")

    amount_dec = Decimal(str(amount)).quantize(Decimal('0.01'))
    if amount_dec <= Decimal('0.00'):
        raise ValidationError("Payment amount must be greater than zero.")

    if invoice.status == Invoice.Status.CANCELLED:
        raise ValidationError("Cannot record payment against a cancelled invoice.")

    payment = Payment(
        invoice=invoice,
        amount=amount_dec,
        payment_date=payment_date,
        method=method,
        reference=reference,
        notes=notes,
    )
    payment.full_clean()
    payment.save()
    return payment


@transaction.atomic
def delete_payment(*, payment_id: int) -> None:
    """
    Delete a payment record to correct a mistaken entry.
    Carries simple_history.HistoricalRecords on Payment so the operation remains fully auditable.
    """
    try:
        payment = Payment.objects.select_for_update().get(pk=payment_id)
    except Payment.DoesNotExist:
        raise ValidationError(f"Payment with ID {payment_id} does not exist.")

    payment.delete()

