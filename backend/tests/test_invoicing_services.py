import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.inventory.models import GRN
from apps.delivery.services import create_delivery_note
from apps.delivery.models import DeliveryNote
from apps.invoicing.models import Invoice, InvoiceLine, Payment, PaymentStatus
from apps.invoicing.services import (
    generate_invoices_for_uninvoiced_deliveries,
    preview_uninvoiced_charges,
    post_invoice,
    cancel_invoice,
    record_payment,
    delete_payment,
    build_invoice_pdf,
)
from apps.invoicing.serializers import InvoiceOutputSerializer
from apps.invoicing.selectors import get_invoice_by_id


@pytest.fixture
def test_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Invoice Test Farmer",
        type="DEPOSITOR",
        gstin="27ABCDE1234F1Z5"
    )


@pytest.fixture
def test_party2(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Second Farmer",
        type="DEPOSITOR",
        gstin=""
    )


@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Test Commodity",
        unit="BAGS"
    )



@pytest.mark.django_db
def test_generate_invoices_for_withdrawals_single_party(default_facility, test_party, test_commodity):
    """
    Test generating invoices for posted delivery notes for a single party.
    Includes rent calculation and loading charges.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        loading_charge=Decimal('100.00'),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),  # 31 days -> multiplier 1.5
        loading_charge=Decimal('50.00'),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    invoices = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id,
        party_id=test_party.id
    )

    assert len(invoices) == 1
    inv = invoices[0]
    assert inv.facility == default_facility
    assert inv.party == test_party
    assert inv.status == Invoice.Status.DRAFT
    assert inv.party_gstin_snapshot == "27ABCDE1234F1Z5"
    
    # Rent: 100 * 50 * 1.0 = 5000.00
    # GRN Loading: 100.00
    # DN Delivery: 50.00
    # Subtotal: 5150.00
    assert inv.subtotal == Decimal('5150.00')
    assert inv.gst_rate == Decimal('18.00')
    assert inv.gst_amount == Decimal('927.00')
    assert inv.total_amount == Decimal('6077.00')
    assert inv.invoice_number.startswith("INV-")

    # 3 lines: Rent, GRN Loading, DN Delivery
    assert inv.lines.count() == 3


@pytest.mark.django_db
def test_generate_invoices_double_invoicing_guard(default_facility, test_party, test_commodity):
    """
    Asserts calling generate_invoices_for_uninvoiced_deliveries twice returns empty on second call
    because all delivery lines were marked invoiced_at on the first call.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    # First call creates invoice
    invoices1 = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id,
        party_id=test_party.id
    )
    assert len(invoices1) == 1

    # Second call finds 0 uninvoiced delivery lines -> returns []
    invoices2 = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id,
        party_id=test_party.id
    )
    assert len(invoices2) == 0


@pytest.mark.django_db
def test_post_and_cancel_invoice_status_transitions(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    invoices = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id,
        party_id=test_party.id
    )
    inv = invoices[0]
    assert inv.status == Invoice.Status.DRAFT

    # Post invoice
    posted_inv = post_invoice(invoice_id=inv.id)
    assert posted_inv.status == Invoice.Status.POSTED

    # Re-posting fails
    with pytest.raises(ValidationError) as exc:
        post_invoice(invoice_id=inv.id)
    assert "must be DRAFT" in str(exc.value)

    # Cancelling POSTED invoice fails
    with pytest.raises(ValidationError) as exc:
        cancel_invoice(invoice_id=inv.id)
    assert "must be DRAFT" in str(exc.value)


@pytest.mark.django_db
def test_cancel_draft_invoice(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    invoices = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id,
        party_id=test_party.id
    )
    inv = invoices[0]

    cancelled_inv = cancel_invoice(invoice_id=inv.id)
    assert cancelled_inv.status == Invoice.Status.CANCELLED


@pytest.mark.django_db
def test_generate_invoice_pdf(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    invoices = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id,
        party_id=test_party.id
    )
    inv = invoices[0]

    pdf_bytes = build_invoice_pdf(invoice_id=inv.id)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF')

    inv_fetched = get_invoice_by_id(inv.id)
    serializer = InvoiceOutputSerializer(inv_fetched)
    assert 'pdf_url' not in serializer.data


@pytest.mark.django_db
def test_invoice_party_and_facility_snapshots_and_rename_resilience(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    invoices = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id,
        party_id=test_party.id
    )
    inv = invoices[0]

    original_party_name = test_party.name
    assert inv.party_name_snapshot == original_party_name
    assert inv.party_gstin_snapshot == test_party.gstin
    assert inv.facility_name_snapshot == default_facility.name

    # Rename party in live database
    test_party.name = "Renamed Corporate Entity Ltd"
    test_party.save()

    # Assert invoice snapshot field remains unchanged
    inv.refresh_from_db()
    assert inv.party_name_snapshot == original_party_name
    assert inv.party.name == "Renamed Corporate Entity Ltd"


@pytest.mark.django_db
def test_invoice_no_payments_unpaid(default_facility, test_party):
    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-TEST-001",
        party=test_party,
        invoice_date=date(2026, 7, 1),
        subtotal=Decimal('1000.00'),
        gst_rate=Decimal('18.00'),
        gst_amount=Decimal('180.00'),
        total_amount=Decimal('1180.00')
    )
    assert inv.payment_status == PaymentStatus.UNPAID
    assert inv.amount_paid == Decimal('0.00')
    assert inv.amount_due == Decimal('1180.00')


@pytest.mark.django_db
def test_record_payment_partial_and_paid(default_facility, test_party):
    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-TEST-002",
        party=test_party,
        invoice_date=date(2026, 7, 1),
        total_amount=Decimal('1000.00')
    )

    # 1. Partial payment
    payment1 = record_payment(
        invoice_id=inv.id,
        amount=Decimal('400.00'),
        payment_date=date(2026, 7, 2),
        method=Payment.Method.CASH,
        reference="REF-001"
    )
    assert payment1.amount == Decimal('400.00')
    inv.refresh_from_db()
    assert inv.payment_status == PaymentStatus.PARTIAL
    assert inv.amount_paid == Decimal('400.00')
    assert inv.amount_due == Decimal('600.00')

    # 2. Paying remaining exact balance
    payment2 = record_payment(
        invoice_id=inv.id,
        amount=Decimal('600.00'),
        payment_date=date(2026, 7, 3),
        method=Payment.Method.BANK_TRANSFER,
        reference="UTR12345678"
    )
    assert payment2.amount == Decimal('600.00')
    inv.refresh_from_db()
    assert inv.payment_status == PaymentStatus.PAID
    assert inv.amount_paid == Decimal('1000.00')
    assert inv.amount_due == Decimal('0.00')


@pytest.mark.django_db
def test_two_partial_payments_sum_correctly(default_facility, test_party):
    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-TEST-003",
        party=test_party,
        invoice_date=date(2026, 7, 1),
        total_amount=Decimal('919.26')
    )

    record_payment(
        invoice_id=inv.id,
        amount=Decimal('500.00'),
        payment_date=date(2026, 7, 2),
        method=Payment.Method.UPI
    )
    record_payment(
        invoice_id=inv.id,
        amount=Decimal('419.26'),
        payment_date=date(2026, 7, 3),
        method=Payment.Method.CHEQUE
    )

    inv.refresh_from_db()
    assert inv.amount_paid == Decimal('919.26')
    assert inv.amount_due == Decimal('0.00')
    assert inv.payment_status == PaymentStatus.PAID


@pytest.mark.django_db
def test_record_payment_invalid_amount_raises_validation_error(default_facility, test_party):
    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-TEST-004",
        party=test_party,
        invoice_date=date(2026, 7, 1),
        total_amount=Decimal('1000.00')
    )

    with pytest.raises(ValidationError) as exc1:
        record_payment(
            invoice_id=inv.id,
            amount=Decimal('0.00'),
            payment_date=date(2026, 7, 2)
        )
    assert "greater than zero" in str(exc1.value)

    with pytest.raises(ValidationError) as exc2:
        record_payment(
            invoice_id=inv.id,
            amount=Decimal('-50.00'),
            payment_date=date(2026, 7, 2)
        )
    assert "greater than zero" in str(exc2.value)


@pytest.mark.django_db
def test_record_payment_cancelled_invoice_raises_validation_error(default_facility, test_party):
    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-TEST-005",
        party=test_party,
        invoice_date=date(2026, 7, 1),
        status=Invoice.Status.CANCELLED,
        total_amount=Decimal('1000.00')
    )

    with pytest.raises(ValidationError) as exc:
        record_payment(
            invoice_id=inv.id,
            amount=Decimal('500.00'),
            payment_date=date(2026, 7, 2)
        )
    assert "cancelled invoice" in str(exc.value)


@pytest.mark.django_db
def test_record_payment_overpayment(default_facility, test_party):
    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-TEST-006",
        party=test_party,
        invoice_date=date(2026, 7, 1),
        total_amount=Decimal('1000.00')
    )

    payment = record_payment(
        invoice_id=inv.id,
        amount=Decimal('1200.00'),
        payment_date=date(2026, 7, 2),
        method=Payment.Method.CASH
    )
    assert payment.amount == Decimal('1200.00')

    inv.refresh_from_db()
    assert inv.amount_paid == Decimal('1200.00')
    assert inv.amount_due == Decimal('0.00')  # Clamped to 0.00, NOT negative -200.00
    assert inv.payment_status == PaymentStatus.PAID


@pytest.mark.django_db
def test_delete_payment_service(default_facility, test_party):
    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-TEST-007",
        party=test_party,
        invoice_date=date(2026, 7, 1),
        total_amount=Decimal('1000.00')
    )

    payment = record_payment(
        invoice_id=inv.id,
        amount=Decimal('400.00'),
        payment_date=date(2026, 7, 2)
    )
    inv.refresh_from_db()
    assert inv.amount_paid == Decimal('400.00')

    delete_payment(payment_id=payment.id)
    inv.refresh_from_db()
    assert inv.amount_paid == Decimal('0.00')
    assert inv.payments.count() == 0


@pytest.mark.django_db
def test_preview_uninvoiced_charges_totals_identical_to_generation(default_facility, test_party, test_commodity):
    """
    Assert preview returns totals IDENTICAL to what generation then actually produces for the same data.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        loading_charge=Decimal('100.00'),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        loading_charge=Decimal('50.00'),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    preview_list = preview_uninvoiced_charges(
        facility_id=default_facility.id,
        party_id=test_party.id
    )
    assert len(preview_list) == 1
    prev = preview_list[0]
    assert prev['party_id'] == test_party.id
    assert prev['party_name'] == test_party.name
    assert prev['party_code'] == test_party.code

    # Generate invoices
    invoices = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id,
        party_id=test_party.id
    )
    assert len(invoices) == 1
    inv = invoices[0]

    # Assert Decimals match exactly
    assert prev['subtotal'] == inv.subtotal
    assert prev['gst_rate'] == inv.gst_rate
    assert prev['gst_amount'] == inv.gst_amount
    assert prev['total_amount'] == inv.total_amount

    # Assert line breakdowns match
    inv_lines = list(inv.lines.all())
    assert len(prev['lines']) == len(inv_lines)
    for p_line, i_line in zip(prev['lines'], inv_lines):
        assert p_line['description'] == i_line.description
        assert p_line['amount'] == i_line.amount


@pytest.mark.django_db
def test_preview_uninvoiced_charges_does_not_create_records_or_mark_invoiced(default_facility, test_party, test_commodity):
    """
    Assert preview does NOT create Invoice/InvoiceLine rows and does NOT set DeliveryLine.invoiced_at.
    """
    from apps.delivery.selectors import get_uninvoiced_delivery_lines

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    inv_count_before = Invoice.objects.count()
    inv_line_count_before = InvoiceLine.objects.count()

    preview_list = preview_uninvoiced_charges(facility_id=default_facility.id)
    assert len(preview_list) == 1

    assert Invoice.objects.count() == inv_count_before
    assert InvoiceLine.objects.count() == inv_line_count_before

    uninvoiced_lines = get_uninvoiced_delivery_lines(facility_id=default_facility.id)
    assert uninvoiced_lines.count() == 1


@pytest.mark.django_db
def test_preview_uninvoiced_charges_does_not_consume_sequence_number(default_facility, test_party, test_commodity):
    """
    Assert preview does not consume an invoice sequence number.
    """
    from libs.sequences import Sequence

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    seq_before = Sequence.objects.filter(facility=default_facility, sequence_type='INV').first()
    val_before = seq_before.current_value if seq_before else 0

    # Call preview twice
    preview_uninvoiced_charges(facility_id=default_facility.id)
    preview_uninvoiced_charges(facility_id=default_facility.id)

    seq_after = Sequence.objects.filter(facility=default_facility, sequence_type='INV').first()
    val_after = seq_after.current_value if seq_after else 0

    assert val_before == val_after

    # Generate invoice afterwards and check sequence number
    invoices = generate_invoices_for_uninvoiced_deliveries(facility_id=default_facility.id)
    assert len(invoices) == 1
    assert invoices[0].invoice_number.endswith(f"{val_before + 1:06d}")


@pytest.mark.django_db
def test_preview_already_invoiced_delivery_lines_never_appear(default_facility, test_party, test_commodity):
    """
    Assert already-invoiced delivery lines never appear in a preview.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    # Generate invoice
    generate_invoices_for_uninvoiced_deliveries(facility_id=default_facility.id)

    # Preview now returns empty list
    preview_list = preview_uninvoiced_charges(facility_id=default_facility.id)
    assert len(preview_list) == 0


@pytest.mark.django_db
def test_preview_already_billed_grn_charge_does_not_reappear(default_facility, test_party, test_commodity):
    """
    Assert a GRN receiving charge already billed on an earlier invoice does not reappear in a later preview.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        loading_charge=Decimal('200.00'),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    # Withdrawal 1
    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 15),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 40}]
    )

    # Generate invoice for 1st withdrawal -> GRN receiving charge gets billed
    generate_invoices_for_uninvoiced_deliveries(facility_id=default_facility.id)

    # Withdrawal 2
    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 60}]
    )

    # Preview for withdrawal 2
    preview_list = preview_uninvoiced_charges(facility_id=default_facility.id)
    assert len(preview_list) == 1
    prev = preview_list[0]

    descriptions = [line['description'] for line in prev['lines']]
    assert not any("Receiving Charge" in desc for desc in descriptions)


@pytest.mark.django_db
def test_preview_party_id_filtering(default_facility, test_party, test_party2, test_commodity):
    """
    Assert party_id filtering returns only that party.
    """
    grn1 = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{"commodity_id": test_commodity.id, "initial_qty": 50, "unit_weight": Decimal('50.00'), "rent_rate_per_unit": Decimal('50.00')}]
    )
    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 10),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": grn1.lots.first().id, "qty": 50}]
    )

    grn2 = create_grn(
        facility_id=default_facility.id,
        party_id=test_party2.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{"commodity_id": test_commodity.id, "initial_qty": 30, "unit_weight": Decimal('50.00'), "rent_rate_per_unit": Decimal('50.00')}]
    )
    create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party2.id,
        dispatch_date=date(2026, 7, 12),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": grn2.lots.first().id, "qty": 30}]
    )

    # Preview all
    preview_all = preview_uninvoiced_charges(facility_id=default_facility.id)
    assert len(preview_all) == 2

    # Preview party 1 only
    preview_p1 = preview_uninvoiced_charges(facility_id=default_facility.id, party_id=test_party.id)
    assert len(preview_p1) == 1
    assert preview_p1[0]['party_id'] == test_party.id

    # Preview party 2 only
    preview_p2 = preview_uninvoiced_charges(facility_id=default_facility.id, party_id=test_party2.id)
    assert len(preview_p2) == 1
    assert preview_p2[0]['party_id'] == test_party2.id




@pytest.mark.django_db
def test_invoice_lines_carry_billed_quantity_unit_and_rate(default_facility):
    """
    InvoiceLine used to only store description + amount. A quantity/unit/rate
    was embedded in the description text but never available as data, so the
    frontend had nothing real to show and displayed fabricated zero columns.
    """
    party = create_party(facility_id=default_facility.id, name="Rate Test Farmer", type="DEPOSITOR")
    commodity = create_commodity(facility_id=default_facility.id, name="Rate Test Commodity", unit="BAGS")

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        loading_charge_mode='PER_UNIT',
        loading_unloading_rate_per_bag=Decimal('2.00'),
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "rent_rate_per_unit": Decimal('12.00'),
        }],
    )
    lot = grn.lots.first()

    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 8, 1),
        status=DeliveryNote.Status.POSTED,
        loading_charge_mode='FLAT',
        loading_charge=Decimal('150.00'),
        lines=[{"lot_id": lot.id, "qty": 100}],
    )

    invoice = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id, party_id=party.id
    )[0]

    rent_line = InvoiceLine.objects.get(invoice=invoice, description__startswith='Rent')
    assert rent_line.quantity == 100
    assert rent_line.unit == 'BAGS'
    assert rent_line.rate_per_unit == Decimal('12.00')

    grn_charge_line = InvoiceLine.objects.get(invoice=invoice, description__contains=grn.grn_number)
    assert grn_charge_line.quantity == 100
    assert grn_charge_line.rate_per_unit == Decimal('2.00')
    assert "Loading/Unloading Charge" in grn_charge_line.description

    dn_charge_line = InvoiceLine.objects.get(invoice=invoice, description__contains=dn.dn_number)
    assert dn_charge_line.quantity is None
    assert dn_charge_line.rate_per_unit is None
    assert "Loading/Unloading Charge" in dn_charge_line.description
