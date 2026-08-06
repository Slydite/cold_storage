from typing import List, Dict, Any
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.mail import EmailMessage

from libs.sequences import get_next_sequence_number
from libs.lot_numbers import build_voucher_number, is_valid_voucher_number
from libs.lookups import get_facility_or_raise, get_party_or_raise
from libs.pdf import render_pdf
from libs.choices import ChargeMode
from libs.sanitizers import clean_text, title_name, upper_code
from apps.inventory.models import Lot, Sequence
from apps.inventory.services import withdraw_stock_from_lot
from .models import DeliveryNote, DeliveryLine


@transaction.atomic
def create_delivery_note(
    *,
    facility_id: int,
    party_id: int,
    dispatch_date: date,
    vehicle_number: str = '',
    driver_name: str = '',
    transporter: str = '',
    remarks: str = '',
    loading_charge: Decimal = Decimal('0.00'),
    loading_unloading_rate_per_unit: Decimal = Decimal('0.00'),
    loading_charge_mode: str = ChargeMode.FLAT,
    status: str = DeliveryNote.Status.DRAFT,
    lines: List[Dict[str, Any]] = None,
    dn_number: str = None,
    validate_dn_number_format: bool = True
) -> DeliveryNote:
    """
    Create a Delivery Note with lines.
    Validates lots belong to the same facility and line qty > 0.
    Fetches lots in one query (avoiding N+1).
    Stock is withdrawn ONLY when status is POSTED.
    """
    facility = get_facility_or_raise(facility_id)
    party = get_party_or_raise(party_id, facility)

    if status not in DeliveryNote.Status.values:
        raise ValidationError(f"Invalid status: {status}. Allowed: {DeliveryNote.Status.values}")

    if loading_charge_mode not in ChargeMode.values:
        raise ValidationError(f"Invalid loading_charge_mode: {loading_charge_mode}. Allowed: {ChargeMode.values}")

    vehicle_number = upper_code(vehicle_number)
    driver_name = title_name(driver_name)
    transporter = title_name(transporter)
    remarks = clean_text(remarks)


    lines = lines or []
    lot_ids = [line_data.get('lot_id') for line_data in lines if line_data.get('lot_id') is not None]

    lots_by_id = Lot.objects.in_bulk(lot_ids, field_name='pk')
    lots_by_id = {
        lid: lot for lid, lot in lots_by_id.items()
        if lot.facility_id == facility.id
    }

    validated_lines = []
    for line_data in lines:
        lot_id = line_data.get('lot_id')
        qty = line_data.get('qty', 0)

        lot = lots_by_id.get(lot_id)
        if lot is None:
            raise ValidationError(f"Lot with ID {lot_id} does not exist in facility {facility_id}.")

        if qty <= 0:
            raise ValidationError(f"Quantity for lot '{lot.lot_number}' must be greater than 0.")

        validated_lines.append((lot, qty))

    if dn_number:
        if validate_dn_number_format:
            if not is_valid_voucher_number(dn_number):
                raise ValidationError(
                    f"Invalid DN number format: {dn_number}. "
                    f"Expected YYYYMMDD-SSSSS."
                )
    else:
        seq, created = Sequence.objects.select_for_update().get_or_create(
            facility=facility,
            sequence_type='DN_VNO',
            defaults={'prefix': '', 'current_value': 2905}
        )
        if not created and seq.current_value == 0:
            seq.current_value = 2905
            seq.save(update_fields=['current_value'])

        seq.current_value += 1
        seq.save(update_fields=['current_value'])

        dn_number, _warning = build_voucher_number(doc_date=dispatch_date, voucher_no=seq.current_value)

    dn = DeliveryNote(
        facility=facility,
        dn_number=dn_number,
        party=party,
        dispatch_date=dispatch_date,
        vehicle_number=vehicle_number,
        driver_name=driver_name,
        transporter=transporter,
        remarks=remarks,
        loading_charge=loading_charge,
        loading_unloading_rate_per_unit=loading_unloading_rate_per_unit,
        loading_charge_mode=loading_charge_mode,
        status=DeliveryNote.Status.DRAFT
    )
    dn.full_clean()
    dn.save()

    for lot, qty in validated_lines:
        line = DeliveryLine(
            facility=facility,
            delivery_note=dn,
            lot=lot,
            qty=qty
        )
        line.full_clean()
        line.save()

    if status == DeliveryNote.Status.POSTED:
        return post_delivery_note(delivery_note_id=dn.id)
    elif status == DeliveryNote.Status.CANCELLED:
        return cancel_delivery_note(delivery_note_id=dn.id)

    return dn


@transaction.atomic
def post_delivery_note(*, delivery_note_id: int) -> DeliveryNote:
    """
    Transition a Delivery Note from DRAFT to POSTED using select_for_update() row lock.
    Withdraws stock from each lot via inventory's withdraw_stock_from_lot service.
    Populates balance_after for each line immediately after successful stock withdrawal.
    If any line fails, transaction rolls back completely.
    """
    try:
        dn = DeliveryNote.objects.select_for_update().get(pk=delivery_note_id)
    except DeliveryNote.DoesNotExist:
        raise ValidationError(f"Delivery Note with ID {delivery_note_id} does not exist.")

    if dn.status != DeliveryNote.Status.DRAFT:
        raise ValidationError(f"Cannot post Delivery Note: current status is '{dn.status}', must be DRAFT.")

    for line in dn.lines.select_related('lot').all():
        updated_lot = withdraw_stock_from_lot(lot_id=line.lot_id, qty_to_withdraw=line.qty)
        line.balance_after = updated_lot.remaining_qty
        line.save(update_fields=['balance_after'])

    dn.status = DeliveryNote.Status.POSTED
    dn.full_clean()
    dn.save()
    return dn


@transaction.atomic
def cancel_delivery_note(*, delivery_note_id: int) -> DeliveryNote:
    """
    Transition a Delivery Note from DRAFT to CANCELLED using select_for_update() row lock.
    Only DRAFT notes can be cancelled.
    """
    try:
        dn = DeliveryNote.objects.select_for_update().get(pk=delivery_note_id)
    except DeliveryNote.DoesNotExist:
        raise ValidationError(f"Delivery Note with ID {delivery_note_id} does not exist.")

    if dn.status != DeliveryNote.Status.DRAFT:
        raise ValidationError(f"Cannot cancel Delivery Note: current status is '{dn.status}', must be DRAFT.")

    dn.status = DeliveryNote.Status.CANCELLED
    dn.full_clean()
    dn.save()
    return dn


def build_delivery_note_pdf(*, delivery_note_id: int) -> bytes:
    """
    Generate PDF bytes for a Delivery Note (Delivery Challan) matching real form layout via WeasyPrint.
    Performs no file I/O and no model save.
    """
    try:
        dn = DeliveryNote.objects.select_related('facility', 'party').prefetch_related('lines__lot__commodity').get(pk=delivery_note_id)
    except DeliveryNote.DoesNotExist:
        raise ValidationError(f"Delivery Note with ID {delivery_note_id} does not exist.")

    facility = dn.facility
    party = dn.party
    total_qty = sum(line.qty for line in dn.lines.all())

    context = {
        'dn': dn,
        'facility': facility,
        'party': party,
        'total_qty': total_qty,
    }
    return render_pdf('pdf/delivery_note.html', context)


@transaction.atomic
def email_delivery_note_to_party(*, delivery_note_id: int) -> None:
    """
    Build the Delivery Note PDF, send it to the party's email address, and record the timestamp.
    """
    try:
        dn = DeliveryNote.objects.select_for_update().select_related('facility', 'party').get(pk=delivery_note_id)
    except DeliveryNote.DoesNotExist:
        raise ValidationError(f"Delivery Note with ID {delivery_note_id} does not exist.")

    party = dn.party
    if not party.email or not party.email.strip():
        raise ValidationError(f"Cannot email Delivery Note: Party '{party.name}' does not have an email address on file.")

    pdf_bytes = build_delivery_note_pdf(delivery_note_id=delivery_note_id)

    subject = f"Delivery Note {dn.dn_number} from {dn.facility.name}"
    body = (
        f"Dear {party.name},\n\n"
        f"Please find attached Delivery Note {dn.dn_number} from {dn.facility.name} "
        f"dated {dn.dispatch_date.strftime('%d-%m-%Y')}.\n\n"
        f"Regards,\n"
        f"{dn.facility.name}"
    )

    email = EmailMessage(
        subject=subject,
        body=body,
        to=[party.email.strip()],
    )
    email.attach(f"{dn.dn_number}.pdf", pdf_bytes, 'application/pdf')
    email.send()

    dn.last_emailed_at = timezone.now()
    dn.save()


