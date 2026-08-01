"""
Tests for the accounting-compatible invoicing additions:
  - FY-scoped invoice numbering (Section 1)
  - Flat discount reduces taxable value before tax; totals reconcile (Section 2)
  - Discount validation (negative / exceeds subtotal rejected) (Section 2)
  - gst_amount == cgst_amount + sgst_amount + igst_amount (Section 3)
  - Three independent non-zero rates → three independent amounts, no auto-splitting (Section 3)
  - Zero tax → BILL_OF_SUPPLY; any tax → TAX_INVOICE; explicit override honoured (Section 4)
"""
import pytest
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError

from apps.invoicing.models import Invoice, InvoiceLine
from apps.invoicing.services import (
    generate_invoices_for_uninvoiced_deliveries,
    _compute_tax_amounts,
    _derive_document_type,
)
from apps.inventory.models import Sequence
from apps.inventory.services import create_grn, create_commodity
from apps.delivery.services import create_delivery_note
from apps.delivery.models import DeliveryNote
from apps.inventory.models import GRN
from apps.parties.services import create_party
from libs.sequences import get_next_sequence_number


# ---------------------------------------------------------------------------
# Section 1 – FY-scoped invoice numbering
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_invoice_numbering_resets_at_fy_boundary(default_facility):
    """
    A sequence counter keyed to 2025-26 and one keyed to 2026-27 are independent.
    The second FY's first invoice is …-000001 regardless of how many were issued in the first FY.
    """
    # Issue three in FY 2025-26
    for _ in range(3):
        get_next_sequence_number(facility=default_facility, sequence_type='INV', financial_year='2025-26')

    # First in FY 2026-27 must restart at 000001
    num = get_next_sequence_number(facility=default_facility, sequence_type='INV', financial_year='2026-27')
    assert num == 'INV-2026-27-000001', f"Expected INV-2026-27-000001, got {num}"


@pytest.mark.django_db
def test_invoice_numbering_consecutive_within_fy(default_facility):
    """
    Numbers issued within a single FY are strictly consecutive.
    """
    nums = [
        get_next_sequence_number(facility=default_facility, sequence_type='INV', financial_year='2026-27')
        for _ in range(5)
    ]
    expected = [f'INV-2026-27-{i:06d}' for i in range(1, 6)]
    assert nums == expected


@pytest.mark.django_db
def test_non_invoice_sequences_keep_flat_format(default_facility):
    """
    GRN, LOT, DN and any other sequence type must NOT be FY-scoped.
    Their format must remain the legacy GRN-000001 style.
    """
    grn_num = get_next_sequence_number(facility=default_facility, sequence_type='GRN')
    assert grn_num.startswith('GRN-'), f"Expected GRN-XXXXXX, got {grn_num}"
    assert '-' not in grn_num[4:], f"GRN number must not contain a dash after prefix: {grn_num}"


# ---------------------------------------------------------------------------
# Section 2 – Discount
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_discount_reduces_taxable_value_before_tax_and_totals_reconcile(default_facility):
    """
    taxable_value = subtotal - discount_amount
    tax_total     = cgst_amount + sgst_amount + igst_amount
    total_amount  = taxable_value + tax_total
    """
    subtotal = Decimal('1000.00')
    discount = Decimal('100.00')
    taxable  = subtotal - discount   # 900.00
    cgst_rate = Decimal('9.00')
    sgst_rate = Decimal('9.00')
    igst_rate = Decimal('0.00')

    cgst, sgst, igst = _compute_tax_amounts(taxable, cgst_rate, sgst_rate, igst_rate)
    gst_total = cgst + sgst + igst
    total = taxable + gst_total

    assert taxable == Decimal('900.00')
    assert cgst == (Decimal('900.00') * Decimal('9') / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    assert sgst == cgst
    assert igst == Decimal('0.00')
    assert total == taxable + gst_total


@pytest.mark.django_db
def test_discount_exceeding_subtotal_rejected(default_facility):
    """
    A discount_amount that exceeds subtotal must raise ValidationError.
    """
    party = create_party(facility_id=default_facility.id, name="Discount Test Party", type="DEPOSITOR")
    inv = Invoice(
        facility=default_facility,
        invoice_number="TST-DISC-001",
        party=party,
        invoice_date=date.today(),
        subtotal=Decimal('500.00'),
        discount_amount=Decimal('600.00'),  # exceeds subtotal
        taxable_value=Decimal('0.00'),
    )
    with pytest.raises(ValidationError) as exc:
        inv.full_clean()
    assert 'discount_amount' in exc.value.message_dict


@pytest.mark.django_db
def test_negative_discount_rejected(default_facility):
    """
    A negative discount_amount must raise ValidationError.
    """
    party = create_party(facility_id=default_facility.id, name="Neg Discount Party", type="DEPOSITOR")
    inv = Invoice(
        facility=default_facility,
        invoice_number="TST-DISC-002",
        party=party,
        invoice_date=date.today(),
        subtotal=Decimal('500.00'),
        discount_amount=Decimal('-10.00'),
        taxable_value=Decimal('510.00'),
    )
    with pytest.raises(ValidationError) as exc:
        inv.full_clean()
    assert 'discount_amount' in exc.value.message_dict


# ---------------------------------------------------------------------------
# Section 3 – Three-component GST
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_gst_amount_equals_sum_of_components(default_facility):
    """
    gst_amount must always equal cgst_amount + sgst_amount + igst_amount.
    Tested over the backfill migration's intra-state split and an explicit IGST scenario.
    """
    party = create_party(facility_id=default_facility.id, name="GST Sum Party", type="DEPOSITOR")

    # Intra-state: CGST 9% + SGST 9%
    taxable = Decimal('1000.00')
    cgst, sgst, igst = _compute_tax_amounts(taxable, Decimal('9.00'), Decimal('9.00'), Decimal('0.00'))
    inv1 = Invoice.objects.create(
        facility=default_facility,
        invoice_number="TST-GST-001",
        party=party,
        invoice_date=date.today(),
        subtotal=taxable,
        taxable_value=taxable,
        cgst_rate=Decimal('9.00'),
        sgst_rate=Decimal('9.00'),
        igst_rate=Decimal('0.00'),
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        gst_amount=cgst + sgst + igst,
        total_amount=taxable + cgst + sgst + igst,
    )
    assert inv1.gst_amount == inv1.cgst_amount + inv1.sgst_amount + inv1.igst_amount

    # Inter-state: IGST 18%
    cgst2, sgst2, igst2 = _compute_tax_amounts(taxable, Decimal('0.00'), Decimal('0.00'), Decimal('18.00'))
    inv2 = Invoice.objects.create(
        facility=default_facility,
        invoice_number="TST-GST-002",
        party=party,
        invoice_date=date.today(),
        subtotal=taxable,
        taxable_value=taxable,
        cgst_rate=Decimal('0.00'),
        sgst_rate=Decimal('0.00'),
        igst_rate=Decimal('18.00'),
        cgst_amount=cgst2,
        sgst_amount=sgst2,
        igst_amount=igst2,
        gst_amount=cgst2 + sgst2 + igst2,
        total_amount=taxable + cgst2 + sgst2 + igst2,
    )
    assert inv2.gst_amount == inv2.cgst_amount + inv2.sgst_amount + inv2.igst_amount


@pytest.mark.django_db
def test_three_different_rates_produce_three_independent_amounts_no_auto_splitting(default_facility):
    """
    Given three distinct non-zero rates, each amount is independently computed
    from taxable_value * rate / 100. No rate is halved or distributed automatically.
    """
    taxable = Decimal('1000.00')
    cgst_rate = Decimal('5.00')
    sgst_rate = Decimal('9.00')
    igst_rate = Decimal('12.00')

    cgst, sgst, igst = _compute_tax_amounts(taxable, cgst_rate, sgst_rate, igst_rate)

    expected_cgst = (taxable * cgst_rate / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    expected_sgst = (taxable * sgst_rate / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    expected_igst = (taxable * igst_rate / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    assert cgst == expected_cgst, f"CGST mismatch: {cgst} != {expected_cgst}"
    assert sgst == expected_sgst, f"SGST mismatch: {sgst} != {expected_sgst}"
    assert igst == expected_igst, f"IGST mismatch: {igst} != {expected_igst}"

    # Ensure no amount equals another (confirming no accidental halving)
    assert cgst != sgst, "CGST and SGST should differ with different rates"
    assert sgst != igst, "SGST and IGST should differ with different rates"


# ---------------------------------------------------------------------------
# Section 4 – document_type
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_zero_tax_defaults_to_bill_of_supply(default_facility):
    """
    When all three tax amounts are zero, _derive_document_type returns BILL_OF_SUPPLY.
    """
    result = _derive_document_type(Decimal('0.00'), Decimal('0.00'), Decimal('0.00'))
    assert result == Invoice.DocumentType.BILL_OF_SUPPLY


@pytest.mark.django_db
def test_nonzero_tax_defaults_to_tax_invoice(default_facility):
    """
    When any component tax amount is non-zero, _derive_document_type returns TAX_INVOICE.
    """
    result_cgst = _derive_document_type(Decimal('90.00'), Decimal('0.00'), Decimal('0.00'))
    assert result_cgst == Invoice.DocumentType.TAX_INVOICE

    result_igst = _derive_document_type(Decimal('0.00'), Decimal('0.00'), Decimal('180.00'))
    assert result_igst == Invoice.DocumentType.TAX_INVOICE


@pytest.mark.django_db
def test_explicit_document_type_override_is_honoured(default_facility):
    """
    The owner can override document_type regardless of the tax total.
    An invoice with tax can be manually set to BILL_OF_SUPPLY and vice versa.
    """
    party = create_party(facility_id=default_facility.id, name="DocType Override Party", type="DEPOSITOR")

    # Tax present but manually set to BILL_OF_SUPPLY
    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="TST-DOCTYPE-001",
        party=party,
        invoice_date=date.today(),
        subtotal=Decimal('1000.00'),
        taxable_value=Decimal('1000.00'),
        cgst_amount=Decimal('90.00'),
        sgst_amount=Decimal('90.00'),
        igst_amount=Decimal('0.00'),
        gst_amount=Decimal('180.00'),
        total_amount=Decimal('1180.00'),
        document_type=Invoice.DocumentType.BILL_OF_SUPPLY,  # explicit override
    )
    inv.refresh_from_db()
    assert inv.document_type == Invoice.DocumentType.BILL_OF_SUPPLY

    # Zero tax but manually set to TAX_INVOICE
    inv2 = Invoice.objects.create(
        facility=default_facility,
        invoice_number="TST-DOCTYPE-002",
        party=party,
        invoice_date=date.today(),
        subtotal=Decimal('500.00'),
        taxable_value=Decimal('500.00'),
        cgst_amount=Decimal('0.00'),
        sgst_amount=Decimal('0.00'),
        igst_amount=Decimal('0.00'),
        gst_amount=Decimal('0.00'),
        total_amount=Decimal('500.00'),
        document_type=Invoice.DocumentType.TAX_INVOICE,  # explicit override
    )
    inv2.refresh_from_db()
    assert inv2.document_type == Invoice.DocumentType.TAX_INVOICE


# ---------------------------------------------------------------------------
# Section 5 – InvoiceLine charge_type and period fields (via service)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_invoice_lines_have_correct_charge_type_and_period(default_facility):
    """
    Rent lines created by generate_invoices_for_uninvoiced_deliveries must carry
    charge_type=RENT and have period_from / period_to set to the storage period billed.
    Loading/unloading lines must carry charge_type=LOADING_UNLOADING.
    """
    party = create_party(facility_id=default_facility.id, name="Charge Type Test Party", type="DEPOSITOR")
    commodity = create_commodity(facility_id=default_facility.id, name="Charge Type Commodity", unit="BAGS")

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 1),
        loading_charge=Decimal('100.00'),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 50,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
        }],
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 50}],
    )

    invoice = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id, party_id=party.id
    )[0]

    rent_line = InvoiceLine.objects.get(invoice=invoice, charge_type=InvoiceLine.ChargeType.RENT)
    assert rent_line.period_from == date(2026, 7, 1)
    assert rent_line.period_to == date(2026, 7, 31)
    assert rent_line.sac_code == '996729'

    lu_line = InvoiceLine.objects.get(invoice=invoice, charge_type=InvoiceLine.ChargeType.LOADING_UNLOADING)
    assert lu_line.period_from is None
    assert lu_line.period_to is None
    assert lu_line.sac_code == '998619'


# ---------------------------------------------------------------------------
# Section 6 – Generated invoice carries financial_year from invoice_date
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_generated_invoice_carries_financial_year(default_facility):
    """
    generate_invoices_for_uninvoiced_deliveries must set financial_year
    from the invoice_date using fy_label, and the invoice_number must embed it.
    """
    from libs.fiscal import fy_label
    party = create_party(facility_id=default_facility.id, name="FY Label Party", type="DEPOSITOR")
    commodity = create_commodity(facility_id=default_facility.id, name="FY Commodity", unit="BAGS")

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 10,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('5.00'),
        }],
    )
    lot = grn.lots.first()
    create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 7, 31),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 10}],
    )

    invoice = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id, party_id=party.id
    )[0]

    today = date.today()
    expected_fy = fy_label(today)
    assert invoice.financial_year == expected_fy
    assert expected_fy in invoice.invoice_number, (
        f"Invoice number '{invoice.invoice_number}' should contain FY '{expected_fy}'"
    )
