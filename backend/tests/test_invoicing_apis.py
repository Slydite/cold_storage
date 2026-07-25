import pytest
from rest_framework import status
from datetime import date
from decimal import Decimal
from django.urls import path, include
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.billing.services import create_rate_card, create_rent_run, post_rent_run
from apps.billing.models import RateCard
from apps.invoicing.models import Invoice

urlpatterns = [
    path('api/', include('apps.invoicing.urls')),
]

pytestmark = pytest.mark.urls('tests.test_invoicing_apis')


@pytest.fixture
def test_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Invoice API Customer",
        code="CUST-INV-01",
        type="DEPOSITOR",
        gstin="27ABCDE1234F1Z5"
    )


@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Sweet Corn",
        code="CORN-01",
        unit="BAGS"
    )


@pytest.mark.django_db
def test_unauthenticated_invoicing_apis_denied(api_client):
    assert api_client.get('/api/invoices/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.post('/api/invoices/', {}).status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_invoice_api_generate_list_retrieve_post_cancel_pdf(auth_client, default_facility, test_party, test_commodity, tmp_path, settings):
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

    payload = {
        "facility_id": default_facility.id,
        "rent_run_id": rent_run.id
    }

    # Generate invoices
    res = auth_client.post('/api/invoices/', payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    assert len(res.data) == 1
    inv_data = res.data[0]
    inv_id = inv_data['id']
    assert inv_data['status'] == Invoice.Status.DRAFT
    assert inv_data['subtotal'] == "5000.00"
    assert inv_data['gst_amount'] == "900.00"
    assert inv_data['total_amount'] == "5900.00"
    assert inv_data['pdf_url'] is None

    # List Invoices
    res_list = auth_client.get(f'/api/invoices/?facility_id={default_facility.id}')
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1

    # Retrieve Invoice
    res_get = auth_client.get(f'/api/invoices/{inv_id}/')
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.data['id'] == inv_id

    # Generate PDF via API
    res_pdf = auth_client.post(f'/api/invoices/{inv_id}/generate-pdf/')
    assert res_pdf.status_code == status.HTTP_200_OK
    assert res_pdf.data['pdf_url'] is not None

    # Post Invoice via API
    res_post = auth_client.post(f'/api/invoices/{inv_id}/post/')
    assert res_post.status_code == status.HTTP_200_OK
    assert res_post.data['status'] == Invoice.Status.POSTED
