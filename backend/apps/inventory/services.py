from typing import List, Dict, Any
from datetime import date
from decimal import Decimal
from io import BytesIO
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from libs.sequences import get_next_sequence_number
from libs.lookups import get_facility_or_raise, get_party_or_raise
from apps.locations.models import Floor, Chamber
from .models import Commodity, GRN, Lot


def _safe_pdf_text(val: Any) -> str:
    if val is None:
        return ""
    s = str(val)
    return s.encode('latin-1', errors='replace').decode('latin-1')


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
    bill_no: str = '',
    bilty_no: str = '',
    transporter: str = '',
    preservation_rate_per_bag_per_month: Decimal = Decimal('0.00'),
    loading_unloading_rate_per_bag: Decimal = Decimal('0.00'),
    inward_time: Any = None,
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
        bill_no=bill_no,
        bilty_no=bilty_no,
        transporter=transporter,
        preservation_rate_per_bag_per_month=preservation_rate_per_bag_per_month,
        loading_unloading_rate_per_bag=loading_unloading_rate_per_bag,
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

        lot_number = item_data.get('lot_number') or get_next_sequence_number(facility=facility, sequence_type='LOT')

        chamber_id = item_data.get('chamber_id')
        floor_id = item_data.get('floor_id')

        floor_ref = None
        chamber_ref = None
        chamber_text = item_data.get('chamber', '')
        floor_text = item_data.get('floor', '')

        if chamber_id is not None:
            try:
                chamber_ref = Chamber.objects.select_related('floor').get(pk=chamber_id)
            except Chamber.DoesNotExist:
                raise ValidationError(f"Chamber with ID {chamber_id} does not exist.")

            if chamber_ref.floor.facility_id != facility.id:
                raise ValidationError(f"Chamber with ID {chamber_id} does not belong to facility {facility.id}.")

            if floor_id is not None and chamber_ref.floor_id != floor_id:
                raise ValidationError(f"Chamber with ID {chamber_id} does not belong to floor {floor_id}.")

            floor_ref = chamber_ref.floor
            chamber_text = chamber_ref.name
            floor_text = floor_ref.name
        elif floor_id is not None:
            try:
                floor_ref = Floor.objects.get(pk=floor_id)
            except Floor.DoesNotExist:
                raise ValidationError(f"Floor with ID {floor_id} does not exist.")

            if floor_ref.facility_id != facility.id:
                raise ValidationError(f"Floor with ID {floor_id} does not belong to facility {facility.id}.")

            floor_text = floor_ref.name

        lot = Lot(
            facility=facility,
            grn=grn,
            commodity=commodity,
            lot_number=lot_number,
            chamber=chamber_text,
            floor=floor_text,
            rack=item_data.get('rack', ''),
            floor_ref=floor_ref,
            chamber_ref=chamber_ref,
            special_remarks=item_data.get('special_remarks', ''),
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


def generate_grn_pdf(*, grn_id: int) -> str:
    """
    Generate a PDF for a Goods Receipt Note (GRN) matching paper receipt layout.
    """
    try:
        grn = GRN.objects.select_related('facility', 'party').prefetch_related('lots__commodity').get(pk=grn_id)
    except GRN.DoesNotExist:
        raise ValidationError(f"GRN with ID {grn_id} does not exist.")

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

    facility = grn.facility
    party = grn.party

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
    if fac_bank: contact_parts.append(f"<b>A/c:</b> {fac_bank}")
    if fac_ifsc: contact_parts.append(f"<b>IFSC:</b> {fac_ifsc}")
    if contact_parts:
        header_left += "<br/>" + " | ".join(contact_parts)

    grn_time_str = grn.inward_time.strftime('%H:%M') if grn.inward_time else '—'
    header_right = (
        f"<b>GOODS RECEIPT NOTE (Receipt / Rasid)</b><br/>"
        f"<b>GRN No. (Kramank):</b> {_safe_pdf_text(grn.grn_number)}<br/>"
        f"<b>Date (Dinank):</b> {grn.receipt_date}<br/>"
        f"<b>Time (Samay):</b> {grn_time_str}"
    )

    header_table = Table([[Paragraph(header_left, styles['Normal']), Paragraph(header_right, styles['Normal'])]], colWidths=[310, 230])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    party_name = _safe_pdf_text(party.name)
    party_gstin = _safe_pdf_text(getattr(party, 'gstin', '')) or 'N/A'
    party_phone = _safe_pdf_text(getattr(party, 'mobile', '')) or 'N/A'
    party_addr = _safe_pdf_text(getattr(party, 'address', ''))

    party_text = f"<b>M/s (Party Name):</b> {party_name}<br/>"
    party_text += f"<b>GSTIN:</b> {party_gstin} | <b>Mobile:</b> {party_phone}"
    if party_addr:
        party_text += f"<br/><b>Address:</b> {party_addr}"

    party_table = Table([[Paragraph(party_text, styles['Normal'])]], colWidths=[540])
    party_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(party_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("<i>Received following goods for cold storage based on terms and conditions stated below.</i>", styles['Normal']))
    elements.append(Spacer(1, 6))

    table_data = [["Qty (Bags)", "Description (Commodity)", "Lot No.", "Special Remarks"]]
    for lot in grn.lots.all():
        table_data.append([
            str(lot.initial_qty),
            _safe_pdf_text(lot.commodity.name),
            _safe_pdf_text(lot.lot_number),
            _safe_pdf_text(lot.special_remarks or '—')
        ])

    items_table = Table(table_data, colWidths=[80, 180, 130, 150])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("<font size=8><i>(Goods received unchecked/unverified as to condition / Avashtha ki santushti ke bina, bagair jancha gaya mal)</i></font>", styles['Normal']))
    elements.append(Spacer(1, 10))

    charges_text = (
        f"<b>Preservation Charge (Per bag/month):</b> ₹{grn.preservation_rate_per_bag_per_month:.2f}<br/>"
        f"<b>Loading/Unloading Labor Rate (Per bag):</b> ₹{grn.loading_unloading_rate_per_bag:.2f} (Total Charge: ₹{grn.loading_charge:.2f})"
    )
    ref_text = (
        f"<b>Bill No:</b> {_safe_pdf_text(grn.bill_no or '—')}<br/>"
        f"<b>Bilty / LR No:</b> {_safe_pdf_text(grn.bilty_no or '—')}<br/>"
        f"<b>Transporter:</b> {_safe_pdf_text(grn.transporter or '—')}<br/>"
        f"<b>Vehicle No:</b> {_safe_pdf_text(grn.vehicle_number or '—')} | <b>Driver:</b> {_safe_pdf_text(grn.driver_name or '—')}<br/>"
        f"<b>Chamber/Remarks:</b> {_safe_pdf_text(grn.remarks or '—')}"
    )
    info_table = Table([[Paragraph(charges_text, styles['Normal']), Paragraph(ref_text, styles['Normal'])]], colWidths=[270, 270])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    terms_text = _safe_pdf_text(getattr(facility, 'terms_and_conditions', ''))
    if terms_text.strip():
        terms_style = ParagraphStyle(
            'TermsStyle',
            parent=styles['Normal'],
            fontSize=7,
            leading=9,
            textColor=colors.dimgrey
        )
        elements.append(Paragraph(f"<b>Terms & Conditions:</b> {terms_text}", terms_style))
        elements.append(Spacer(1, 10))

    footer_left = "<b>Party Signature</b><br/><br/><br/>______________________"
    footer_right = f"<b>For: {fac_name}</b><br/><br/><br/><b>Authorised Signatory</b><br/>Thank You"
    footer_table = Table([[Paragraph(footer_left, styles['Normal']), Paragraph(footer_right, styles['Normal'])]], colWidths=[270, 270])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(footer_table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"{grn.grn_number}.pdf"
    with transaction.atomic():
        grn.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    return grn.pdf_file.url
