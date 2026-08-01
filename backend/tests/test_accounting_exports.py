import pytest
import csv
import io
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from django.urls import path, include
from rest_framework import status

from apps.parties.services import create_party
from apps.invoicing.models import Invoice, InvoiceLine
from apps.facilities.models import Facility

urlpatterns = [
    path('api/', include('apps.invoicing.urls')),
]

pytestmark = pytest.mark.urls('tests.test_accounting_exports')


@pytest.fixture
def test_party_helper(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Export Customer & Sons",
        type="DEPOSITOR",
        gstin="27ABCDE1234F1Z5"
    )


@pytest.mark.django_db
def test_endpoints_require_authentication(api_client, default_facility):
    # CSV Register export
    url_csv = f"/api/exports/invoice-register/?facility={default_facility.id}"
    res_csv = api_client.get(url_csv)
    assert res_csv.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    # Tally XML export
    url_tally = f"/api/exports/tally/?facility={default_facility.id}"
    res_tally = api_client.get(url_tally)
    assert res_tally.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_csv_summary_and_line_exports_return_correct_rows(auth_client, default_facility, test_party_helper):
    # Create a POSTED invoice with lines
    invoice = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-2026-27-000001",
        party=test_party_helper,
        invoice_date=date(2026, 6, 1),
        status=Invoice.Status.POSTED,
        financial_year="2026-27",
        subtotal=Decimal("1000.00"),
        discount_amount=Decimal("100.00"),
        taxable_value=Decimal("900.00"),
        cgst_rate=Decimal("9.00"),
        cgst_amount=Decimal("81.00"),
        sgst_rate=Decimal("9.00"),
        sgst_amount=Decimal("81.00"),
        igst_rate=Decimal("0.00"),
        igst_amount=Decimal("0.00"),
        gst_amount=Decimal("162.00"),
        total_amount=Decimal("1062.00"),
        document_type=Invoice.DocumentType.TAX_INVOICE,
        place_of_supply="27",
    )

    InvoiceLine.objects.create(
        invoice=invoice,
        charge_type=InvoiceLine.ChargeType.RENT,
        sac_code="996729",
        description="Chamber Rent",
        quantity=10,
        unit="BAGS",
        rate_per_unit=Decimal("100.00"),
        amount=Decimal("1000.00"),
        period_from=date(2026, 5, 1),
        period_to=date(2026, 5, 31)
    )

    # 1. Test Summary View (Default)
    url_summary = f"/api/exports/invoice-register/?facility={default_facility.id}&detail=summary"
    res_summary = auth_client.get(url_summary)
    assert res_summary.status_code == status.HTTP_200_OK
    assert res_summary['Content-Type'].startswith('text/csv')
    assert 'Content-Disposition' in res_summary
    assert 'invoice_register_summary_FAC-01_2026-27.csv' in res_summary['Content-Disposition']

    reader_summary = csv.reader(io.StringIO(res_summary.content.decode('utf-8')))
    rows_summary = list(reader_summary)
    assert len(rows_summary) == 2  # Header + 1 row
    
    header_summary = rows_summary[0]
    data_row_summary = rows_summary[1]

    # Verify key fields in header & data
    assert "invoice_number" in header_summary
    assert data_row_summary[header_summary.index("invoice_number")] == "INV-2026-27-000001"
    assert data_row_summary[header_summary.index("subtotal")] == "1000.00"
    assert data_row_summary[header_summary.index("discount")] == "100.00"
    assert data_row_summary[header_summary.index("taxable_value")] == "900.00"
    assert data_row_summary[header_summary.index("cgst_amount")] == "81.00"
    assert data_row_summary[header_summary.index("total_amount")] == "1062.00"

    # 2. Test Lines View
    url_lines = f"/api/exports/invoice-register/?facility={default_facility.id}&detail=lines"
    res_lines = auth_client.get(url_lines)
    assert res_lines.status_code == status.HTTP_200_OK
    assert res_lines['Content-Type'].startswith('text/csv')
    assert 'invoice_register_lines_FAC-01_2026-27.csv' in res_lines['Content-Disposition']

    reader_lines = csv.reader(io.StringIO(res_lines.content.decode('utf-8')))
    rows_lines = list(reader_lines)
    assert len(rows_lines) == 2  # Header + 1 row

    header_lines = rows_lines[0]
    data_row_lines = rows_lines[1]

    assert "charge_type" in header_lines
    assert data_row_lines[header_lines.index("charge_type")] == "RENT"
    assert data_row_lines[header_lines.index("sac_code")] == "996729"
    assert data_row_lines[header_lines.index("amount")] == "1000.00"


@pytest.mark.django_db
def test_only_posted_invoices_appear(auth_client, default_facility, test_party_helper):
    # 1. Create a DRAFT invoice
    Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-DRAFT-01",
        party=test_party_helper,
        invoice_date=date(2026, 6, 1),
        status=Invoice.Status.DRAFT,
        financial_year="2026-27",
        total_amount=Decimal("500.00"),
    )

    # 2. Create a CANCELLED invoice
    Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-CANCELLED-01",
        party=test_party_helper,
        invoice_date=date(2026, 6, 2),
        status=Invoice.Status.CANCELLED,
        financial_year="2026-27",
        total_amount=Decimal("800.00"),
    )

    # 3. Create a POSTED invoice
    Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-POSTED-01",
        party=test_party_helper,
        invoice_date=date(2026, 6, 3),
        status=Invoice.Status.POSTED,
        financial_year="2026-27",
        total_amount=Decimal("1200.00"),
    )

    # Check CSV Export
    url_csv = f"/api/exports/invoice-register/?facility={default_facility.id}"
    res_csv = auth_client.get(url_csv)
    assert res_csv.status_code == status.HTTP_200_OK
    content_csv = res_csv.content.decode('utf-8')
    
    assert "INV-POSTED-01" in content_csv
    assert "INV-DRAFT-01" not in content_csv
    assert "INV-CANCELLED-01" not in content_csv

    # Check Tally XML Export
    url_tally = f"/api/exports/tally/?facility={default_facility.id}"
    res_tally = auth_client.get(url_tally)
    assert res_tally.status_code == status.HTTP_200_OK
    content_tally = res_tally.content.decode('utf-8')

    assert "INV-POSTED-01" in content_tally
    assert "INV-DRAFT-01" not in content_tally
    assert "INV-CANCELLED-01" not in content_tally


@pytest.mark.django_db
def test_financial_year_filtering_selects_right_invoices(auth_client, default_facility, test_party_helper):
    # Invoice in FY 2025-26 (31 March 2026)
    Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-2025-26-000001",
        party=test_party_helper,
        invoice_date=date(2026, 3, 31),
        status=Invoice.Status.POSTED,
        financial_year="2025-26",
        total_amount=Decimal("100.00"),
    )

    # Invoice in FY 2026-27 (1 April 2026)
    Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-2026-27-000001",
        party=test_party_helper,
        invoice_date=date(2026, 4, 1),
        status=Invoice.Status.POSTED,
        financial_year="2026-27",
        total_amount=Decimal("200.00"),
    )

    # Filter by 2025-26
    res_25_26 = auth_client.get(f"/api/exports/invoice-register/?facility={default_facility.id}&financial_year=2025-26")
    content_25_26 = res_25_26.content.decode('utf-8')
    assert "INV-2025-26-000001" in content_25_26
    assert "INV-2026-27-000001" not in content_25_26

    # Filter by 2026-27
    res_26_27 = auth_client.get(f"/api/exports/invoice-register/?facility={default_facility.id}&financial_year=2026-27")
    content_26_27 = res_26_27.content.decode('utf-8')
    assert "INV-2026-27-000001" in content_26_27
    assert "INV-2025-26-000001" not in content_26_27


@pytest.mark.django_db
def test_tally_xml_parses_and_vouchers_balance_to_zero(auth_client, default_facility, test_party_helper):
    invoice = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-TALLY-001",
        party=test_party_helper,
        invoice_date=date(2026, 6, 1),
        status=Invoice.Status.POSTED,
        financial_year="2026-27",
        subtotal=Decimal("1500.50"),
        discount_amount=Decimal("150.00"),
        taxable_value=Decimal("1350.50"),
        cgst_rate=Decimal("9.00"),
        cgst_amount=Decimal("121.55"),  # 1350.50 * 0.09 = 121.545 -> rounds to 121.55
        sgst_rate=Decimal("9.00"),
        sgst_amount=Decimal("121.55"),
        igst_rate=Decimal("0.00"),
        igst_amount=Decimal("0.00"),
        gst_amount=Decimal("243.10"),
        total_amount=Decimal("1593.60"),  # 1350.50 + 243.10 = 1593.60
        document_type=Invoice.DocumentType.TAX_INVOICE,
    )

    InvoiceLine.objects.create(
        invoice=invoice,
        charge_type=InvoiceLine.ChargeType.RENT,
        sac_code="996729",
        description="Rent Line",
        quantity=1,
        unit="MONTH",
        rate_per_unit=Decimal("1000.00"),
        amount=Decimal("1000.00"),
    )

    InvoiceLine.objects.create(
        invoice=invoice,
        charge_type=InvoiceLine.ChargeType.LOADING_UNLOADING,
        sac_code="998619",
        description="Handling Line",
        quantity=10,
        unit="BAGS",
        rate_per_unit=Decimal("50.05"),
        amount=Decimal("500.50"),
    )

    # Request Tally XML
    res = auth_client.get(f"/api/exports/tally/?facility={default_facility.id}")
    assert res.status_code == status.HTTP_200_OK
    assert res['Content-Type'].startswith('application/xml')

    # Verify XML well-formedness
    xml_data = res.content
    root = ET.fromstring(xml_data)
    assert root.tag == 'ENVELOPE'

    # Verify SVCOMPANY
    sv_company = root.find(".//SVCURRENTCOMPANY")
    assert sv_company is not None
    assert sv_company.text == default_facility.name

    # Find the voucher
    vouchers = root.findall(".//VOUCHER")
    assert len(vouchers) == 1
    voucher = vouchers[0]
    assert voucher.attrib['VCHTYPE'] == 'Sales'

    # Check DATE, VOUCHERNUMBER, PARTYLEDGERNAME
    assert voucher.find("DATE").text == "20260601"
    assert voucher.find("VOUCHERNUMBER").text == "INV-TALLY-001"
    assert voucher.find("PARTYLEDGERNAME").text == invoice.party_name_snapshot or test_party_helper.name

    # Check ledger entries balance to zero
    ledger_entries = voucher.findall("ALLLEDGERENTRIES.LIST")
    assert len(ledger_entries) > 0

    running_sum = Decimal('0.00')
    for le in ledger_entries:
        ledger_name = le.find("LEDGERNAME").text
        is_deemed = le.find("ISDEEMEDPOSITIVE").text
        amount_val = Decimal(le.find("AMOUNT").text)
        
        # Verify sign convention
        if is_deemed == 'Yes':
            assert amount_val > 0, f"Debit ledger {ledger_name} must have a positive amount"
        else:
            assert amount_val < 0, f"Credit ledger {ledger_name} must have a negative amount"

        running_sum += amount_val

    assert running_sum == Decimal('0.00'), f"Voucher entries did not balance to zero! Sum is {running_sum}"


@pytest.mark.django_db
def test_party_name_with_special_characters_roundtrips(auth_client, default_facility):
    # Party name containing '&' and '"'
    special_name = 'M/s Quick & Fast "Logistics" Ltd'
    party = create_party(
        facility_id=default_facility.id,
        name=special_name,
        type="DEPOSITOR",
        gstin="27ABCDE1234F1Z5"
    )

    invoice = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-SPECIAL-01",
        party=party,
        party_name_snapshot=special_name,
        invoice_date=date(2026, 6, 1),
        status=Invoice.Status.POSTED,
        financial_year="2026-27",
        total_amount=Decimal("100.00"),
    )

    res = auth_client.get(f"/api/exports/tally/?facility={default_facility.id}")
    assert res.status_code == status.HTTP_200_OK

    root = ET.fromstring(res.content)
    
    # PARTYLEDGERNAME should match special_name exactly (roundtripped through XML parsing)
    party_ledger_name_el = root.find(".//PARTYLEDGERNAME")
    assert party_ledger_name_el is not None
    assert party_ledger_name_el.text == special_name

    # The ledger name in the entries for the party ledger should also match exactly
    party_ledger_entry_name = root.find(".//ALLLEDGERENTRIES.LIST[ISDEEMEDPOSITIVE='Yes']/LEDGERNAME")
    assert party_ledger_entry_name is not None
    assert party_ledger_entry_name.text == special_name
