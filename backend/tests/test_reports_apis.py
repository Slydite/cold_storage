import pytest
from datetime import date
from decimal import Decimal
from rest_framework import status
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.delivery.services import create_delivery_note
from apps.delivery.models import DeliveryNote
from apps.billing.models import RateCard
from apps.billing.services import create_rate_card, create_rent_run, post_rent_run
from apps.invoicing.services import generate_invoices_for_rent_run


@pytest.fixture
def party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Report Test Farmer",
        code="REP-FARM-01",
        type="DEPOSITOR",
        gstin="27ABCDE1234F1Z5"
    )


@pytest.fixture
def commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Potato",
        code="POT-01",
        unit="BAGS"
    )


@pytest.mark.django_db
def test_unauthenticated_reports_denied(api_client):
    assert api_client.get('/api/reports/stock-summary/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/reports/grn-register/?facility_id=1').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/reports/dn-register/?facility_id=1').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/reports/rent-runs/1/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/reports/invoices/?facility_id=1').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_stock_summary_api_json_and_csv(auth_client, default_facility, party, commodity):
    # Create posted GRN with 200 bags, 50kg each in Chamber A
    create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 10),
        items=[{
            "commodity_id": commodity.id,
            "chamber": "Chamber A",
            "initial_qty": 200,
            "unit_weight": Decimal('50.00')
        }]
    )

    # JSON test
    res = auth_client.get(f'/api/reports/stock-summary/?facility_id={default_facility.id}')
    assert res.status_code == status.HTTP_200_OK
    assert "by_commodity" in res.data
    assert "by_chamber" in res.data
    assert len(res.data["by_commodity"]) == 1
    assert res.data["by_commodity"][0]["total_qty"] == 200
    assert res.data["by_commodity"][0]["total_weight_kg"] == 10000.0
    assert len(res.data["by_chamber"]) == 1
    assert res.data["by_chamber"][0]["chamber"] == "Chamber A"
    assert res.data["by_chamber"][0]["total_qty"] == 200

    # CSV test
    res_csv = auth_client.get(f'/api/reports/stock-summary/?facility_id={default_facility.id}&export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert 'stock-summary.csv' in res_csv.headers['Content-Disposition']
    csv_content = res_csv.content.decode('utf-8')
    assert "facility_id,facility_name,commodity_id,commodity_name,total_qty,total_weight_kg" in csv_content
    assert "200" in csv_content


@pytest.mark.django_db
def test_grn_register_api_json_csv_and_date_filter(auth_client, default_facility, party, commodity):
    # Missing facility_id -> 400
    res_err = auth_client.get('/api/reports/grn-register/')
    assert res_err.status_code == status.HTTP_400_BAD_REQUEST

    # Create GRN on 2026-07-15
    create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 15),
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100
        }]
    )

    # Date filter matching -> returns 1 row
    res_match = auth_client.get(f'/api/reports/grn-register/?facility_id={default_facility.id}&date_from=2026-07-01&date_to=2026-07-31')
    assert res_match.status_code == status.HTTP_200_OK
    assert len(res_match.data) == 1

    # Date filter excluding -> returns 0 rows
    res_excl = auth_client.get(f'/api/reports/grn-register/?facility_id={default_facility.id}&date_from=2026-08-01')
    assert res_excl.status_code == status.HTTP_200_OK
    assert len(res_excl.data) == 0

    # CSV test
    res_csv = auth_client.get(f'/api/reports/grn-register/?facility_id={default_facility.id}&export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert 'grn-register.csv' in res_csv.headers['Content-Disposition']


@pytest.mark.django_db
def test_dn_register_api_json_csv_and_date_filter(auth_client, default_facility, party, commodity):
    # Missing facility_id -> 400
    res_err = auth_client.get('/api/reports/dn-register/')
    assert res_err.status_code == status.HTTP_400_BAD_REQUEST

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": commodity.id, "initial_qty": 100}]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 7, 20),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 30}]
    )

    # Date filter matching -> returns 1 row
    res_match = auth_client.get(f'/api/reports/dn-register/?facility_id={default_facility.id}&date_from=2026-07-01&date_to=2026-07-31')
    assert res_match.status_code == status.HTTP_200_OK
    assert len(res_match.data) == 1

    # Date filter excluding -> returns 0 rows
    res_excl = auth_client.get(f'/api/reports/dn-register/?facility_id={default_facility.id}&date_from=2026-08-01')
    assert res_excl.status_code == status.HTTP_200_OK
    assert len(res_excl.data) == 0

    # CSV test
    res_csv = auth_client.get(f'/api/reports/dn-register/?facility_id={default_facility.id}&export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert 'dn-register.csv' in res_csv.headers['Content-Disposition']


@pytest.mark.django_db
def test_rent_run_report_api_json_csv_and_404(auth_client, default_facility, party, commodity):
    # Non-existent ID -> 404
    res_404 = auth_client.get('/api/reports/rent-runs/99999/')
    assert res_404.status_code == status.HTTP_404_NOT_FOUND

    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )
    create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": commodity.id, "initial_qty": 50, "unit_weight": Decimal('50.00')}]
    )
    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )

    # JSON test
    res_json = auth_client.get(f'/api/reports/rent-runs/{rent_run.id}/')
    assert res_json.status_code == status.HTTP_200_OK
    assert res_json.data['id'] == rent_run.id
    assert len(res_json.data['lines']) == 1

    # CSV test
    res_csv = auth_client.get(f'/api/reports/rent-runs/{rent_run.id}/?export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert f'rent-run-{rent_run.id}.csv' in res_csv.headers['Content-Disposition']
    csv_text = res_csv.content.decode('utf-8')
    assert "TOTAL" in csv_text


@pytest.mark.django_db
def test_invoice_register_api_json_csv_and_date_filter(auth_client, default_facility, party, commodity):
    # Missing facility_id -> 400
    res_err = auth_client.get('/api/reports/invoices/')
    assert res_err.status_code == status.HTTP_400_BAD_REQUEST

    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )
    create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": commodity.id, "initial_qty": 50, "unit_weight": Decimal('50.00')}]
    )
    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    post_rent_run(rent_run_id=rent_run.id)
    invoices = generate_invoices_for_rent_run(facility_id=default_facility.id, rent_run_id=rent_run.id)
    inv = invoices[0]

    # Date filter matching
    res_match = auth_client.get(f'/api/reports/invoices/?facility_id={default_facility.id}&date_from={inv.invoice_date}')
    assert res_match.status_code == status.HTTP_200_OK
    assert len(res_match.data) == 1

    # Date filter excluding -> 0 rows
    res_excl = auth_client.get(f'/api/reports/invoices/?facility_id={default_facility.id}&date_from=2030-01-01')
    assert res_excl.status_code == status.HTTP_200_OK
    assert len(res_excl.data) == 0

    # CSV test
    res_csv = auth_client.get(f'/api/reports/invoices/?facility_id={default_facility.id}&export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert 'invoice-register.csv' in res_csv.headers['Content-Disposition']
