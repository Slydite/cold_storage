from typing import List, Dict, Any
from datetime import date
from io import BytesIO
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

from libs.sequences import get_next_sequence_number
from libs.lookups import get_facility_or_raise, get_party_or_raise
from apps.inventory.models import Lot
from apps.inventory.services import withdraw_stock_from_lot
from .models import DeliveryNote, DeliveryLine


def _safe_pdf_text(val: Any) -> str:
    if val is None:
        return ""
    s = str(val)
    return s.encode('latin-1', errors='replace').decode('latin-1')


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
        transporter=transporter,
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


def generate_delivery_note_pdf(*, delivery_note_id: int) -> str:
    """
    Generate a PDF for a Delivery Note (Delivery Challan) matching real form layout.
    """
    try:
        dn = DeliveryNote.objects.select_related('facility', 'party').prefetch_related('lines__lot__commodity').get(pk=delivery_note_id)
    except DeliveryNote.DoesNotExist:
        raise ValidationError(f"Delivery Note with ID {delivery_note_id} does not exist.")

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

    facility = dn.facility
    party = dn.party

    fac_name = _safe_pdf_text(facility.name)
    fac_addr = _safe_pdf_text(facility.address or facility.code)
    fac_gstin = _safe_pdf_text(getattr(facility, 'gstin', ''))
    fac_phone = _safe_pdf_text(getattr(facility, 'phone', ''))
    fac_factory = _safe_pdf_text(getattr(facility, 'factory_phone', ''))

    header_left = f"<b>{fac_name}</b><br/>{fac_addr}"
    contact_parts = []
    if fac_gstin: contact_parts.append(f"<b>GSTIN:</b> {fac_gstin}")
    if fac_phone: contact_parts.append(f"<b>Mob:</b> {fac_phone}")
    if fac_factory: contact_parts.append(f"<b>Factory:</b> {fac_factory}")
    if contact_parts:
        header_left += "<br/>" + " | ".join(contact_parts)

    header_right = (
        f"<b>DELIVERY CHALLAN</b><br/>"
        f"<b>No. (DN Number):</b> {_safe_pdf_text(dn.dn_number)}<br/>"
        f"<b>Date:</b> {dn.dispatch_date}<br/>"
        f"<b>Status:</b> {dn.status}"
    )

    header_table = Table([[Paragraph(header_left, styles['Normal']), Paragraph(header_right, styles['Normal'])]], colWidths=[310, 230])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    party_name = _safe_pdf_text(party.name)
    party_addr = _safe_pdf_text(getattr(party, 'address', ''))
    party_text = f"<b>M/s:</b> {party_name}"
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

    transport_info = f"Please receive the under mentioned goods per LORRY / Vehicle No.: <b>{_safe_pdf_text(dn.vehicle_number or '—')}</b>"
    if dn.driver_name:
        transport_info += f" | Driver: <b>{_safe_pdf_text(dn.driver_name)}</b>"
    if dn.transporter:
        transport_info += f" | Transporter: <b>{_safe_pdf_text(dn.transporter)}</b>"

    elements.append(Paragraph(transport_info, styles['Normal']))
    elements.append(Spacer(1, 10))

    table_data = [["Lot No.", "Qty", "Particulars (Commodity)", "Balance"]]
    total_qty = 0
    for line in dn.lines.all():
        total_qty += line.qty
        balance_str = str(line.balance_after) if line.balance_after is not None else "—"
        table_data.append([
            _safe_pdf_text(line.lot.lot_number),
            str(line.qty),
            _safe_pdf_text(line.lot.commodity.name),
            balance_str
        ])

    table_data.append(["Total", f"Total- {total_qty} Bag", "", ""])

    items_table = Table(table_data, colWidths=[130, 90, 220, 100])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (1, -1), (3, -1)),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("<b>Note:</b> After the delivery of goods we are not responsible for any complaint.", styles['Normal']))
    elements.append(Spacer(1, 16))

    footer_left = "Please Sign the duplicate & return.<br/><br/><br/><b>Receiver / Driver Signature</b>"
    footer_right = f"<b>For: {fac_name}</b><br/><br/><br/><b>Authorised Signatory</b>"
    footer_table = Table([[Paragraph(footer_left, styles['Normal']), Paragraph(footer_right, styles['Normal'])]], colWidths=[270, 270])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(footer_table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"{dn.dn_number}.pdf"
    with transaction.atomic():
        dn.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    return dn.pdf_file.url
