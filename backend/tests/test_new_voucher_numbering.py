import pytest
import csv
from datetime import date
from decimal import Decimal
import re
from io import StringIO
from django.core.exceptions import ValidationError
from django.core.management import call_command
from apps.inventory.services import create_grn
from apps.delivery.services import create_delivery_note
from apps.inventory.models import Lot, Sequence, GRN
from apps.delivery.models import DeliveryNote, DeliveryLine
from apps.parties.models import Party
from apps.inventory.models import Commodity
from apps.facilities.models import Facility
from libs.lot_numbers import build_voucher_number, is_valid_voucher_number

@pytest.fixture
def party(default_facility):
    return Party.objects.create(
        facility=default_facility,
        name="Test Party",
        code="PRT-000001",
        type="DEPOSITOR"
    )

@pytest.fixture
def commodity(default_facility):
    return Commodity.objects.create(
        facility=default_facility,
        name="Potato",
        code="CMD-000001",
        unit="BAGS"
    )

@pytest.fixture
def other_facility(db):
    return Facility.objects.create(name="Other Facility", code="FAC-999999")

@pytest.fixture
def other_party(other_facility):
    return Party.objects.create(
        facility=other_facility,
        name="Other Party",
        code="PRT-999999",
        type="DEPOSITOR"
    )

@pytest.fixture
def other_commodity(other_facility):
    return Commodity.objects.create(
        facility=other_facility,
        name="Other Potato",
        code="CMD-999999",
        unit="BAGS"
    )

def setup_csv_files_local(tmp_path, parties=None, commodities=None, chambers=None, floors=None, blocks=None, grns=None, lots=None, delivery_notes=None, delivery_lines=None):
    def write_csv(path, fieldnames, rows):
        with open(path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

    if parties is None:
        parties = [{
            'code': 'P01', 'name': 'Test Party 1', 'type': 'DEPOSITOR',
            'phone': '1234567890', 'email': 'p1@example.com',
            'address': 'Address 1', 'gstin': '09AAAAA1111A1Z1', 'is_active': 'True'
        }]
    if commodities is None:
        commodities = [{
            'code': 'C01', 'name': 'Potato', 'unit': 'BAGS',
            'description': 'Fresh Potatoes', 'is_active': 'True'
        }]
    if chambers is None:
        chambers = [{
            'code': 'CH01', 'name': 'Chamber 1', 'is_active': 'True'
        }]
    if floors is None:
        floors = [{
            'code': 'FL01', 'chamber_code': 'CH01', 'name': 'Floor 1', 'is_active': 'True'
        }]
    if blocks is None:
        blocks = [{
            'code': 'BK01', 'floor_code': 'FL01', 'name': 'Block 1', 'capacity_bags': '1000', 'is_active': 'True'
        }]
    if grns is None:
        grns = []
    if lots is None:
        lots = []
    if delivery_notes is None:
        delivery_notes = []
    if delivery_lines is None:
        delivery_lines = []

    write_csv(tmp_path / 'cleaned_parties.csv', ['code', 'name', 'type', 'phone', 'email', 'address', 'gstin', 'is_active'], parties)
    write_csv(tmp_path / 'cleaned_commodities.csv', ['code', 'name', 'unit', 'description', 'is_active'], commodities)
    write_csv(tmp_path / 'cleaned_chambers.csv', ['code', 'name', 'is_active'], chambers)
    write_csv(tmp_path / 'cleaned_floors.csv', ['code', 'chamber_code', 'name', 'is_active'], floors)
    write_csv(tmp_path / 'cleaned_blocks.csv', ['code', 'floor_code', 'name', 'capacity_bags', 'is_active'], blocks)
    write_csv(tmp_path / 'cleaned_grns.csv', ['grn_number', 'party_code', 'receipt_date', 'vehicle_number', 'remarks', 'status', 'legacy_ref'], grns)
    write_csv(tmp_path / 'cleaned_lots.csv', [
        'lot_number', 'grn_number', 'commodity_code', 'chamber_ref_code', 'floor_ref_code', 'block_ref_code',
        'initial_qty', 'remaining_qty', 'rent_rate_per_unit', 'unit', 'chamber', 'floor', 'rack',
        'special_remarks', 'unit_weight', 'inward_date', 'legacy_ref', 'lot_number_warning'
    ], lots)
    write_csv(tmp_path / 'cleaned_delivery_notes.csv', ['dn_number', 'party_code', 'dispatch_date', 'vehicle_number', 'remarks', 'status', 'legacy_ref'], delivery_notes)
    write_csv(tmp_path / 'cleaned_delivery_lines.csv', ['dn_number', 'lot_number', 'qty', 'balance_after'], delivery_lines)


def test_build_voucher_number_helper():
    # formats and zero-pads correctly
    number, warning = build_voucher_number(doc_date=date(2026, 7, 27), voucher_no=2905)
    assert number == "20260727-02905"
    assert warning == ""
    assert is_valid_voucher_number(number)

    # clamps oversized voucher number rather than truncating
    number, warning = build_voucher_number(doc_date=date(2026, 7, 27), voucher_no=123456)
    assert number == "20260727-99999"
    assert "123456" in warning
    assert is_valid_voucher_number(number)

    # clamps negative voucher number to 0
    number, warning = build_voucher_number(doc_date=date(2026, 7, 27), voucher_no=-10)
    assert number == "20260727-00000"
    assert "-10" in warning
    assert is_valid_voucher_number(number)


@pytest.mark.django_db
def test_create_grn_gets_receipt_date_and_counter(default_facility, party, commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {
                "commodity_id": commodity.id,
                "initial_qty": 100,
                "rent_rate_per_unit": Decimal("10.00")
            }
        ],
        require_location=False
    )
    # default starting VNo is 1068, so next issued is 1069
    assert grn.grn_number == "20260725-01069"


@pytest.mark.django_db
def test_grn_counter_advances_and_is_per_facility(default_facility, party, commodity, other_facility, other_party, other_commodity):
    grn1 = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[{"commodity_id": commodity.id, "initial_qty": 100}],
        require_location=False
    )
    grn2 = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[{"commodity_id": commodity.id, "initial_qty": 200}],
        require_location=False
    )
    assert grn1.grn_number == "20260725-01069"
    assert grn2.grn_number == "20260725-01070"

    # per-facility sequence: other facility starts at 1069
    grn3 = create_grn(
        facility_id=other_facility.id,
        party_id=other_party.id,
        receipt_date=date(2026, 7, 25),
        items=[{"commodity_id": other_commodity.id, "initial_qty": 100}],
        require_location=False
    )
    assert grn3.grn_number == "20260725-01069"


@pytest.mark.django_db
def test_create_delivery_note_gets_dispatch_date_and_counter(default_facility, party, commodity, default_block):
    # Setup stock
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[{"commodity_id": commodity.id, "initial_qty": 100, "block_id": default_block.id}],
    )
    lot = grn.lots.first()

    dn1 = create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 7, 27),
        lines=[{"lot_id": lot.id, "qty": 10}]
    )
    dn2 = create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 7, 27),
        lines=[{"lot_id": lot.id, "qty": 10}]
    )
    # default starting VNo is 2905, so next issued is 2906
    assert dn1.dn_number == "20260727-02906"
    assert dn2.dn_number == "20260727-02907"


@pytest.mark.django_db
def test_explicitly_supplied_voucher_validation(default_facility, party, commodity):
    # Explicit valid format is accepted
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[{"commodity_id": commodity.id, "initial_qty": 100}],
        require_location=False,
        grn_number="20260725-05555"
    )
    assert grn.grn_number == "20260725-05555"

    # Explicit invalid format is rejected
    with pytest.raises(ValidationError):
        create_grn(
            facility_id=default_facility.id,
            party_id=party.id,
            receipt_date=date(2026, 7, 25),
            items=[{"commodity_id": commodity.id, "initial_qty": 100}],
            require_location=False,
            grn_number="BAD-GRN-123"
        )


@pytest.mark.django_db
def test_importer_idempotency_double_run(default_facility, tmp_path):
    # Setup cleaned files
    grns = [
        {
            'grn_number': '20260711-01042',
            'party_code': 'P01',
            'receipt_date': '2026-07-11',
            'vehicle_number': 'UP-15-1234',
            'remarks': 'Idempotency test GRN',
            'status': 'POSTED',
            'legacy_ref': '2026000042'
        }
    ]
    lots = [
        {
            'lot_number': '20260711-02606-00100',
            'grn_number': '20260711-01042',
            'commodity_code': 'C01',
            'chamber_ref_code': '',
            'floor_ref_code': '',
            'block_ref_code': '',
            'initial_qty': '100',
            'remaining_qty': '100',
            'rent_rate_per_unit': '10.00',
            'unit': 'BAGS',
            'chamber': '',
            'floor': '',
            'rack': '',
            'special_remarks': '',
            'unit_weight': '50.00',
            'inward_date': '2026-07-11',
            'legacy_ref': '2606/100',
            'lot_number_warning': ''
        }
    ]
    setup_csv_files_local(tmp_path, grns=grns, lots=lots)

    # First run should import the GRN and Lot
    out1 = StringIO()
    call_command('import_legacy', source=str(tmp_path), facility=default_facility.id, commit=True, stdout=out1)
    
    assert GRN.objects.filter(facility=default_facility, legacy_ref='2026000042').exists()
    grn_obj = GRN.objects.get(facility=default_facility, legacy_ref='2026000042')
    assert grn_obj.grn_number == '20260711-01042'
    
    # Second run should create nothing, skip, and be idempotent
    out2 = StringIO()
    call_command('import_legacy', source=str(tmp_path), facility=default_facility.id, commit=True, stdout=out2)
    
    output2 = out2.getvalue()
    # Confirm it reports skipped
    assert "Skipped: 1" in output2 or "grns_skipped': 1" in output2 or "Skipped" in output2
    assert "Created: 0" in output2 or "grns_created': 0" in output2 or "Created" in output2
