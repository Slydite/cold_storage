import pytest
from rest_framework import status
from datetime import date
from decimal import Decimal
from django.urls import path, include
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.inventory.models import GRN
from apps.delivery.services import create_delivery_note
from apps.delivery.models import DeliveryNote
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
        type="DEPOSITOR",
        gstin="27ABCDE1234F1Z5"
    )


@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Sweet Corn",
        unit="BAGS"
    )



@pytest.mark.django_db
def test_unauthenticated_invoicing_apis_denied(api_client):
    assert api_client.get('/api/invoices/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/invoices/preview/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.post('/api/invoices/', {}).status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/invoices/1/pdf/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.get('/api/invoices/1/payments/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.post('/api/invoices/1/payments/', {}).status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.delete('/api/invoices/1/payments/1/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_invoice_api_generate_list_retrieve_post_cancel_pdf(auth_client, default_facility, test_party, test_commodity):
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

    payload = {
        "facility_id": default_facility.id,
        "party_id": test_party.id
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
    assert inv_data['payment_status'] == "UNPAID"
    assert inv_data['amount_paid'] == "0.00"
    assert inv_data['amount_due'] == "5900.00"
    assert 'pdf_url' not in inv_data

    # List Invoices
    res_list = auth_client.get(f'/api/invoices/?facility_id={default_facility.id}')
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1

    # Retrieve Invoice
    res_get = auth_client.get(f'/api/invoices/{inv_id}/')
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.data['id'] == inv_id

    # Stream PDF via GET API
    res_pdf = auth_client.get(f'/api/invoices/{inv_id}/pdf/')
    assert res_pdf.status_code == status.HTTP_200_OK
    assert res_pdf['Content-Type'] == 'application/pdf'
    assert inv_data['invoice_number'] in res_pdf['Content-Disposition']
    assert res_pdf.content.startswith(b'%PDF')

    # Post Invoice via API
    res_post = auth_client.post(f'/api/invoices/{inv_id}/post/')
    assert res_post.status_code == status.HTTP_200_OK
    assert res_post.data['status'] == Invoice.Status.POSTED


@pytest.mark.django_db
def test_payment_api_workflow_and_filtering(auth_client, default_facility, test_party):
    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-API-PAY-001",
        party=test_party,
        invoice_date=date(2026, 7, 1),
        total_amount=Decimal('1000.00')
    )

    # 1. Record payment via API
    pay_payload1 = {
        "amount": "400.00",
        "payment_date": "2026-07-27",
        "method": "CASH",
        "reference": "REC-01",
        "notes": "Partial cash payment"
    }
    res_pay1 = auth_client.post(f'/api/invoices/{inv.id}/payments/', pay_payload1, format='json')
    assert res_pay1.status_code == status.HTTP_200_OK
    assert res_pay1.data['payment_status'] == "PARTIAL"
    assert res_pay1.data['amount_paid'] == "400.00"
    assert res_pay1.data['amount_due'] == "600.00"
    assert len(res_pay1.data['payments']) == 1
    p1_id = res_pay1.data['payments'][0]['id']

    # 2. List payments for invoice via GET API
    res_pay_list = auth_client.get(f'/api/invoices/{inv.id}/payments/')
    assert res_pay_list.status_code == status.HTTP_200_OK
    assert len(res_pay_list.data) == 1
    assert res_pay_list.data[0]['amount'] == "400.00"
    assert res_pay_list.data[0]['method_display'] == "Cash"

    # 3. Filter invoices list by payment_status
    res_filter_partial = auth_client.get(f'/api/invoices/?facility_id={default_facility.id}&payment_status=PARTIAL')
    assert res_filter_partial.status_code == status.HTTP_200_OK
    assert len(res_filter_partial.data) == 1

    res_filter_paid = auth_client.get(f'/api/invoices/?facility_id={default_facility.id}&payment_status=PAID')
    assert res_filter_paid.status_code == status.HTTP_200_OK
    assert len(res_filter_paid.data) == 0

    # 4. Record second payment to reach PAID
    pay_payload2 = {
        "amount": "600.00",
        "payment_date": "2026-07-28",
        "method": "BANK_TRANSFER",
        "reference": "UTR9999"
    }
    res_pay2 = auth_client.post(f'/api/invoices/{inv.id}/payments/', pay_payload2, format='json')
    assert res_pay2.status_code == status.HTTP_200_OK
    assert res_pay2.data['payment_status'] == "PAID"
    assert res_pay2.data['amount_paid'] == "1000.00"
    assert res_pay2.data['amount_due'] == "0.00"
    assert len(res_pay2.data['payments']) == 2
    p2_id = res_pay2.data['payments'][0]['id']  # ordered -payment_date

    # 5. Delete a payment via DELETE API
    res_del = auth_client.delete(f'/api/invoices/{inv.id}/payments/{p2_id}/')
    assert res_del.status_code == status.HTTP_200_OK
    assert res_del.data['payment_status'] == "PARTIAL"
    assert res_del.data['amount_paid'] == "400.00"
    assert res_del.data['amount_due'] == "600.00"
    assert len(res_del.data['payments']) == 1


@pytest.mark.django_db
def test_invoice_preview_api_endpoint(auth_client, default_facility, test_party, test_commodity):
    """
    Test GET /api/invoices/preview/?facility_id=<int>&party_id=<int optional>
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

    # Missing facility_id -> 400 Bad Request
    res_missing = auth_client.get('/api/invoices/preview/')
    assert res_missing.status_code == status.HTTP_400_BAD_REQUEST
    assert "facility_id" in res_missing.data

    # Valid preview request
    res = auth_client.get(f'/api/invoices/preview/?facility_id={default_facility.id}&party_id={test_party.id}')
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) == 1

    entry = res.data[0]
    assert entry['party_id'] == test_party.id
    assert entry['party_name'] == test_party.name
    assert entry['party_code'] == test_party.code
    assert entry['subtotal'] == "5150.00"
    assert entry['gst_rate'] == "18.00"
    assert entry['gst_amount'] == "927.00"
    assert entry['total_amount'] == "6077.00"
    assert len(entry['lines']) == 3

    rent_line = entry['lines'][0]
    assert rent_line['lot_number'] == lot.lot_number
    assert rent_line['commodity_name'] == test_commodity.name
    assert rent_line['qty'] == 100
    assert rent_line['inward_date'] == "2026-07-01"
    assert rent_line['dispatch_date'] == "2026-07-31"
    assert rent_line['days_stored'] == 30


@pytest.mark.django_db
def test_invoice_email_api_workflow(auth_client, default_facility, test_party):
    # Unauthenticated access is covered separately by
    # test_invoice_email_action_genuinely_unauthenticated: requesting both
    # auth_client and api_client in one test resolves to the SAME already-
    # authenticated instance (auth_client's own fixture depends on api_client),
    # so an "unauthenticated" assertion here would silently pass for the
    # wrong reason.
    from django.core import mail
    from apps.parties.models import Party

    inv = Invoice.objects.create(
        facility=default_facility,
        invoice_number="INV-EMAIL-001",
        party=test_party,
        invoice_date=date(2026, 7, 1),
        total_amount=Decimal('1000.00')
    )

    # 1. Party has blank email by default -> 400, does not send
    mail.outbox.clear()
    res_blank = auth_client.post(f'/api/invoices/{inv.id}/email/')
    assert res_blank.status_code == status.HTTP_400_BAD_REQUEST
    assert "does not have an email address on file" in res_blank.data['detail']
    assert len(mail.outbox) == 0

    # 3. Update party to have email
    p_obj = Party.objects.get(pk=test_party.id)
    p_obj.email = "invoice_client@example.com"
    p_obj.save()

    # 4. Email invoice -> 200, sends mail, updates last_emailed_at
    mail.outbox.clear()
    res_success = auth_client.post(f'/api/invoices/{inv.id}/email/')
    assert res_success.status_code == status.HTTP_200_OK
    assert res_success.data['last_emailed_at'] is not None

    # Check email sent
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["invoice_client@example.com"]
    assert "Invoice" in msg.subject
    assert len(msg.attachments) == 1
    filename, content, mimetype = msg.attachments[0]
    assert filename.endswith('.pdf')
    assert mimetype == 'application/pdf'
    assert content.startswith(b'%PDF')





@pytest.mark.django_db
def test_invoice_email_action_genuinely_unauthenticated():
    """
    Isolated from test_invoice_email_api_workflow deliberately: that test
    requests both auth_client and api_client fixtures in one function, and
    since auth_client's own fixture dependency resolves api_client first,
    pytest caches and hands back the SAME already-authenticated instance to
    both parameters within one test call. So its "unauthenticated" assertion
    was silently exercising an authenticated client.
    """
    from rest_framework.test import APIClient
    fresh_client = APIClient()
    res = fresh_client.post('/api/invoices/1/email/')
    assert res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
