from typing import List, Dict, Any
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from libs.sequences import get_next_sequence_number
from libs.lookups import get_facility_or_raise, get_party_or_raise
from apps.inventory.models import Lot
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
    remarks: str = '',
    status: str = DeliveryNote.Status.DRAFT,
    lines: List[Dict[str, Any]] = None
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

    lines = lines or []
    lot_ids = [line_data.get('lot_id') for line_data in lines if line_data.get('lot_id') is not None]

    lots_by_id = Lot.objects.in_bulk(lot_ids, field_name='pk')
    lots_by_id = {
        lid: lot for lid, lot in lots_by_id.items()
        if lot.facility_id == facility.id
    }

    # Validate lines before creating any records
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

    dn_number = get_next_sequence_number(facility=facility, sequence_type='DN')

    dn = DeliveryNote(
        facility=facility,
        dn_number=dn_number,
        party=party,
        dispatch_date=dispatch_date,
        vehicle_number=vehicle_number,
        driver_name=driver_name,
        remarks=remarks,
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
    If any line fails, transaction rolls back completely.
    """
    try:
        dn = DeliveryNote.objects.select_for_update().get(pk=delivery_note_id)
    except DeliveryNote.DoesNotExist:
        raise ValidationError(f"Delivery Note with ID {delivery_note_id} does not exist.")

    if dn.status != DeliveryNote.Status.DRAFT:
        raise ValidationError(f"Cannot post Delivery Note: current status is '{dn.status}', must be DRAFT.")

    for line in dn.lines.select_related('lot').all():
        withdraw_stock_from_lot(lot_id=line.lot_id, qty_to_withdraw=line.qty)

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
