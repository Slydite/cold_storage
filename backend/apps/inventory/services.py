from typing import List, Dict, Any
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from libs.sequences import get_next_sequence_number
from libs.lookups import get_facility_or_raise, get_party_or_raise
from .models import Commodity, GRN, Lot

@transaction.atomic
def create_commodity(
    *,
    facility_id: int,
    name: str,
    code: str,
    unit: str = 'BAGS',
    description: str = '',
    is_active: bool = True
) -> Commodity:
    """
    Create a new commodity for a facility.
    """
    facility = get_facility_or_raise(facility_id)

    commodity = Commodity(
        facility=facility,
        name=name,
        code=code,
        unit=unit,
        description=description,
        is_active=is_active
    )
    commodity.full_clean()
    commodity.save()
    return commodity


@transaction.atomic
def update_commodity(*, commodity_id: int, **fields) -> Commodity:
    """
    Update an existing commodity.
    """
    try:
        commodity = Commodity.objects.get(pk=commodity_id)
    except Commodity.DoesNotExist:
        raise ValidationError(f"Commodity with ID {commodity_id} does not exist.")

    allowed_fields = ['name', 'code', 'unit', 'description', 'is_active']
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(commodity, field, value)

    commodity.full_clean()
    commodity.save()
    return commodity


@transaction.atomic
def create_grn(
    *,
    facility_id: int,
    party_id: int,
    receipt_date: date,
    vehicle_number: str = '',
    driver_name: str = '',
    remarks: str = '',
    loading_charge: Decimal = Decimal('0.00'),
    status: str = GRN.Status.POSTED,
    items: List[Dict[str, Any]] = None
) -> GRN:
    """
    Create a Goods Receipt Note (GRN) with lots/items.
    Generates GRN number safely using sequence lock.
    """
    facility = get_facility_or_raise(facility_id)
    party = get_party_or_raise(party_id, facility)

    if status not in GRN.Status.values:
        raise ValidationError(f"Invalid status: {status}. Allowed: {GRN.Status.values}")

    grn_number = get_next_sequence_number(facility=facility, sequence_type='GRN')

    grn = GRN(
        facility=facility,
        grn_number=grn_number,
        party=party,
        receipt_date=receipt_date,
        vehicle_number=vehicle_number,
        driver_name=driver_name,
        remarks=remarks,
        loading_charge=loading_charge,
        status=status
    )
    grn.full_clean()
    grn.save()

    items = items or []

    commodity_ids = {item_data.get('commodity_id') for item_data in items}
    commodities_by_id = Commodity.objects.in_bulk(commodity_ids, field_name='pk')
    commodities_by_id = {
        cid: commodity for cid, commodity in commodities_by_id.items()
        if commodity.facility_id == facility.id
    }

    for item_data in items:
        commodity_id = item_data.get('commodity_id')
        commodity = commodities_by_id.get(commodity_id)
        if commodity is None:
            raise ValidationError(f"Commodity with ID {commodity_id} does not exist in facility {facility_id}.")

        initial_qty = item_data.get('initial_qty', 0)
        if initial_qty <= 0:
            raise ValidationError(f"Initial quantity for commodity '{commodity.name}' must be greater than 0.")

        lot_number = item_data.get('lot_number') or get_next_sequence_number(facility=facility, sequence_type='LOT')

        lot = Lot(
            facility=facility,
            grn=grn,
            commodity=commodity,
            lot_number=lot_number,
            chamber=item_data.get('chamber', ''),
            floor=item_data.get('floor', ''),
            rack=item_data.get('rack', ''),
            initial_qty=initial_qty,
            remaining_qty=initial_qty,  # Rule #2: Derived server-side
            unit_weight=item_data.get('unit_weight', 0.00),
            rent_rate_per_unit=item_data.get('rent_rate_per_unit', 0.00),
            inward_date=receipt_date
        )
        lot.full_clean()
        lot.save()

    return grn


@transaction.atomic
def post_grn(*, grn_id: int) -> GRN:
    """
    Transition a GRN from DRAFT to POSTED using select_for_update() row lock.
    """
    try:
        grn = GRN.objects.select_for_update().get(pk=grn_id)
    except GRN.DoesNotExist:
        raise ValidationError(f"GRN with ID {grn_id} does not exist.")

    if grn.status != GRN.Status.DRAFT:
        raise ValidationError(f"Cannot post GRN: current status is '{grn.status}', must be DRAFT.")

    grn.status = GRN.Status.POSTED
    grn.full_clean()
    grn.save()
    return grn


@transaction.atomic
def cancel_grn(*, grn_id: int) -> GRN:
    """
    Transition a GRN from DRAFT to CANCELLED using select_for_update() row lock.
    """
    try:
        grn = GRN.objects.select_for_update().get(pk=grn_id)
    except GRN.DoesNotExist:
        raise ValidationError(f"GRN with ID {grn_id} does not exist.")

    if grn.status != GRN.Status.DRAFT:
        raise ValidationError(f"Cannot cancel GRN: current status is '{grn.status}', must be DRAFT.")

    grn.status = GRN.Status.CANCELLED
    grn.full_clean()
    grn.save()
    return grn


@transaction.atomic
def withdraw_stock_from_lot(*, lot_id: int, qty_to_withdraw: int) -> Lot:
    """
    Safely withdraw stock from a lot using select_for_update() row lock.
    Enforces Rule #2: stock quantity is sacred.
    Refuses withdrawal if the GRN is not POSTED.
    """
    if qty_to_withdraw <= 0:
        raise ValidationError("Quantity to withdraw must be greater than 0.")

    try:
        lot = Lot.objects.select_for_update().select_related('grn').get(pk=lot_id)
    except Lot.DoesNotExist:
        raise ValidationError(f"Lot with ID {lot_id} does not exist.")

    if lot.grn.status != GRN.Status.POSTED:
        raise ValidationError(
            f"Cannot withdraw stock from Lot '{lot.lot_number}' because its GRN status is '{lot.grn.status}' (must be POSTED)."
        )

    if lot.remaining_qty < qty_to_withdraw:
        raise ValidationError(
            f"Insufficient stock in Lot '{lot.lot_number}'. "
            f"Available: {lot.remaining_qty}, Requested: {qty_to_withdraw}"
        )

    lot.remaining_qty -= qty_to_withdraw
    lot.save()
    return lot

