from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage

from libs.lookups import get_facility_or_raise
from libs.pdf import render_pdf
from libs.sequences import get_next_sequence_number
from libs.fiscal import fy_label
from apps.billing.services import compute_delivery_line_rent, days_stored, compute_segmented_rent_details
from apps.delivery.selectors import get_uninvoiced_delivery_lines
from libs.choices import ChargeMode
from .models import Invoice, InvoiceLine, Payment
from .selectors import get_invoice_by_id


def _compute_tax_amounts(
    taxable_value: Decimal,
    cgst_rate: Decimal,
    sgst_rate: Decimal,
    igst_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Compute three independent GST component amounts: taxable_value * rate / 100,
    quantized to 2dp ROUND_HALF_UP. Nothing is split or halved automatically.
    Returns (cgst_amount, sgst_amount, igst_amount).
    """
    def _amt(rate):
        return (taxable_value * rate / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return _amt(cgst_rate), _amt(sgst_rate), _amt(igst_rate)


def _derive_document_type(cgst_amount, sgst_amount, igst_amount) -> str:
    """
    Derive the default document_type from whether any tax is present.
    Zero tax → Bill of Supply; any tax → Tax Invoice.

    NOTE: The tax position depends on what is actually stored and must be
    confirmed with the business's CA — the code implements a mechanism and
    does not give tax advice.
    """
    tax_total = cgst_amount + sgst_amount + igst_amount
    if tax_total == Decimal('0.00'):
        return Invoice.DocumentType.BILL_OF_SUPPLY
    return Invoice.DocumentType.TAX_INVOICE


def compute_invoice_totals(
    *,
    subtotal: Decimal,
    discount_amount: Decimal,
    cgst_rate: Decimal,
    sgst_rate: Decimal,
    igst_rate: Decimal,
) -> dict:
    """
    Single implementation of the money arithmetic on an invoice.

    Both the generation path and the adjust path go through here, so a draft
    that is later adjusted cannot end up computed differently from one that
    was generated with the same numbers.

    Discount comes off before tax: a discount shown on the face of the invoice
    reduces the taxable value under s.15(3)(a) of the CGST Act.
    """
    if discount_amount < Decimal('0.00'):
        raise ValidationError("Discount cannot be negative.")
    if discount_amount > subtotal:
        raise ValidationError(
            f"Discount ({discount_amount}) cannot exceed the invoice subtotal ({subtotal})."
        )

    taxable_value = (subtotal - discount_amount).quantize(Decimal('0.01'))
    cgst_amount, sgst_amount, igst_amount = _compute_tax_amounts(
        taxable_value, cgst_rate, sgst_rate, igst_rate
    )
    gst_amount = (cgst_amount + sgst_amount + igst_amount).quantize(Decimal('0.01'))

    return {
        'discount_amount': discount_amount,
        'taxable_value': taxable_value,
        # Kept in step with the components so the legacy total-rate field can
        # never contradict them.
        'gst_rate': (cgst_rate + sgst_rate + igst_rate).quantize(Decimal('0.01')),
        'cgst_rate': cgst_rate,
        'sgst_rate': sgst_rate,
        'igst_rate': igst_rate,
        'cgst_amount': cgst_amount,
        'sgst_amount': sgst_amount,
        'igst_amount': igst_amount,
        'gst_amount': gst_amount,
        'total_amount': (taxable_value + gst_amount).quantize(Decimal('0.01')),
    }


def build_invoice_items(
    *,
    party,
    line_list: list,
    default_gst_rate: Decimal | None = None,
    cgst_rate: Decimal | None = None,
    sgst_rate: Decimal | None = None,
    igst_rate: Decimal | None = None,
    discount_amount: Decimal | None = None,
) -> dict:
    """
    Build invoice line items, subtotal, GST rate, GST amount, and total amount
    for a list of delivery lines belonging to a party.

    Tax rates and discount may be supplied explicitly. When they are not, the
    facility's `default_gst_rate` is split evenly across CGST/SGST, which is
    what this business does for a local (intra-state) supply.

    Pure and side-effect free: does NOT write to database or mutate any model.
    """
    invoice_items = []

    # 1. Rent for each delivery line
    for line in line_list:
        segments = compute_segmented_rent_details(
            qty=line.qty,
            intake_rate=line.lot.rent_rate_per_unit,
            rate_changes=line.lot.rate_changes.all(),
            inward_date=line.lot.inward_date,
            out_date=line.delivery_note.dispatch_date,
        )
        for seg in segments:
            if len(segments) == 1:
                desc = f"Rent - Lot {line.lot.lot_number} ({line.lot.commodity.name}) - Qty: {line.qty} ({seg['days_stored']} days)"
            else:
                desc = f"Rent - Lot {line.lot.lot_number} ({line.lot.commodity.name}) - Qty: {line.qty} ({seg['days_stored']} days) [Segment: {seg['period_from']} to {seg['period_to']} @ Rs {seg['rate_per_unit']}]"
            
            invoice_items.append({
                'description': desc,
                'amount': seg['amount'],
                'delivery_line': line,
                'lot_number': line.lot.lot_number,
                'commodity_name': line.lot.commodity.name,
                'qty': line.qty,
                'inward_date': line.lot.inward_date,
                'dispatch_date': line.delivery_note.dispatch_date,
                'days_stored': seg['days_stored'],
                'quantity': line.qty,
                'unit': line.lot.unit,
                'rate_per_unit': seg['rate_per_unit'],
                # Charge head: rent lines carry the storage period billed
                'charge_type': InvoiceLine.ChargeType.RENT,
                'period_from': seg['period_from'],
                'period_to': seg['period_to'],
            })

    # 2. GRN loading/unloading charges (billed once on first withdrawal).
    # User-facing wording is "Loading/Unloading Charge" on the frontend and on
    # invoices; the field/method names (loading_charge, computed_loading_charge)
    # stay as-is - this is presentation wording only, not a schema change.
    processed_grns = set()
    for line in line_list:
        grn = line.lot.grn
        if grn.id not in processed_grns and grn.loading_charge_invoiced_at is None:
            processed_grns.add(grn.id)
            charge = grn.computed_loading_charge()
            if charge > Decimal('0.00'):
                is_per_unit = grn.loading_charge_mode == ChargeMode.PER_UNIT
                total_units = sum(lot.initial_qty for lot in grn.lots.all()) if is_per_unit else None
                invoice_items.append({
                    'description': f"Loading/Unloading Charge - GRN #{grn.grn_number}",
                    'amount': charge,
                    'grn': grn,
                    'lot_number': None,
                    'commodity_name': None,
                    'qty': None,
                    'inward_date': None,
                    'dispatch_date': None,
                    'days_stored': None,
                    'quantity': total_units,
                    'unit': 'UNITS' if is_per_unit else '',
                    'rate_per_unit': grn.loading_unloading_rate_per_bag if is_per_unit else None,
                    'charge_type': InvoiceLine.ChargeType.LOADING_UNLOADING,
                    'period_from': None,
                    'period_to': None,
                })

    # 3. DN loading/unloading charges (billed once on invoice containing DN's lines)
    processed_dns = set()
    for line in line_list:
        dn = line.delivery_note
        if dn.id not in processed_dns and dn.loading_charge_invoiced_at is None:
            processed_dns.add(dn.id)
            charge = dn.computed_loading_charge()
            if charge > Decimal('0.00'):
                is_per_unit = dn.loading_charge_mode == ChargeMode.PER_UNIT
                total_units = sum(dl.qty for dl in dn.lines.all()) if is_per_unit else None
                invoice_items.append({
                    'description': f"Loading/Unloading Charge - DN #{dn.dn_number}",
                    'amount': charge,
                    'dn': dn,
                    'lot_number': None,
                    'commodity_name': None,
                    'qty': None,
                    'inward_date': None,
                    'dispatch_date': None,
                    'days_stored': None,
                    'quantity': total_units,
                    'unit': 'UNITS' if is_per_unit else '',
                    'rate_per_unit': dn.loading_unloading_rate_per_unit if is_per_unit else None,
                    'charge_type': InvoiceLine.ChargeType.LOADING_UNLOADING,
                    'period_from': None,
                    'period_to': None,
                })

    subtotal = sum((item['amount'] for item in invoice_items), Decimal('0.00')).quantize(Decimal('0.01'))

    # When no explicit split is given, fall back to the facility default and
    # treat the supply as intra-state, which is overwhelmingly what this
    # business does. Any of the three can be overridden per invoice.
    if cgst_rate is None and sgst_rate is None and igst_rate is None:
        base_rate = default_gst_rate if default_gst_rate is not None else Decimal('18.00')
        cgst_rate = (base_rate / 2).quantize(Decimal('0.01'))
        sgst_rate = (base_rate / 2).quantize(Decimal('0.01'))
        igst_rate = Decimal('0.00')
    else:
        cgst_rate = cgst_rate if cgst_rate is not None else Decimal('0.00')
        sgst_rate = sgst_rate if sgst_rate is not None else Decimal('0.00')
        igst_rate = igst_rate if igst_rate is not None else Decimal('0.00')

    totals = compute_invoice_totals(
        subtotal=subtotal,
        discount_amount=discount_amount if discount_amount is not None else Decimal('0.00'),
        cgst_rate=cgst_rate,
        sgst_rate=sgst_rate,
        igst_rate=igst_rate,
    )

    return {
        'items': invoice_items,
        'subtotal': subtotal,
        'document_type': _derive_document_type(
            totals['cgst_amount'], totals['sgst_amount'], totals['igst_amount']
        ),
        **totals,
    }


def preview_uninvoiced_charges(
    *,
    facility_id: int,
    party_id: int | None = None
) -> list[dict]:
    """
    Preview pending charges for uninvoiced delivery lines grouped by party without creating invoices.
    
    Strictly read-only: does NOT write to database, does NOT set DeliveryLine.invoiced_at,
    and does NOT consume invoice sequence numbers.
    """
    facility = get_facility_or_raise(facility_id)
    lines = list(get_uninvoiced_delivery_lines(facility_id=facility_id, party_id=party_id))
    if not lines:
        return []

    party_lines_map = {}
    for line in lines:
        party = line.delivery_note.party
        party_lines_map.setdefault(party, []).append(line)

    previews = []
    for party, line_list in sorted(party_lines_map.items(), key=lambda item: item[0].id):
        items_data = build_invoice_items(
            party=party,
            line_list=line_list,
            default_gst_rate=facility.default_gst_rate,
        )

        line_breakdown = []
        for item in items_data['items']:
            line_breakdown.append({
                'description': item['description'],
                'amount': item['amount'],
                'lot_number': item['lot_number'],
                'commodity_name': item['commodity_name'],
                'qty': item['qty'],
                'inward_date': item['inward_date'],
                'dispatch_date': item['dispatch_date'],
                'days_stored': item['days_stored'],
                'quantity': item['quantity'],
                'unit': item['unit'],
                'rate_per_unit': item['rate_per_unit'],
            })

        previews.append({
            'party_id': party.id,
            'party_name': party.name,
            'party_code': party.code,
            'lines': line_breakdown,
            'subtotal': items_data['subtotal'],
            'gst_rate': items_data['gst_rate'],
            'gst_amount': items_data['gst_amount'],
            'total_amount': items_data['total_amount'],
        })

    return previews


@transaction.atomic
def generate_invoices_for_uninvoiced_deliveries(
    *,
    facility_id: int,
    party_id: int | None = None,
    cgst_rate: Decimal | None = None,
    sgst_rate: Decimal | None = None,
    igst_rate: Decimal | None = None,
    discount_amount: Decimal | None = None,
) -> list[Invoice]:
    """
    Generate one Invoice per party for uninvoiced delivery lines (withdrawals).
    
    Implements Rule 3 (Only withdrawn stock is invoiced) and Anti-double-billing Invariant:
    - Queries uninvoiced delivery lines from POSTED delivery notes via get_uninvoiced_delivery_lines.
    - Uses build_invoice_items to compute rent, receiving charges, loading charges, subtotals, and GST.
    - Marks DeliveryLine.invoiced_at and links DeliveryLine.invoice_line.
    """
    facility = get_facility_or_raise(facility_id)
    now = timezone.now()
    today = date.today()

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
        items_data = build_invoice_items(
            party=party,
            line_list=line_list,
            default_gst_rate=facility.default_gst_rate,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            igst_rate=igst_rate,
            discount_amount=discount_amount,
        )
        invoice_items = items_data['items']

        # FY-scoped invoice numbering (GST Rule 46(b))
        fy = fy_label(today)
        inv_number = get_next_sequence_number(
            facility=facility,
            sequence_type='INV',
            financial_year=fy,
        )

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
            invoice_date=today,
            status=Invoice.Status.DRAFT,
            party_gstin_snapshot=party_gstin_snapshot,
            party_name_snapshot=party_name_snapshot,
            party_address_snapshot=party_address_snapshot,
            facility_name_snapshot=facility_name_snapshot,
            facility_address_snapshot=facility_address_snapshot,
            facility_gstin_snapshot=facility_gstin_snapshot,
            financial_year=fy,
            subtotal=items_data['subtotal'],
            discount_amount=items_data['discount_amount'],
            taxable_value=items_data['taxable_value'],
            gst_rate=items_data['gst_rate'],
            gst_amount=items_data['gst_amount'],
            cgst_rate=items_data['cgst_rate'],
            sgst_rate=items_data['sgst_rate'],
            igst_rate=items_data['igst_rate'],
            cgst_amount=items_data['cgst_amount'],
            sgst_amount=items_data['sgst_amount'],
            igst_amount=items_data['igst_amount'],
            total_amount=items_data['total_amount'],
            document_type=items_data['document_type'],
        )
        invoice.full_clean()
        invoice.save()

        # Create InvoiceLine objects and mark DeliveryLine, GRN, DN as invoiced
        for item in invoice_items:
            sac_code = InvoiceLine.DEFAULT_SAC_CODES.get(item.get('charge_type', InvoiceLine.ChargeType.OTHER), '')
            inv_line = InvoiceLine(
                invoice=invoice,
                description=item['description'],
                amount=item['amount'],
                quantity=item.get('quantity'),
                unit=item.get('unit') or '',
                rate_per_unit=item.get('rate_per_unit'),
                charge_type=item.get('charge_type', InvoiceLine.ChargeType.OTHER),
                sac_code=sac_code,
                period_from=item.get('period_from'),
                period_to=item.get('period_to'),
            )
            inv_line.full_clean()
            inv_line.save()

            if item.get('delivery_line'):
                dl = item['delivery_line']
                dl.invoiced_at = now
                dl.invoice_line = inv_line
                dl.save(update_fields=['invoiced_at', 'invoice_line'])

            if item.get('grn'):
                g = item['grn']
                g.loading_charge_invoiced_at = now
                g.save(update_fields=['loading_charge_invoiced_at'])

            if item.get('dn'):
                d = item['dn']
                d.loading_charge_invoiced_at = now
                d.save(update_fields=['loading_charge_invoiced_at'])

        created_invoices.append(get_invoice_by_id(invoice.id))

    return created_invoices


@transaction.atomic
def adjust_invoice(*, invoice_id: int, **changes) -> Invoice:
    """
    Apply the owner's manual tax and discount decisions to a DRAFT invoice and
    recompute its money.

    Only DRAFT invoices can be adjusted. Once POSTED an invoice is a document
    that has been issued to a customer, and editing its numbers after the fact
    is exactly what an audit trail exists to prevent.

    Accepted keys (all optional; omitted keys are left unchanged):
    discount_amount, discount_reason, cgst_rate, sgst_rate, igst_rate,
    place_of_supply, document_type, is_reverse_charge, exemption_reason.
    """
    try:
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    except Invoice.DoesNotExist:
        raise ValidationError(f"Invoice with ID {invoice_id} does not exist.")

    if invoice.status != Invoice.Status.DRAFT:
        raise ValidationError(
            f"Cannot adjust Invoice: current status is '{invoice.status}', must be DRAFT."
        )

    passthrough = (
        'discount_reason', 'place_of_supply', 'is_reverse_charge', 'exemption_reason',
    )
    for field in passthrough:
        if field in changes and changes[field] is not None:
            setattr(invoice, field, changes[field])

    for field in ('cgst_rate', 'sgst_rate', 'igst_rate', 'discount_amount'):
        if field in changes and changes[field] is not None:
            setattr(invoice, field, changes[field])

    totals = compute_invoice_totals(
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        cgst_rate=invoice.cgst_rate,
        sgst_rate=invoice.sgst_rate,
        igst_rate=invoice.igst_rate,
    )
    for field, value in totals.items():
        setattr(invoice, field, value)

    # An explicit document_type wins; otherwise follow the new tax total.
    if changes.get('document_type'):
        invoice.document_type = changes['document_type']
    else:
        invoice.document_type = _derive_document_type(
            totals['cgst_amount'], totals['sgst_amount'], totals['igst_amount']
        )

    invoice.full_clean()
    invoice.save()
    return get_invoice_by_id(invoice.id)


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


@transaction.atomic
def email_invoice_to_party(*, invoice_id: int) -> None:
    """
    Build the Invoice PDF, send it to the party's email address, and record the timestamp.
    """
    try:
        invoice = Invoice.objects.select_for_update().select_related('facility', 'party').get(pk=invoice_id)
    except Invoice.DoesNotExist:
        raise ValidationError(f"Invoice with ID {invoice_id} does not exist.")

    party = invoice.party
    if not party.email or not party.email.strip():
        raise ValidationError(f"Cannot email Invoice: Party '{party.name}' does not have an email address on file.")

    pdf_bytes = build_invoice_pdf(invoice_id=invoice_id)

    subject = f"Invoice {invoice.invoice_number} from {invoice.facility.name}"
    body = (
        f"Dear {party.name},\n\n"
        f"Please find attached Invoice {invoice.invoice_number} from {invoice.facility.name} "
        f"dated {invoice.invoice_date.strftime('%d-%m-%Y')}.\n\n"
        f"Regards,\n"
        f"{invoice.facility.name}"
    )

    email = EmailMessage(
        subject=subject,
        body=body,
        to=[party.email.strip()],
    )
    email.attach(f"{invoice.invoice_number}.pdf", pdf_bytes, 'application/pdf')
    email.send()

    invoice.last_emailed_at = timezone.now()
    invoice.save()
