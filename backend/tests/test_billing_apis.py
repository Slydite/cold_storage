import pytest
from rest_framework import status
from datetime import date
from decimal import Decimal
from django.urls import path, include
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.billing.services import create_rate_card
from apps.billing.models import RateCard, RentRun, RentRunLine

# Route configuration so tests pass independently of config/urls.py registration
urlpatterns = [
    path('api/', include('apps.billing.urls')),
]

pytestmark = pytest.mark.urls('tests.test_billing_apis')


@pytest.fixture
def test_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Billing API Customer",
        code="CUST-BILL-01",
        type="DEPOSITOR"
    )


@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Green Peas",
        code="PEAS-01",
        unit="BAGS"
    )


@pytest.mark.django_db
def test_unauthenticated_billing_apis_denied(api_client):
    assert api_client.get('/api/rate-cards/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.post('/api/rate-cards/', {}).status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/rent-runs/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.post('/api/rent-runs/', {}).status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.post('/api/rent-runs/preview/', {}).status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/rent-runs/1/pdf/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_rate_card_api_create_list_retrieve(auth_client, default_facility, test_commodity, test_party):
    payload = {
        "facility_id": default_facility.id,
        "commodity_id": test_commodity.id,
        "party_id": test_party.id,
        "weight_category": "KG_50",
        "rate_per_bag_per_month": "45.00",
        "effective_from": "2026-01-01",
        "is_active": True
    }

    # Create RateCard with party_id
    res = auth_client.post('/api/rate-cards/', payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    rc_id = res.data['id']
    assert res.data['commodity_name'] == "Green Peas"
    assert res.data['party_id'] == test_party.id
    assert res.data['party_name'] == "Billing API Customer"
    assert res.data['is_default'] is False
    assert res.data['rate_per_bag_per_month'] == "45.00"

    # List RateCards filtered by party_id
    res_list = auth_client.get(f'/api/rate-cards/?facility_id={default_facility.id}&party_id={test_party.id}')
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1

    # List RateCards filtered by is_default=true
    res_list_def = auth_client.get(f'/api/rate-cards/?facility_id={default_facility.id}&is_default=true')
    assert res_list_def.status_code == status.HTTP_200_OK
    assert len(res_list_def.data) == 0

    # Retrieve RateCard
    res_get = auth_client.get(f'/api/rate-cards/{rc_id}/')
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.data['id'] == rc_id


@pytest.mark.django_db
def test_rent_run_api_preview_does_not_persist(auth_client, default_facility, test_party, test_commodity):
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
        items=[{"commodity_id": test_commodity.id, "initial_qty": 100, "unit_weight": Decimal('50.00')}]
    )

    payload = {
        "facility_id": default_facility.id,
        "period_start": "2026-07-01",
        "period_end": "2026-07-31",
        "party_id": test_party.id,
        "min_billing_days": 10
    }

    initial_run_count = RentRun.objects.count()
    initial_line_count = RentRunLine.objects.count()

    res = auth_client.post('/api/rent-runs/preview/', payload, format='json')
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data['lines']) == 1
    assert res.data['lines'][0]['rate_source'] == 'DEFAULT'
    assert Decimal(res.data['total_amount']) == Decimal('5000.00')

    # Assert no persistence in DB
    assert RentRun.objects.count() == initial_run_count
    assert RentRunLine.objects.count() == initial_line_count


@pytest.mark.django_db
def test_rent_run_api_create_list_retrieve_post_and_pdf(auth_client, default_facility, test_party, test_commodity):
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

    payload = {
        "facility_id": default_facility.id,
        "period_start": "2026-07-01",
        "period_end": "2026-07-31",
        "notes": "Regular July run"
    }

    # Create RentRun
    res = auth_client.post('/api/rent-runs/', payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    run_id = res.data['id']
    assert res.data['status'] == RentRun.Status.DRAFT
    assert res.data['notes'] == "Regular July run"
    assert len(res.data['lines']) == 1
    assert Decimal(res.data['total_amount']) == Decimal('5000.00')

    # List RentRuns
    res_list = auth_client.get(f'/api/rent-runs/?facility_id={default_facility.id}')
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1

    # Retrieve RentRun
    res_get = auth_client.get(f'/api/rent-runs/{run_id}/')
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.data['id'] == run_id

    # Stream PDF
    res_pdf = auth_client.get(f'/api/rent-runs/{run_id}/pdf/')
    assert res_pdf.status_code == status.HTTP_200_OK
    assert res_pdf['Content-Type'] == 'application/pdf'
    assert f'RentRun-{run_id}.pdf' in res_pdf['Content-Disposition']
    assert res_pdf.content.startswith(b'%PDF')

    # Post RentRun
    res_post = auth_client.post(f'/api/rent-runs/{run_id}/post/')
    assert res_post.status_code == status.HTTP_200_OK
    assert res_post.data['status'] == RentRun.Status.POSTED


@pytest.mark.django_db
def test_rent_run_api_cancel_draft(auth_client, default_facility, test_party, test_commodity):
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

    payload = {
        "facility_id": default_facility.id,
        "period_start": "2026-07-01",
        "period_end": "2026-07-31"
    }

    res_create = auth_client.post('/api/rent-runs/', payload, format='json')
    assert res_create.status_code == status.HTTP_201_CREATED
    run_id = res_create.data['id']

    # Cancel DRAFT
    res_cancel = auth_client.post(f'/api/rent-runs/{run_id}/cancel/')
    assert res_cancel.status_code == status.HTTP_200_OK
    assert res_cancel.data['status'] == RentRun.Status.CANCELLED

