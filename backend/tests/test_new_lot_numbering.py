import pytest
import csv
from datetime import date
from decimal import Decimal
import re
from django.core.exceptions import ValidationError
from apps.inventory.services import create_grn
from apps.inventory.models import Lot, Sequence, GRN
from apps.parties.models import Party
from apps.inventory.models import Commodity
from apps.facilities.models import Facility

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
    write_csv(tmp_path / 'cleaned_grns.csv', ['grn_number', 'party_code', 'receipt_date', 'vehicle_number', 'remarks', 'status'], grns)
    write_csv(tmp_path / 'cleaned_lots.csv', [
        'lot_number', 'grn_number', 'commodity_code', 'chamber_ref_code', 'floor_ref_code', 'block_ref_code',
        'initial_qty', 'remaining_qty', 'rent_rate_per_unit', 'unit', 'chamber', 'floor', 'rack',
        'special_remarks', 'unit_weight', 'inward_date', 'legacy_ref', 'lot_number_warning'
    ], lots)
    write_csv(tmp_path / 'cleaned_delivery_notes.csv', ['dn_number', 'party_code', 'dispatch_date', 'vehicle_number', 'remarks', 'status'], delivery_notes)
    write_csv(tmp_path / 'cleaned_delivery_lines.csv', ['dn_number', 'lot_number', 'qty', 'balance_after'], delivery_lines)

@pytest.mark.django_db
def test_create_grn_new_lot_number_format(default_facility, party, commodity):
    # Create GRN with item, no lot_number
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {
                "commodity_id": commodity.id,
                "initial_qty": 594,
                "rent_rate_per_unit": Decimal("10.00")
            }
        ],
        require_location=False
    )
    lot = grn.lots.first()
    assert lot is not None
    # format: YYYYMMDD-SSSSS-BBBBB
    # next value issued is 2607, continuing 2606
    assert lot.lot_number == "20260725-02607-00594"

@pytest.mark.django_db
def test_serial_counter_advances_same_day(default_facility, party, commodity):
    # Create two lots on the same day in same GRN
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {
                "commodity_id": commodity.id,
                "initial_qty": 594,
                "rent_rate_per_unit": Decimal("10.00")
            },
            {
                "commodity_id": commodity.id,
                "initial_qty": 594,
                "rent_rate_per_unit": Decimal("10.00")
            }
        ],
        require_location=False
    )
    lots = list(grn.lots.order_by('id'))
    assert len(lots) == 2
    assert lots[0].lot_number == "20260725-02607-00594"
    assert lots[1].lot_number == "20260725-02608-00594"

@pytest.mark.django_db
def test_counter_is_per_facility(default_facility, party, commodity, other_facility, other_party, other_commodity):
    # Issue a sequence for default_facility
    grn1 = create_grn(
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
    lot1 = grn1.lots.first()
    assert lot1.lot_number == "20260725-02607-00100"

    # Issue a sequence for other_facility - it should also seed at 2607!
    grn2 = create_grn(
        facility_id=other_facility.id,
        party_id=other_party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {
                "commodity_id": other_commodity.id,
                "initial_qty": 200,
                "rent_rate_per_unit": Decimal("10.00")
            }
        ],
        require_location=False
    )
    lot2 = grn2.lots.first()
    assert lot2.lot_number == "20260725-02607-00200"

@pytest.mark.django_db
def test_explicit_lot_number_validation(default_facility, party, commodity):
    # Valid explicit new format
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {
                "commodity_id": commodity.id,
                "initial_qty": 500,
                "lot_number": "20260725-01234-00500",
                "rent_rate_per_unit": Decimal("10.00")
            }
        ],
        require_location=False
    )
    assert grn.lots.first().lot_number == "20260725-01234-00500"

    # Explicit old format (LOT-000099) is now rejected when validated
    with pytest.raises(ValidationError):
        create_grn(
            facility_id=default_facility.id,
            party_id=party.id,
            receipt_date=date(2026, 7, 25),
            items=[
                {
                    "commodity_id": commodity.id,
                    "initial_qty": 500,
                    "lot_number": "LOT-000099",
                    "rent_rate_per_unit": Decimal("10.00")
                }
            ],
            require_location=False
        )

    # But accepted when validation is bypassed (as the importer does)
    grn2 = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {
                "commodity_id": commodity.id,
                "initial_qty": 500,
                "lot_number": "LOT-000099",
                "rent_rate_per_unit": Decimal("10.00")
            }
        ],
        require_location=False,
        validate_lot_number_format=False
    )
    assert grn2.lots.first().lot_number == "LOT-000099"

    # Bad format
    with pytest.raises(ValidationError):
        create_grn(
            facility_id=default_facility.id,
            party_id=party.id,
            receipt_date=date(2026, 7, 25),
            items=[
                {
                    "commodity_id": commodity.id,
                    "initial_qty": 500,
                    "lot_number": "BAD-FORMAT-123",
                    "rent_rate_per_unit": Decimal("10.00")
                }
            ],
            require_location=False
        )

@pytest.mark.django_db
def test_import_collision_disambiguates(default_facility, party, commodity, tmp_path):
    from django.core.management import call_command

    # Set up two colliding lots
    lots = [
        {
            'lot_number': '20260725-02606-00594', 'grn_number': 'GRN01', 'commodity_code': 'C01',
            'chamber_ref_code': '', 'floor_ref_code': '', 'block_ref_code': '',
            'initial_qty': '594', 'remaining_qty': '594', 'rent_rate_per_unit': '10.00',
            'unit': 'BAGS', 'chamber': '', 'floor': '', 'rack': '', 'special_remarks': '',
            'unit_weight': '50.00', 'inward_date': '2026-07-25', 'legacy_ref': '2606/594'
        },
        {
            # Second lot with the exact same lot_number (colliding) but with -B suffix from ETL
            'lot_number': '20260725-02606-00594-B', 'grn_number': 'GRN02', 'commodity_code': 'C01',
            'chamber_ref_code': '', 'floor_ref_code': '', 'block_ref_code': '',
            'initial_qty': '594', 'remaining_qty': '594', 'rent_rate_per_unit': '10.00',
            'unit': 'BAGS', 'chamber': '', 'floor': '', 'rack': '', 'special_remarks': '',
            'unit_weight': '50.00', 'inward_date': '2026-07-25', 'legacy_ref': '2606/594'
        }
    ]
    grns = [
        {'grn_number': 'GRN01', 'party_code': 'P01', 'receipt_date': '2026-07-25', 'vehicle_number': '', 'remarks': '', 'status': 'POSTED'},
        {'grn_number': 'GRN02', 'party_code': 'P01', 'receipt_date': '2026-07-25', 'vehicle_number': '', 'remarks': '', 'status': 'POSTED'}
    ]

    setup_csv_files_local(tmp_path, grns=grns, lots=lots)

    # Run importer - it should import both and not raise unique constraint errors
    call_command('import_legacy', source=str(tmp_path), facility=default_facility.id, commit=True)

    # Both lots should exist
    assert Lot.objects.filter(facility=default_facility, lot_number='20260725-02606-00594').exists()
    assert Lot.objects.filter(facility=default_facility, lot_number='20260725-02606-00594-B').exists()

@pytest.mark.django_db
def test_searching_lot_by_raw_fas_string(default_facility, party, commodity):
    # Create a lot with a legacy_ref
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {
                "commodity_id": commodity.id,
                "initial_qty": 594,
                "rent_rate_per_unit": Decimal("10.00"),
                "lot_number": "20260725-02606-00594"
            }
        ],
        require_location=False
    )
    lot = grn.lots.first()
    lot.legacy_ref = "2606/594"
    lot.save()

    # Search using Django ORM by legacy_ref
    found = Lot.objects.filter(facility=default_facility, legacy_ref="2606/594")
    assert found.exists()
    assert found.first().id == lot.id

def test_build_lot_number_formats_and_pads():
    """The shared helper is the single implementation - exercise it, not a copy."""
    from libs.lot_numbers import build_lot_number, is_valid_lot_number

    number, warning = build_lot_number(
        receipt_date=date(2026, 7, 25), serial=2606, bags=594
    )
    assert number == "20260725-02606-00594"
    assert warning == ""
    assert is_valid_lot_number(number)


def test_build_lot_number_clamps_oversized_serial_rather_than_truncating():
    """
    222265 truncated to 22226 would be a plausible-looking wrong number that
    nothing would ever catch. It must be pinned to the maximum and reported.
    """
    from libs.lot_numbers import build_lot_number, is_valid_lot_number

    number, warning = build_lot_number(
        receipt_date=date(2025, 2, 7), serial=222265, bags=288
    )
    assert number == "20250207-99999-00288"
    assert "222265" in warning
    # The guard exists so the result still satisfies the format's own rules;
    # an unclamped serial would widen the field and fail this.
    assert is_valid_lot_number(number)

    number, warning = build_lot_number(
        receipt_date=date(2020, 4, 24), serial=17108650, bags=650
    )
    assert number == "20200424-99999-00650"
    assert "17108650" in warning
    assert is_valid_lot_number(number)


def test_build_lot_number_clamps_oversized_quantity():
    from libs.lot_numbers import build_lot_number, is_valid_lot_number

    number, warning = build_lot_number(
        receipt_date=date(2026, 7, 25), serial=10, bags=1234567
    )
    assert number == "20260725-00010-99999"
    assert "1234567" in warning
    assert is_valid_lot_number(number)


def test_generated_lot_numbers_always_satisfy_their_own_validation():
    """
    create_grn validates a supplied lot number against the same rule it uses to
    generate one. Any input that produced a number failing that check would be
    a number the app could create but not accept.
    """
    from libs.lot_numbers import build_lot_number, is_valid_lot_number

    for serial, bags in [(0, 0), (1, 1), (99999, 99999), (100000, 100000), (-5, -5)]:
        number, _ = build_lot_number(
            receipt_date=date(2026, 1, 1), serial=serial, bags=bags
        )
        assert is_valid_lot_number(number), f"{number} fails its own validation"


@pytest.mark.django_db
def test_data_migration_renames_legacy_lot_and_leaves_new_ones(default_facility, party, commodity):
    import importlib
    migration_mod = importlib.import_module("apps.inventory.migrations.0022_auto_20260807_1926")
    rename_legacy_lots = migration_mod.rename_legacy_lots
    reverse_rename_legacy_lots = migration_mod.reverse_rename_legacy_lots
    from django.apps import apps as django_apps
    
    # Create a legacy-pattern lot (validate_lot_number_format=False)
    grn_legacy = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        items=[
            {
                "commodity_id": commodity.id,
                "initial_qty": 100,
                "lot_number": "LOT-000001",
                "rent_rate_per_unit": Decimal("10.00")
            }
        ],
        require_location=False,
        validate_lot_number_format=False
    )
    lot_legacy = grn_legacy.lots.first()
    assert lot_legacy.lot_number == "LOT-000001"

    # Create a new-format lot
    grn_new = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        items=[
            {
                "commodity_id": commodity.id,
                "initial_qty": 200,
                "lot_number": "20260807-02606-00200",
                "rent_rate_per_unit": Decimal("10.00")
            }
        ],
        require_location=False
    )
    lot_new = grn_new.lots.first()
    assert lot_new.lot_number == "20260807-02606-00200"

    # Run the migration
    rename_legacy_lots(django_apps, None)

    # Reload from db
    lot_legacy.refresh_from_db()
    lot_new.refresh_from_db()

    # Legacy lot should have been renamed
    # Sequence current_val starts at 2606 by default defaults, so incremented value should be 2607
    assert lot_legacy.lot_number == "20260807-02607-00100"

    # New lot should remain untouched
    assert lot_new.lot_number == "20260807-02606-00200"

    # Reverse migration raises IrreversibleMigration
    with pytest.raises(Exception):
        reverse_rename_legacy_lots(django_apps, None)
