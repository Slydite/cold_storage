import pytest
from datetime import date, time
from decimal import Decimal
from rest_framework.test import APIClient

from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn, build_grn_pdf
from apps.inventory.models import GRN, Lot
from apps.inventory.serializers import GRNOutputSerializer
from apps.delivery.services import create_delivery_note, post_delivery_note, build_delivery_note_pdf
from apps.delivery.models import DeliveryNote, DeliveryLine
from apps.delivery.serializers import DeliveryNoteOutputSerializer
from apps.invoicing.services import build_invoice_pdf, generate_invoices_for_uninvoiced_deliveries, _amount_in_words


@pytest.fixture
def test_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Doc Test Farmer",
        type="DEPOSITOR",
        gstin="08ABCDE1234F1Z5"
    )


@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Doc Test Commodity",
        unit="BAGS"
    )



@pytest.mark.django_db
def test_generate_grn_pdf_service_and_serializer(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        bill_no="BILL-101",
        bilty_no="LR-505",
        transporter="Jaipur Freight",
        preservation_rate_per_bag_per_month=Decimal('12.00'),
        loading_unloading_rate_per_bag=Decimal('15.00'),
        inward_time=time(14, 30),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "special_remarks": "Floor 2 Chamber 4"
        }]
    )

    pdf_bytes = build_grn_pdf(grn_id=grn.id)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF')

    serializer = GRNOutputSerializer(grn)
    assert 'pdf_url' not in serializer.data
    assert serializer.data['bill_no'] == "BILL-101"
    assert serializer.data['bilty_no'] == "LR-505"
    assert serializer.data['transporter'] == "Jaipur Freight"
    assert serializer.data['lots'][0]['special_remarks'] == "Floor 2 Chamber 4"


@pytest.mark.django_db
def test_generate_delivery_note_pdf_and_balance_after(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    # Create DRAFT Delivery Note
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 10),
        transporter="National Express",
        status=DeliveryNote.Status.DRAFT,
        lines=[{
            "lot_id": lot.id,
            "qty": 30
        }]
    )
    line = dn.lines.first()

    # Draft line must have balance_after == None
    assert line.balance_after is None

    # Post DN -> stock is withdrawn (100 - 30 = 70)
    posted_dn = post_delivery_note(delivery_note_id=dn.id)
    line.refresh_from_db()
    lot.refresh_from_db()

    assert lot.remaining_qty == 70
    assert line.balance_after == 70

    # Build PDF
    pdf_bytes = build_delivery_note_pdf(delivery_note_id=posted_dn.id)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF')

    serializer = DeliveryNoteOutputSerializer(posted_dn)
    assert 'pdf_url' not in serializer.data
    assert serializer.data['transporter'] == "National Express"
    assert serializer.data['lines'][0]['balance_after'] == 70


@pytest.mark.django_db
def test_pdf_determinism(default_facility, test_party, test_commodity):
    """
    Assert that rendering the same record twice produces byte-identical output (same SHA256 / bytes).
    This is the core property on-the-fly streaming rests on.
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

    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 10),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 10}]
    )

    invoices = generate_invoices_for_uninvoiced_deliveries(
        facility_id=default_facility.id,
        party_id=test_party.id
    )
    invoice = invoices[0]

    # Test GRN PDF determinism
    grn_pdf1 = build_grn_pdf(grn_id=grn.id)
    grn_pdf2 = build_grn_pdf(grn_id=grn.id)
    assert grn_pdf1 == grn_pdf2

    # Test Delivery Note PDF determinism
    dn_pdf1 = build_delivery_note_pdf(delivery_note_id=dn.id)
    dn_pdf2 = build_delivery_note_pdf(delivery_note_id=dn.id)
    assert dn_pdf1 == dn_pdf2

    # Test Invoice PDF determinism
    inv_pdf1 = build_invoice_pdf(invoice_id=invoice.id)
    inv_pdf2 = build_invoice_pdf(invoice_id=invoice.id)
    assert inv_pdf1 == inv_pdf2


def test_amount_in_words():
    assert _amount_in_words(Decimal('5919.00')) == "Rupees Five Thousand Nine Hundred and Nineteen only"
    assert _amount_in_words(Decimal('145200.00')) == "Rupees One Lakh Forty Five Thousand Two Hundred only"
    assert _amount_in_words(Decimal('145200.50')) == "Rupees One Lakh Forty Five Thousand Two Hundred and Fifty Paise only"
    assert _amount_in_words(Decimal('0.00')) == "Rupees Zero only"
    assert _amount_in_words(Decimal('10000000.00')) == "Rupees One Crore only"


@pytest.mark.django_db
def test_grn_new_fields_roundtrip_api(admin_user, default_facility, test_party, test_commodity):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    payload = {
        "facility_id": default_facility.id,
        "party_id": test_party.id,
        "receipt_date": "2026-07-15",
        "vehicle_number": "RJ-14-AB-1234",
        "driver_name": "Ramesh",
        "remarks": "Manjil-2 Kaksh-4",
        "loading_charge": "1500.00",
        "bill_no": "BILL-202",
        "bilty_no": "LR-909",
        "transporter": "Jaipur Logistics",
        "preservation_rate_per_bag_per_month": "12.00",
        "loading_unloading_rate_per_bag": "15.00",
        "inward_time": "10:45:00",
        "status": "POSTED",
        "items": [
            {
                "commodity_id": test_commodity.id,
                "initial_qty": 100,
                "special_remarks": "Special Quality Peas"
            }
        ]
    }

    response = client.post("/api/grns/", payload, format="json")
    assert response.status_code == 217 or response.status_code == 201
    data = response.json()

    assert data["bill_no"] == "BILL-202"
    assert data["bilty_no"] == "LR-909"
    assert data["transporter"] == "Jaipur Logistics"
    assert data["preservation_rate_per_bag_per_month"] == "12.00"
    assert data["loading_unloading_rate_per_bag"] == "15.00"
    assert data["inward_time"] == "10:45:00"
    assert data["lots"][0]["special_remarks"] == "Special Quality Peas"


@pytest.mark.django_db
def test_delivery_note_new_fields_roundtrip_api(admin_user, default_facility, test_party, test_commodity):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        status=GRN.Status.POSTED,
        items=[{"commodity_id": test_commodity.id, "initial_qty": 50}]
    )
    lot = grn.lots.first()

    payload = {
        "facility_id": default_facility.id,
        "party_id": test_party.id,
        "dispatch_date": "2026-07-20",
        "vehicle_number": "RJ-14-CD-5678",
        "driver_name": "Suresh",
        "transporter": "Fast Cargo",
        "remarks": "Part delivery",
        "status": "DRAFT",
        "lines": [
            {
                "lot_id": lot.id,
                "qty": 20
            }
        ]
    }

    response = client.post("/api/delivery-notes/", payload, format="json")
    assert response.status_code == 201
    data = response.json()

    assert data["transporter"] == "Fast Cargo"
    assert data["lines"][0]["balance_after"] is None


@pytest.mark.django_db
def test_render_pdf_helper(default_facility):
    from libs.pdf import render_pdf
    pdf_bytes = render_pdf('pdf/base.html', {'facility': default_facility})
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF')


@pytest.mark.django_db
def test_grn_pdf_rendering_locations(default_facility, test_party, test_commodity):
    from apps.locations.services import create_chamber, create_floor, create_block

    chamber = create_chamber(facility_id=default_facility.id, name="Chamber 1")
    floor = create_floor(chamber_id=chamber.id, name="Floor 2")
    block = create_block(floor_id=floor.id, name="Block A")

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[
            {
                "commodity_id": test_commodity.id,
                "initial_qty": 100,
                "chamber_id": chamber.id,
                "floor_id": floor.id,
                "block_id": block.id
            },
            {
                "commodity_id": test_commodity.id,
                "initial_qty": 50
            }
        ]
    )

    pdf_bytes = build_grn_pdf(grn_id=grn.id)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF')
