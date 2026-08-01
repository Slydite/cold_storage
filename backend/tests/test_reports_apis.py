import pytest
from datetime import date
from decimal import Decimal
from rest_framework import status
from apps.facilities.models import Facility
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.delivery.services import create_delivery_note
from apps.delivery.models import DeliveryNote
from apps.invoicing.services import (
    generate_invoices_for_uninvoiced_deliveries,
    record_payment,
    delete_payment,
)


@pytest.fixture
def party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Report Test Farmer",
        type="DEPOSITOR",
        gstin="27ABCDE1234F1Z5"
    )


@pytest.fixture
def commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Potato",
        unit="BAGS"
    )



@pytest.mark.django_db
def test_unauthenticated_reports_denied(api_client):
    assert api_client.get('/api/reports/stock-summary/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/reports/grn-register/?facility_id=1').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/reports/dn-register/?facility_id=1').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/reports/invoices/?facility_id=1').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/reports/payments/?facility_id=1').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)



@pytest.mark.django_db
def test_stock_summary_api_json_and_csv(auth_client, default_facility, party, commodity):
    from apps.locations.services import create_chamber, create_floor, create_block
    ch_a = create_chamber(facility_id=default_facility.id, name="Chamber A")
    fl_a = create_floor(chamber_id=ch_a.id, name="Floor A")
    bl_a = create_block(floor_id=fl_a.id, name="Block A")

    create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 10),
        items=[{
            "commodity_id": commodity.id,
            "chamber": "Chamber A",
            "initial_qty": 200,
            "unit_weight": Decimal('50.00'),
            "block_id": bl_a.id,
        }]
    )

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

    res_csv = auth_client.get(f'/api/reports/stock-summary/?facility_id={default_facility.id}&export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert 'stock-summary.csv' in res_csv.headers['Content-Disposition']
    csv_content = res_csv.content.decode('utf-8')
    assert "facility_id,facility_name,commodity_id,commodity_name,total_qty,total_weight_kg" in csv_content
    assert "200" in csv_content


@pytest.mark.django_db
def test_grn_register_api_json_csv_and_date_filter(auth_client, default_facility, party, commodity, default_block):
    res_err = auth_client.get('/api/reports/grn-register/')
    assert res_err.status_code == status.HTTP_400_BAD_REQUEST

    create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 15),
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )

    res_match = auth_client.get(f'/api/reports/grn-register/?facility_id={default_facility.id}&date_from=2026-07-01&date_to=2026-07-31')
    assert res_match.status_code == status.HTTP_200_OK
    assert len(res_match.data) == 1

    res_excl = auth_client.get(f'/api/reports/grn-register/?facility_id={default_facility.id}&date_from=2026-08-01')
    assert res_excl.status_code == status.HTTP_200_OK
    assert len(res_excl.data) == 0

    res_csv = auth_client.get(f'/api/reports/grn-register/?facility_id={default_facility.id}&export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert 'grn-register.csv' in res_csv.headers['Content-Disposition']


@pytest.mark.django_db
def test_dn_register_api_json_csv_and_date_filter(auth_client, default_facility, party, commodity, default_block):
    res_err = auth_client.get('/api/reports/dn-register/')
    assert res_err.status_code == status.HTTP_400_BAD_REQUEST

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": commodity.id, "initial_qty": 100, "block_id": default_block.id}]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 7, 20),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 30}]
    )

    res_match = auth_client.get(f'/api/reports/dn-register/?facility_id={default_facility.id}&date_from=2026-07-01&date_to=2026-07-31')
    assert res_match.status_code == status.HTTP_200_OK
    assert len(res_match.data) == 1

    res_excl = auth_client.get(f'/api/reports/dn-register/?facility_id={default_facility.id}&date_from=2026-08-01')
    assert res_excl.status_code == status.HTTP_200_OK
    assert len(res_excl.data) == 0

    res_csv = auth_client.get(f'/api/reports/dn-register/?facility_id={default_facility.id}&export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert 'dn-register.csv' in res_csv.headers['Content-Disposition']


@pytest.mark.django_db
def test_invoice_register_api_json_csv_and_date_filter(auth_client, default_facility, party, commodity, default_block):
    res_err = auth_client.get('/api/reports/invoices/')
    assert res_err.status_code == status.HTTP_400_BAD_REQUEST

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": commodity.id, "initial_qty": 50, "unit_weight": Decimal('50.00'), "rent_rate_per_unit": Decimal('50.00'), "block_id": default_block.id}]
    )
    lot = grn.lots.first()

    create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 7, 20),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 30}]
    )

    invoices = generate_invoices_for_uninvoiced_deliveries(facility_id=default_facility.id, party_id=party.id)
    inv = invoices[0]

    res_match = auth_client.get(f'/api/reports/invoices/?facility_id={default_facility.id}&date_from={inv.invoice_date}')
    assert res_match.status_code == status.HTTP_200_OK
    assert len(res_match.data) == 1

    res_excl = auth_client.get(f'/api/reports/invoices/?facility_id={default_facility.id}&date_from=2030-01-01')
    assert res_excl.status_code == status.HTTP_200_OK
    assert len(res_excl.data) == 0

    res_csv = auth_client.get(f'/api/reports/invoices/?facility_id={default_facility.id}&export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert 'invoice-register.csv' in res_csv.headers['Content-Disposition']


def _helper_create_invoice(facility_id, party_id, commodity_id):
    from apps.locations.models import Chamber, Floor, Block
    from apps.locations.services import create_chamber, create_floor, create_block
    chamber = Chamber.objects.filter(facility_id=facility_id, name="Report Temp Chamber").first()
    if not chamber:
        chamber = create_chamber(facility_id=facility_id, name="Report Temp Chamber")
    floor = Floor.objects.filter(chamber_id=chamber.id, name="Report Temp Floor").first()
    if not floor:
        floor = create_floor(chamber_id=chamber.id, name="Report Temp Floor")
    block = Block.objects.filter(floor_id=floor.id, name="Report Temp Block").first()
    if not block:
        block = create_block(floor_id=floor.id, name="Report Temp Block")
    grn = create_grn(
        facility_id=facility_id,
        party_id=party_id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": commodity_id, "initial_qty": 50, "unit_weight": Decimal('50.00'), "rent_rate_per_unit": Decimal('50.00'), "block_id": block.id}]
    )
    lot = grn.lots.first()
    create_delivery_note(
        facility_id=facility_id,
        party_id=party_id,
        dispatch_date=date(2026, 7, 10),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 10}]
    )
    invoices = generate_invoices_for_uninvoiced_deliveries(facility_id=facility_id, party_id=party_id)
    return invoices[0]


@pytest.mark.django_db
def test_payment_register_facility_id_required(auth_client):
    res_no_param = auth_client.get('/api/reports/payments/')
    assert res_no_param.status_code == status.HTTP_400_BAD_REQUEST
    assert 'facility_id' in res_no_param.data

    res_invalid_param = auth_client.get('/api/reports/payments/?facility_id=abc')
    assert res_invalid_param.status_code == status.HTTP_400_BAD_REQUEST
    assert 'facility_id' in res_invalid_param.data


@pytest.mark.django_db
def test_payment_register_facility_isolation(auth_client, default_facility, party, commodity):
    fac2 = Facility.objects.create(code="FAC-02", name="Second Facility", address="456 Logistics Park")
    party2 = create_party(facility_id=fac2.id, name="Fac2 Farmer", type="DEPOSITOR")
    comm2 = create_commodity(facility_id=fac2.id, name="Apple", unit="BOXES")

    inv1 = _helper_create_invoice(default_facility.id, party.id, commodity.id)
    inv2 = _helper_create_invoice(fac2.id, party2.id, comm2.id)

    record_payment(
        invoice_id=inv1.id,
        amount=Decimal('100.00'),
        payment_date=date(2026, 7, 15),
        method='CASH'
    )
    record_payment(
        invoice_id=inv2.id,
        amount=Decimal('200.00'),
        payment_date=date(2026, 7, 15),
        method='CASH'
    )

    res1 = auth_client.get(f'/api/reports/payments/?facility_id={default_facility.id}')
    assert res1.status_code == status.HTTP_200_OK
    assert len(res1.data['results']) == 1
    assert res1.data['results'][0]['invoice_id'] == inv1.id
    assert res1.data['total_amount'] == '100.00'

    res2 = auth_client.get(f'/api/reports/payments/?facility_id={fac2.id}')
    assert res2.status_code == status.HTTP_200_OK
    assert len(res2.data['results']) == 1
    assert res2.data['results'][0]['invoice_id'] == inv2.id
    assert res2.data['total_amount'] == '200.00'


@pytest.mark.django_db
def test_payment_register_filters_and_inclusive_dates(auth_client, default_facility, party, commodity):
    party2 = create_party(facility_id=default_facility.id, name="Second Farmer", type="DEPOSITOR")

    inv1 = _helper_create_invoice(default_facility.id, party.id, commodity.id)
    inv2 = _helper_create_invoice(default_facility.id, party2.id, commodity.id)

    p1 = record_payment(invoice_id=inv1.id, amount=Decimal('100.00'), payment_date=date(2026, 7, 1), method='CASH')
    p2 = record_payment(invoice_id=inv1.id, amount=Decimal('200.00'), payment_date=date(2026, 7, 15), method='BANK_TRANSFER')
    p3 = record_payment(invoice_id=inv2.id, amount=Decimal('300.00'), payment_date=date(2026, 7, 31), method='UPI')

    # Party filter
    res_party = auth_client.get(f'/api/reports/payments/?facility_id={default_facility.id}&party_id={party.id}')
    assert res_party.status_code == status.HTTP_200_OK
    assert len(res_party.data['results']) == 2
    ids = {r['id'] for r in res_party.data['results']}
    assert ids == {p1.id, p2.id}

    # Method filter
    res_method = auth_client.get(f'/api/reports/payments/?facility_id={default_facility.id}&method=BANK_TRANSFER')
    assert res_method.status_code == status.HTTP_200_OK
    assert len(res_method.data['results']) == 1
    assert res_method.data['results'][0]['id'] == p2.id

    # Inclusive date range filter (2026-07-15 to 2026-07-31 includes p2 on 15th and p3 on 31st)
    res_dates = auth_client.get(f'/api/reports/payments/?facility_id={default_facility.id}&date_from=2026-07-15&date_to=2026-07-31')
    assert res_dates.status_code == status.HTTP_200_OK
    assert len(res_dates.data['results']) == 2
    date_ids = {r['id'] for r in res_dates.data['results']}
    assert date_ids == {p2.id, p3.id}

    # Invalid date error check
    res_bad_date = auth_client.get(f'/api/reports/payments/?facility_id={default_facility.id}&date_from=invalid-date')
    assert res_bad_date.status_code == status.HTTP_400_BAD_REQUEST
    assert 'date_from' in res_bad_date.data


@pytest.mark.django_db
def test_payment_register_total_equals_sum_exact_decimals(auth_client, default_facility, party, commodity):
    inv = _helper_create_invoice(default_facility.id, party.id, commodity.id)
    p1_amt = Decimal('123.45')
    p2_amt = Decimal('678.90')

    record_payment(invoice_id=inv.id, amount=p1_amt, payment_date=date(2026, 7, 10), method='CASH')
    record_payment(invoice_id=inv.id, amount=p2_amt, payment_date=date(2026, 7, 11), method='CHEQUE')

    res = auth_client.get(f'/api/reports/payments/?facility_id={default_facility.id}')
    assert res.status_code == status.HTTP_200_OK

    total_from_api = Decimal(res.data['total_amount'])
    expected_total = p1_amt + p2_amt
    assert total_from_api == expected_total
    assert total_from_api == Decimal('802.35')

    row_sum = sum((Decimal(row['amount']) for row in res.data['results']), Decimal('0.00'))
    assert row_sum == total_from_api


@pytest.mark.django_db
def test_payment_register_csv_export(auth_client, default_facility, party, commodity):
    inv = _helper_create_invoice(default_facility.id, party.id, commodity.id)
    record_payment(invoice_id=inv.id, amount=Decimal('500.00'), payment_date=date(2026, 7, 12), method='UPI', reference='UPI123456', notes='Advance')

    res_csv = auth_client.get(f'/api/reports/payments/?facility_id={default_facility.id}&export_format=csv')
    assert res_csv.status_code == status.HTTP_200_OK
    assert res_csv.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in res_csv.headers['Content-Disposition']
    assert 'payment-register.csv' in res_csv.headers['Content-Disposition']

    content = res_csv.content.decode('utf-8')
    assert "payment_date,invoice_number,party_name,method,reference,amount,notes" in content
    assert "500.00" in content
    assert "UPI123456" in content


@pytest.mark.django_db
def test_payment_register_delete_payment_removes_from_register(auth_client, default_facility, party, commodity):
    inv = _helper_create_invoice(default_facility.id, party.id, commodity.id)
    p = record_payment(invoice_id=inv.id, amount=Decimal('250.00'), payment_date=date(2026, 7, 10), method='CASH')

    res_before = auth_client.get(f'/api/reports/payments/?facility_id={default_facility.id}')
    assert res_before.status_code == status.HTTP_200_OK
    assert len(res_before.data['results']) == 1
    assert Decimal(res_before.data['total_amount']) == Decimal('250.00')

    delete_payment(payment_id=p.id)

    res_after = auth_client.get(f'/api/reports/payments/?facility_id={default_facility.id}')
    assert res_after.status_code == status.HTTP_200_OK
    assert len(res_after.data['results']) == 0
    assert Decimal(res_after.data['total_amount']) == Decimal('0.00')

