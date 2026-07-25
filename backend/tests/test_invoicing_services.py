import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.billing.models import RateCard, RentRun
from apps.billing.services import (
    create_rate_card,
    create_rent_run,
    post_rent_run,
)
from apps.invoicing.models import Invoice, InvoiceLine
from apps.invoicing.services import (
    generate_invoices_for_rent_run,
    post_invoice,
    cancel_invoice,
    generate_invoice_pdf,
)
from apps.invoicing.serializers import InvoiceOutputSerializer
from apps.invoicing.selectors import get_invoices_list, get_invoice_by_id


@pytest.fixture
def test_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Invoice Test Farmer",
        code="INV-FARM-01",
        type="DEPOSITOR",
        gstin="27ABCDE1234F1Z5"
    )


@pytest.fixture
def test_party2(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Second Farmer",
        code="INV-FARM-02",
        type="DEPOSITOR",
        gstin=""
    )


@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Test Commodity",
        code="COMM-01",
        unit="BAGS"
    )


@pytest.mark.django_db
def test_generate_invoices_for_posted_rent_run_single_party(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    post_rent_run(rent_run_id=rent_run.id)

    invoices = generate_invoices_for_rent_run(
        facility_id=default_facility.id,
        rent_run_id=rent_run.id
    )

    assert len(invoices) == 1
    inv = invoices[0]
    assert inv.facility == default_facility
    assert inv.party == test_party
    assert inv.rent_run == rent_run
    assert inv.status == Invoice.Status.DRAFT
    assert inv.party_gstin_snapshot == "27ABCDE1234F1Z5"
    assert inv.subtotal == Decimal('5000.00')
    assert inv.gst_rate == Decimal('18.00')
    assert inv.gst_amount == Decimal('900.00')
    assert inv.total_amount == Decimal('5900.00')
    assert inv.invoice_number.startswith("INV-")

    assert inv.lines.count() == 1
    line = inv.lines.first()
    assert line.amount == Decimal('5000.00')
    assert "Rent -" in line.description


@pytest.mark.django_db
def test_generate_invoices_for_posted_rent_run_multiple_parties(default_facility, test_party, test_party2, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party2.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 200,
            "unit_weight": Decimal('50.00')
        }]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    post_rent_run(rent_run_id=rent_run.id)

    invoices = generate_invoices_for_rent_run(
        facility_id=default_facility.id,
        rent_run_id=rent_run.id
    )

    assert len(invoices) == 2
    inv1 = next(i for i in invoices if i.party_id == test_party.id)
    inv2 = next(i for i in invoices if i.party_id == test_party2.id)

    assert inv1.subtotal == Decimal('5000.00')
    assert inv1.total_amount == Decimal('5900.00')
    assert inv1.party_gstin_snapshot == "27ABCDE1234F1Z5"

    assert inv2.subtotal == Decimal('10000.00')
    assert inv2.gst_amount == Decimal('1800.00')
    assert inv2.total_amount == Decimal('11800.00')
    assert inv2.party_gstin_snapshot == ""


@pytest.mark.django_db
def test_generate_invoices_for_draft_rent_run_raises_validation_error(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    # Note: NOT posting rent_run

    with pytest.raises(ValidationError) as exc:
        generate_invoices_for_rent_run(
            facility_id=default_facility.id,
            rent_run_id=rent_run.id
        )
    assert "must be POSTED" in str(exc.value)


@pytest.mark.django_db
def test_generate_invoices_double_invoicing_guard(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    post_rent_run(rent_run_id=rent_run.id)

    # First call succeeds
    invoices = generate_invoices_for_rent_run(
        facility_id=default_facility.id,
        rent_run_id=rent_run.id
    )
    assert len(invoices) == 1

    # Second call raises ValidationError
    with pytest.raises(ValidationError) as exc:
        generate_invoices_for_rent_run(
            facility_id=default_facility.id,
            rent_run_id=rent_run.id
        )
    assert "already been generated" in str(exc.value)
    assert Invoice.objects.filter(rent_run=rent_run).count() == 1


@pytest.mark.django_db
def test_post_and_cancel_invoice_status_transitions(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    post_rent_run(rent_run_id=rent_run.id)

    invoices = generate_invoices_for_rent_run(
        facility_id=default_facility.id,
        rent_run_id=rent_run.id
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
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    post_rent_run(rent_run_id=rent_run.id)

    invoices = generate_invoices_for_rent_run(
        facility_id=default_facility.id,
        rent_run_id=rent_run.id
    )
    inv = invoices[0]

    cancelled_inv = cancel_invoice(invoice_id=inv.id)
    assert cancelled_inv.status == Invoice.Status.CANCELLED


@pytest.mark.django_db
def test_generate_invoice_pdf(default_facility, test_party, test_commodity, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    post_rent_run(rent_run_id=rent_run.id)

    invoices = generate_invoices_for_rent_run(
        facility_id=default_facility.id,
        rent_run_id=rent_run.id
    )
    inv = invoices[0]
    assert not inv.pdf_file

    pdf_url = generate_invoice_pdf(invoice_id=inv.id)
    assert pdf_url is not None
    assert pdf_url != ""

    inv_fetched = get_invoice_by_id(inv.id)
    assert inv_fetched.pdf_file is not None
    assert inv_fetched.pdf_file.read().startswith(b'%PDF')
    serializer = InvoiceOutputSerializer(inv_fetched)
    assert serializer.data['pdf_url'] == pdf_url
