import re
from typing import List, Dict, Any
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.mail import EmailMessage

from libs.sequences import get_next_sequence_number, DEFAULT_PREFIXES
from libs.lookups import get_facility_or_raise, get_party_or_raise
from libs.pdf import render_pdf
from libs.choices import ChargeMode
from libs.sanitizers import clean_text, title_name, upper_code
from apps.locations.models import Chamber, Floor, Block
from .models import Commodity, GRN, Lot, Sequence, StockAdjustment


@transaction.atomic
def create_commodity(
    *,
    facility_id: int,
    name: str,
    unit: str = 'BAGS',
    description: str = '',
    is_active: bool = True
) -> Commodity:
    """
    Create a new commodity for a facility.
    Generates commodity code automatically using sequence helper.
    """
    facility = get_facility_or_raise(facility_id)

    name = title_name(name)
    description = clean_text(description)
    code = get_next_sequence_number(facility=facility, sequence_type='COMMODITY')

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

    if 'name' in fields and fields['name'] is not None:
        fields['name'] = title_name(fields['name'])
    if 'description' in fields and fields['description'] is not None:
        fields['description'] = clean_text(fields['description'])

    allowed_fields = ['name', 'unit', 'description', 'is_active']
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
    bill_no: str = '',
    bilty_no: str = '',
    transporter: str = '',
    preservation_rate_per_bag_per_month: Decimal = Decimal('0.00'),
    loading_unloading_rate_per_bag: Decimal = Decimal('0.00'),
    loading_charge_mode: str = ChargeMode.FLAT,
    inward_time: Any = None,
    status: str = GRN.Status.POSTED,
    items: List[Dict[str, Any]] = None,
    require_location: bool = True
) -> GRN:
    """
    Create a Goods Receipt Note (GRN) with lots/items.
    Generates GRN number safely using sequence lock.
    """
    facility = get_facility_or_raise(facility_id)
    party = get_party_or_raise(party_id, facility)

    if status not in GRN.Status.values:
        raise ValidationError(f"Invalid status: {status}. Allowed: {GRN.Status.values}")

    if loading_charge_mode not in ChargeMode.values:
        raise ValidationError(f"Invalid loading_charge_mode: {loading_charge_mode}. Allowed: {ChargeMode.values}")

    vehicle_number = upper_code(vehicle_number)
    driver_name = title_name(driver_name)
    transporter = title_name(transporter)
    bill_no = upper_code(bill_no)
    bilty_no = upper_code(bilty_no)
    remarks = clean_text(remarks)

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
        bill_no=bill_no,
        bilty_no=bilty_no,
        transporter=transporter,
        preservation_rate_per_bag_per_month=preservation_rate_per_bag_per_month,
        loading_unloading_rate_per_bag=loading_unloading_rate_per_bag,
        loading_charge_mode=loading_charge_mode,
        inward_time=inward_time,
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

        lot_number = item_data.get('lot_number')
        if lot_number:
            seq = Sequence.objects.filter(facility=facility, sequence_type='LOT').first()
            prefix = seq.prefix if seq else DEFAULT_PREFIXES.get('LOT', 'LOT-')
            if not re.match(r'^' + re.escape(prefix) + r'\d+$', lot_number):
                raise ValidationError(f"Invalid lot number format: {lot_number}. Expected prefix '{prefix}' followed by digits.")
        else:
            lot_number = get_next_sequence_number(facility=facility, sequence_type='LOT')

        chamber_id = item_data.get('chamber_id')
        floor_id = item_data.get('floor_id')
        block_id = item_data.get('block_id')

        if require_location and (block_id is None or block_id == ""):
            raise ValidationError(f"Storage location (block) is required for commodity '{commodity.name}'.")

        chamber_ref = None
        floor_ref = None
        block_ref = None

        chamber_text = item_data.get('chamber', '')
        floor_text = item_data.get('floor', '')

        if block_id is not None:
            try:
                block_ref = Block.objects.select_related('floor', 'floor__chamber', 'floor__chamber__facility').get(pk=block_id)
            except Block.DoesNotExist:
                raise ValidationError(f"Block with ID {block_id} does not exist.")

            if floor_id is not None and block_ref.floor_id != floor_id:
                raise ValidationError(f"Block with ID {block_id} does not belong to floor {floor_id}.")

            if chamber_id is not None and block_ref.floor.chamber_id != chamber_id:
                raise ValidationError(f"Block with ID {block_id} does not belong to chamber {chamber_id}.")

            if block_ref.floor.chamber.facility_id != facility.id:
                raise ValidationError(f"Block with ID {block_id} does not belong to facility {facility.id}.")

            floor_ref = block_ref.floor
            chamber_ref = floor_ref.chamber

        elif floor_id is not None:
            try:
                floor_ref = Floor.objects.select_related('chamber', 'chamber__facility').get(pk=floor_id)
            except Floor.DoesNotExist:
                raise ValidationError(f"Floor with ID {floor_id} does not exist.")

            if chamber_id is not None and floor_ref.chamber_id != chamber_id:
                raise ValidationError(f"Floor with ID {floor_id} does not belong to chamber {chamber_id}.")

            if floor_ref.chamber.facility_id != facility.id:
                raise ValidationError(f"Floor with ID {floor_id} does not belong to facility {facility.id}.")

            chamber_ref = floor_ref.chamber

        elif chamber_id is not None:
            try:
                chamber_ref = Chamber.objects.select_related('facility').get(pk=chamber_id)
            except Chamber.DoesNotExist:
                raise ValidationError(f"Chamber with ID {chamber_id} does not exist.")

            if chamber_ref.facility_id != facility.id:
                raise ValidationError(f"Chamber with ID {chamber_id} does not belong to facility {facility.id}.")

        if chamber_ref is not None:
            chamber_text = chamber_ref.name
        if floor_ref is not None:
            floor_text = floor_ref.name

        unit = item_data.get('unit') or commodity.unit or Lot.UnitType.BAGS
        special_remarks = clean_text(item_data.get('special_remarks', ''))

        lot = Lot(
            facility=facility,
            grn=grn,
            commodity=commodity,
            lot_number=lot_number,
            chamber=chamber_text,
            floor=floor_text,
            rack=item_data.get('rack', ''),
            chamber_ref=chamber_ref,
            floor_ref=floor_ref,
            block_ref=block_ref,
            special_remarks=special_remarks,
            initial_qty=initial_qty,
            remaining_qty=initial_qty,  # Rule #2: Derived server-side
            unit=unit,
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


def build_grn_pdf(*, grn_id: int) -> bytes:
    """
    Generate PDF bytes for a Goods Receipt Note (GRN) matching paper receipt layout via WeasyPrint.
    Performs no file I/O and no model save.
    """
    try:
        grn = GRN.objects.select_related('facility', 'party').prefetch_related('lots__commodity').get(pk=grn_id)
    except GRN.DoesNotExist:
        raise ValidationError(f"GRN with ID {grn_id} does not exist.")

    facility = grn.facility
    party = grn.party

    context = {
        'grn': grn,
        'facility': facility,
        'party': party,
    }
    return render_pdf('pdf/grn.html', context)


@transaction.atomic
def email_grn_to_party(*, grn_id: int) -> None:
    """
    Build the GRN PDF, send it to the party's email address, and record the timestamp.
    """
    try:
        grn = GRN.objects.select_for_update().select_related('facility', 'party').get(pk=grn_id)
    except GRN.DoesNotExist:
        raise ValidationError(f"GRN with ID {grn_id} does not exist.")

    party = grn.party
    if not party.email or not party.email.strip():
        raise ValidationError(f"Cannot email GRN: Party '{party.name}' does not have an email address on file.")

    pdf_bytes = build_grn_pdf(grn_id=grn_id)

    subject = f"GRN {grn.grn_number} from {grn.facility.name}"
    body = (
        f"Dear {party.name},\n\n"
        f"Please find attached Goods Receipt Note (GRN) {grn.grn_number} from {grn.facility.name} "
        f"dated {grn.receipt_date.strftime('%d-%m-%Y')}.\n\n"
        f"Regards,\n"
        f"{grn.facility.name}"
    )

    email = EmailMessage(
        subject=subject,
        body=body,
        to=[party.email.strip()],
    )
    email.attach(f"{grn.grn_number}.pdf", pdf_bytes, 'application/pdf')
    email.send()

    grn.last_emailed_at = timezone.now()
    grn.save()


@transaction.atomic
def adjust_lot_stock(
    *,
    lot_id: int,
    reason: str,
    adjustment_date: date,
    new_qty: int = None,
    qty_delta: int = None,
    note: str = '',
    adjusted_by: Any = None,
) -> StockAdjustment:
    """
    Safely adjust stock of a lot using select_for_update() row lock.
    Enforces rules:
    - Resulting quantity may not be negative.
    - Exactly one of new_qty or qty_delta must be provided.
    - reason is mandatory and must be a valid StockAdjustment.Reason choice.
    - note is mandatory when reason is OTHER.
    - A zero net change is rejected.
    - Adjusting a lot whose GRN is not POSTED is rejected.
    - It must not create, touch or trigger any rent, invoice or delivery record.
      (This is a correction, not a movement. Do NOT bill anything here.)
    - Allow quantity to exceed initial_qty.
    """
    # 1. Parameter exclusivity check
    if (new_qty is not None and qty_delta is not None) or (new_qty is None and qty_delta is None):
        raise ValidationError("Specify either new_qty or qty_delta, not both or neither.")

    # 2. Reason validation
    if reason not in StockAdjustment.Reason.values:
        raise ValidationError(f"Invalid reason: {reason}. Allowed: {StockAdjustment.Reason.values}")

    # 3. Note requirement for OTHER
    if reason == StockAdjustment.Reason.OTHER and not note.strip():
        raise ValidationError("Note is mandatory when reason is OTHER.")

    # 4. Fetch Lot with lock
    try:
        lot = Lot.objects.select_for_update().select_related('grn').get(pk=lot_id)
    except Lot.DoesNotExist:
        raise ValidationError(f"Lot with ID {lot_id} does not exist.")

    # 5. Check if GRN is POSTED
    if lot.grn.status != GRN.Status.POSTED:
        raise ValidationError(
            f"Cannot adjust stock for Lot '{lot.lot_number}' because its GRN status is '{lot.grn.status}' (must be POSTED)."
        )

    qty_before = lot.remaining_qty

    if new_qty is not None:
        if new_qty < 0:
            raise ValidationError(f"The resulting quantity may not be negative. Lot: {lot.lot_number}, current quantity: {qty_before}")
        delta = new_qty - qty_before
    else:
        delta = qty_delta

    qty_after = qty_before + delta

    # 6. Negative qty check
    if qty_after < 0:
        raise ValidationError(
            f"The resulting quantity may not be negative. Lot: {lot.lot_number}, current quantity: {qty_before}"
        )

    # 7. Zero change check
    if delta == 0:
        raise ValidationError("A zero net change is rejected — there is nothing to record.")

    # 8. Update Lot remaining_qty
    lot.remaining_qty = qty_after
    lot.save()

    # 9. Create StockAdjustment
    # Note: This is purely a stock correction, not a physical movement.
    # It must not create, touch or trigger any rent, invoice or delivery records.
    adjustment = StockAdjustment(
        lot=lot,
        qty_delta=delta,
        qty_before=qty_before,
        qty_after=qty_after,
        reason=reason,
        note=note,
        adjustment_date=adjustment_date,
        adjusted_by=adjusted_by
    )
    adjustment.full_clean()
    adjustment.save()

    return adjustment



