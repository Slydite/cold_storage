"""
Tests for the manual tax and discount controls on invoices.

The owner enters tax himself rather than having it inferred, so these cover
the paths that let him do that: the DRAFT-only adjust service, tax and
discount supplied at generation time, and the facility-level default rate.
"""
import pytest
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.delivery.models import DeliveryNote
from apps.delivery.services import create_delivery_note
from apps.inventory.models import GRN
from apps.inventory.services import create_commodity, create_grn
from apps.invoicing.models import Invoice
from apps.invoicing.services import (
    adjust_invoice,
    generate_invoices_for_uninvoiced_deliveries,
    post_invoice,
)
from apps.parties.services import create_party


@pytest.fixture
def test_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Tax Control Farmer",
        type="DEPOSITOR",
        gstin="08ABCDE1234F1Z5",
    )


@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Tax Control Commodity",
        unit="BAGS",
    )


def _make_invoice(facility, party, commodity, **generate_kwargs):
    """Put 100 bags in, take them out 31 days later, invoice the result."""
    grn = create_grn(
        facility_id=facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('50.00'),
        }],
    )
    lot = grn.lots.first()
    create_delivery_note(
        facility_id=facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 8, 1),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}],
    )
    invoices = generate_invoices_for_uninvoiced_deliveries(
        facility_id=facility.id,
        party_id=party.id,
        **generate_kwargs,
    )
    assert len(invoices) == 1
    return invoices[0]


@pytest.mark.django_db
def test_adjust_sets_three_independent_rates_without_splitting(
    default_facility, test_party, test_commodity
):
    invoice = _make_invoice(default_facility, test_party, test_commodity)

    adjusted = adjust_invoice(
        invoice_id=invoice.id,
        cgst_rate=Decimal('2.50'),
        sgst_rate=Decimal('6.00'),
        igst_rate=Decimal('1.00'),
    )

    taxable = adjusted.taxable_value
    # Each component follows its own rate. Nothing is halved or redistributed.
    assert adjusted.cgst_amount == (taxable * Decimal('2.50') / 100).quantize(Decimal('0.01'))
    assert adjusted.sgst_amount == (taxable * Decimal('6.00') / 100).quantize(Decimal('0.01'))
    assert adjusted.igst_amount == (taxable * Decimal('1.00') / 100).quantize(Decimal('0.01'))
    assert adjusted.cgst_amount != adjusted.sgst_amount

    assert adjusted.gst_amount == (
        adjusted.cgst_amount + adjusted.sgst_amount + adjusted.igst_amount
    )
    # The legacy total-rate field must never contradict the components.
    assert adjusted.gst_rate == Decimal('9.50')
    assert adjusted.total_amount == adjusted.taxable_value + adjusted.gst_amount


@pytest.mark.django_db
def test_adjust_discount_is_applied_before_tax(
    default_facility, test_party, test_commodity
):
    invoice = _make_invoice(default_facility, test_party, test_commodity)
    subtotal = invoice.subtotal

    adjusted = adjust_invoice(
        invoice_id=invoice.id,
        discount_amount=Decimal('500.00'),
        discount_reason="Regular customer",
        cgst_rate=Decimal('9.00'),
        sgst_rate=Decimal('9.00'),
    )

    assert adjusted.discount_amount == Decimal('500.00')
    assert adjusted.discount_reason == "Regular customer"
    assert adjusted.taxable_value == subtotal - Decimal('500.00')

    # Tax must be charged on the post-discount value, not the subtotal.
    expected_cgst = (adjusted.taxable_value * Decimal('9.00') / 100).quantize(Decimal('0.01'))
    assert adjusted.cgst_amount == expected_cgst
    assert adjusted.cgst_amount < (subtotal * Decimal('9.00') / 100).quantize(Decimal('0.01'))

    assert adjusted.total_amount == adjusted.taxable_value + adjusted.gst_amount


@pytest.mark.django_db
def test_adjust_rejects_discount_greater_than_subtotal(
    default_facility, test_party, test_commodity
):
    invoice = _make_invoice(default_facility, test_party, test_commodity)

    with pytest.raises(ValidationError):
        adjust_invoice(
            invoice_id=invoice.id,
            discount_amount=invoice.subtotal + Decimal('0.01'),
        )


@pytest.mark.django_db
def test_adjust_rejects_negative_discount(
    default_facility, test_party, test_commodity
):
    invoice = _make_invoice(default_facility, test_party, test_commodity)

    with pytest.raises(ValidationError):
        adjust_invoice(invoice_id=invoice.id, discount_amount=Decimal('-1.00'))


@pytest.mark.django_db
def test_posted_invoice_cannot_be_adjusted(
    default_facility, test_party, test_commodity
):
    """A posted invoice has been issued to a customer; its numbers are frozen."""
    invoice = _make_invoice(default_facility, test_party, test_commodity)
    post_invoice(invoice_id=invoice.id)

    with pytest.raises(ValidationError):
        adjust_invoice(invoice_id=invoice.id, cgst_rate=Decimal('9.00'))


@pytest.mark.django_db
def test_zeroing_tax_flips_document_to_bill_of_supply(
    default_facility, test_party, test_commodity
):
    invoice = _make_invoice(default_facility, test_party, test_commodity)
    assert invoice.document_type == Invoice.DocumentType.TAX_INVOICE

    adjusted = adjust_invoice(
        invoice_id=invoice.id,
        cgst_rate=Decimal('0.00'),
        sgst_rate=Decimal('0.00'),
        igst_rate=Decimal('0.00'),
    )

    assert adjusted.gst_amount == Decimal('0.00')
    assert adjusted.document_type == Invoice.DocumentType.BILL_OF_SUPPLY
    assert adjusted.total_amount == adjusted.taxable_value


@pytest.mark.django_db
def test_explicit_document_type_override_is_honoured(
    default_facility, test_party, test_commodity
):
    """Zero tax would normally imply a Bill of Supply; an explicit choice wins."""
    invoice = _make_invoice(default_facility, test_party, test_commodity)

    adjusted = adjust_invoice(
        invoice_id=invoice.id,
        cgst_rate=Decimal('0.00'),
        sgst_rate=Decimal('0.00'),
        igst_rate=Decimal('0.00'),
        document_type=Invoice.DocumentType.TAX_INVOICE,
    )

    assert adjusted.gst_amount == Decimal('0.00')
    assert adjusted.document_type == Invoice.DocumentType.TAX_INVOICE


@pytest.mark.django_db
def test_adjust_carries_gst_metadata(
    default_facility, test_party, test_commodity
):
    invoice = _make_invoice(default_facility, test_party, test_commodity)

    adjusted = adjust_invoice(
        invoice_id=invoice.id,
        place_of_supply="08",
        is_reverse_charge=True,
        exemption_reason="Storage of agricultural produce",
    )

    assert adjusted.place_of_supply == "08"
    assert adjusted.is_reverse_charge is True
    assert adjusted.exemption_reason == "Storage of agricultural produce"


@pytest.mark.django_db
def test_generation_respects_facility_default_gst_rate(
    default_facility, test_party, test_commodity
):
    """Most of this business is exempt, so a facility can default to zero tax."""
    default_facility.default_gst_rate = Decimal('0.00')
    default_facility.save()

    invoice = _make_invoice(default_facility, test_party, test_commodity)

    assert invoice.cgst_rate == Decimal('0.00')
    assert invoice.sgst_rate == Decimal('0.00')
    assert invoice.gst_amount == Decimal('0.00')
    assert invoice.document_type == Invoice.DocumentType.BILL_OF_SUPPLY
    assert invoice.total_amount == invoice.subtotal


@pytest.mark.django_db
def test_generation_accepts_explicit_rates_and_discount(
    default_facility, test_party, test_commodity
):
    invoice = _make_invoice(
        default_facility, test_party, test_commodity,
        cgst_rate=Decimal('0.00'),
        sgst_rate=Decimal('0.00'),
        igst_rate=Decimal('18.00'),
        discount_amount=Decimal('250.00'),
    )

    assert invoice.discount_amount == Decimal('250.00')
    assert invoice.taxable_value == invoice.subtotal - Decimal('250.00')
    assert invoice.cgst_amount == Decimal('0.00')
    assert invoice.sgst_amount == Decimal('0.00')
    assert invoice.igst_amount == (
        invoice.taxable_value * Decimal('18.00') / 100
    ).quantize(Decimal('0.01'))
    assert invoice.gst_amount == invoice.igst_amount
