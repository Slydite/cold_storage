import os
import csv
import pytest
from io import StringIO
from django.core.management import call_command
from apps.parties.models import Party
from apps.inventory.models import Commodity, GRN, Lot
from apps.locations.models import Chamber, Floor, Block
from apps.delivery.models import DeliveryNote, DeliveryLine

def write_csv(path, fieldnames, rows):
    with open(path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def setup_csv_files(tmp_path, parties=None, commodities=None, chambers=None, floors=None, blocks=None, grns=None, lots=None, delivery_notes=None, delivery_lines=None):
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
    write_csv(tmp_path / 'cleaned_lots.csv', ['lot_number', 'grn_number', 'commodity_code', 'chamber_ref_code', 'floor_ref_code', 'block_ref_code', 'initial_qty', 'remaining_qty', 'rent_rate_per_unit', 'unit', 'chamber', 'floor', 'rack', 'special_remarks', 'unit_weight', 'inward_date'], lots)
    write_csv(tmp_path / 'cleaned_delivery_notes.csv', ['dn_number', 'party_code', 'dispatch_date', 'vehicle_number', 'remarks', 'status'], delivery_notes)
    write_csv(tmp_path / 'cleaned_delivery_lines.csv', ['dn_number', 'lot_number', 'qty', 'balance_after'], delivery_lines)

@pytest.mark.django_db
def test_parties_only(tmp_path, default_facility):
    # Setup CSV files with master data and some documents
    setup_csv_files(
        tmp_path,
        grns=[{
            'grn_number': 'GRN01', 'party_code': 'P01', 'receipt_date': '2026-06-01',
            'vehicle_number': 'UP15-1234', 'remarks': 'Remarks', 'status': 'POSTED'
        }],
        lots=[{
            'lot_number': 'LOT01', 'grn_number': 'GRN01', 'commodity_code': 'C01',
            'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
            'initial_qty': '100', 'remaining_qty': '80', 'rent_rate_per_unit': '1.50',
            'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
            'unit_weight': '50.00', 'inward_date': '2026-06-01'
        }]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        parties_only=True,
        commit=True,
        stdout=out
    )

    # Check master data created
    assert Party.objects.filter(facility=default_facility, code='P01').exists()
    assert Commodity.objects.filter(facility=default_facility, code='C01').exists()
    assert Chamber.objects.filter(facility=default_facility, code='CH01').exists()
    assert Floor.objects.filter(chamber__facility=default_facility, code='FL01').exists()
    assert Block.objects.filter(floor__chamber__facility=default_facility, code='BK01').exists()

    # Check zero documents created
    assert GRN.objects.filter(facility=default_facility).count() == 0
    assert Lot.objects.filter(facility=default_facility).count() == 0
    assert DeliveryNote.objects.filter(facility=default_facility).count() == 0
    assert DeliveryLine.objects.filter(lot__facility=default_facility).count() == 0

    # Check output
    output = out.getvalue()
    assert "Mode: Parties Only" in output
    assert "Parties:" in output
    assert "Goods Receipt Notes (GRNs):" not in output

@pytest.mark.django_db
def test_financial_year_filtering(tmp_path, default_facility):
    # Setup CSV with documents in and out of financial year 2026-27 (2026-04-01 to 2027-03-31)
    setup_csv_files(
        tmp_path,
        grns=[
            {
                'grn_number': 'GRN01', 'party_code': 'P01', 'receipt_date': '2026-06-01',
                'vehicle_number': 'V1', 'remarks': '', 'status': 'POSTED'
            },
            {
                'grn_number': 'GRN02', 'party_code': 'P01', 'receipt_date': '2025-06-01',
                'vehicle_number': 'V2', 'remarks': '', 'status': 'POSTED'
            }
        ],
        lots=[
            {
                'lot_number': 'LOT01', 'grn_number': 'GRN01', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '80', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2026-06-01'
            },
            {
                'lot_number': 'LOT02', 'grn_number': 'GRN02', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '100', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2025-06-01'
            }
        ],
        delivery_notes=[
            {
                'dn_number': 'DN01', 'party_code': 'P01', 'dispatch_date': '2026-07-01',
                'vehicle_number': 'V3', 'remarks': '', 'status': 'POSTED'
            },
            {
                'dn_number': 'DN02', 'party_code': 'P01', 'dispatch_date': '2025-07-01',
                'vehicle_number': 'V4', 'remarks': '', 'status': 'POSTED'
            }
        ],
        delivery_lines=[
            {
                'dn_number': 'DN01', 'lot_number': 'LOT01', 'qty': '20', 'balance_after': '80'
            },
            {
                'dn_number': 'DN02', 'lot_number': 'LOT02', 'qty': '10', 'balance_after': '90'
            }
        ]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        commit=True,
        stdout=out
    )

    # GRN01 is inside 2026-27, GRN02 is not
    assert GRN.objects.filter(facility=default_facility, legacy_ref='GRN01').exists()
    assert not GRN.objects.filter(facility=default_facility, legacy_ref='GRN02').exists()

    # DN01 is inside 2026-27, DN02 is not
    assert DeliveryNote.objects.filter(facility=default_facility, legacy_ref='DN01').exists()
    assert not DeliveryNote.objects.filter(facility=default_facility, legacy_ref='DN02').exists()

    output = out.getvalue()
    assert "Mode: Financial Year (2026-27)" in output
    assert "Skipped (FY Filter): 1" in output

@pytest.mark.django_db
def test_delivery_line_skipped_no_lot(tmp_path, default_facility):
    # DN01 is in range (2026-07-01) but references LOT02 from GRN02 (2025-06-01), which is out of range.
    # Therefore, LOT02 is not imported.
    # DN01 also references LOT01 from GRN01 (2026-06-01), which is imported.
    # This means DN01 will have 1 imported line (LOT01) and 1 skipped line (LOT02).
    # Since DN01 has at least one resolved line, DN01 itself should be imported.
    setup_csv_files(
        tmp_path,
        grns=[
            {
                'grn_number': 'GRN01', 'party_code': 'P01', 'receipt_date': '2026-06-01',
                'vehicle_number': 'V1', 'remarks': '', 'status': 'POSTED'
            },
            {
                'grn_number': 'GRN02', 'party_code': 'P01', 'receipt_date': '2025-06-01',
                'vehicle_number': 'V2', 'remarks': '', 'status': 'POSTED'
            }
        ],
        lots=[
            {
                'lot_number': 'LOT01', 'grn_number': 'GRN01', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '80', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2026-06-01'
            },
            {
                'lot_number': 'LOT02', 'grn_number': 'GRN02', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '100', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2025-06-01'
            }
        ],
        delivery_notes=[
            {
                'dn_number': 'DN01', 'party_code': 'P01', 'dispatch_date': '2026-07-01',
                'vehicle_number': 'V3', 'remarks': '', 'status': 'POSTED'
            }
        ],
        delivery_lines=[
            {
                'dn_number': 'DN01', 'lot_number': 'LOT01', 'qty': '20', 'balance_after': '80'
            },
            {
                'dn_number': 'DN01', 'lot_number': 'LOT02', 'qty': '10', 'balance_after': '90'
            }
        ]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        commit=True,
        stdout=out
    )

    # DN01 exists
    dn = DeliveryNote.objects.get(facility=default_facility, legacy_ref='DN01')
    # Only LOT01 line is imported
    assert dn.lines.count() == 1
    assert dn.lines.first().lot.legacy_ref == 'LOT01'

    # Check output metrics
    output = out.getvalue()
    assert "Skipped (No Lot)   : 1" in output
    assert "lot's GRN falls outside the imported financial year: 1" in output
    assert "Lot LOT02, GRN GRN02" in output

@pytest.mark.django_db
def test_delivery_note_skipped_entirely(tmp_path, default_facility):
    # DN01 is in range (2026-07-01) but only references LOT02 (from GRN02, which is out of range).
    # Since LOT02 is not imported, DN01 has 0 resolved lines.
    # Therefore, DN01 should be skipped entirely.
    setup_csv_files(
        tmp_path,
        grns=[
            {
                'grn_number': 'GRN02', 'party_code': 'P01', 'receipt_date': '2025-06-01',
                'vehicle_number': 'V2', 'remarks': '', 'status': 'POSTED'
            }
        ],
        lots=[
            {
                'lot_number': 'LOT02', 'grn_number': 'GRN02', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '100', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2025-06-01'
            }
        ],
        delivery_notes=[
            {
                'dn_number': 'DN01', 'party_code': 'P01', 'dispatch_date': '2026-07-01',
                'vehicle_number': 'V3', 'remarks': '', 'status': 'POSTED'
            }
        ],
        delivery_lines=[
            {
                'dn_number': 'DN01', 'lot_number': 'LOT02', 'qty': '10', 'balance_after': '90'
            }
        ]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        commit=True,
        stdout=out
    )

    assert not DeliveryNote.objects.filter(facility=default_facility, legacy_ref='DN01').exists()

    output = out.getvalue()
    assert "Skipped (Empty)    : 1" in output

@pytest.mark.django_db
def test_financial_year_conflict(tmp_path, default_facility):
    setup_csv_files(tmp_path)
    err = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        full_history=True,
        stderr=err
    )
    assert "Cannot combine --financial-year with --full-history." in err.getvalue()

@pytest.mark.django_db
def test_invalid_financial_year(tmp_path, default_facility):
    setup_csv_files(tmp_path)
    err = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='invalid-fy',
        stderr=err
    )
    assert "Invalid financial year label" in err.getvalue()

@pytest.mark.django_db
def test_import_idempotency(tmp_path, default_facility):
    setup_csv_files(
        tmp_path,
        grns=[{
            'grn_number': 'GRN01', 'party_code': 'P01', 'receipt_date': '2026-06-01',
            'vehicle_number': 'V1', 'remarks': '', 'status': 'POSTED'
        }],
        lots=[{
            'lot_number': 'LOT01', 'grn_number': 'GRN01', 'commodity_code': 'C01',
            'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
            'initial_qty': '100', 'remaining_qty': '80', 'rent_rate_per_unit': '1.50',
            'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
            'unit_weight': '50.00', 'inward_date': '2026-06-01'
        }]
    )

    out1 = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        commit=True,
        stdout=out1
    )
    assert GRN.objects.filter(facility=default_facility, legacy_ref='GRN01').exists()
    assert Lot.objects.filter(facility=default_facility, legacy_ref='LOT01').exists()

    # Second run
    out2 = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        commit=True,
        stdout=out2
    )

    # Count shouldn't double
    assert GRN.objects.filter(facility=default_facility).count() == 1
    assert Lot.objects.filter(facility=default_facility).count() == 1

    output2 = out2.getvalue()
    assert "Skipped            : 1" in output2

@pytest.mark.django_db
def test_dry_run_leaves_db_unchanged(tmp_path, default_facility):
    setup_csv_files(
        tmp_path,
        grns=[{
            'grn_number': 'GRN01', 'party_code': 'P01', 'receipt_date': '2026-06-01',
            'vehicle_number': 'V1', 'remarks': '', 'status': 'POSTED'
        }],
        lots=[{
            'lot_number': 'LOT01', 'grn_number': 'GRN01', 'commodity_code': 'C01',
            'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
            'initial_qty': '100', 'remaining_qty': '80', 'rent_rate_per_unit': '1.50',
            'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
            'unit_weight': '50.00', 'inward_date': '2026-06-01'
        }]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        commit=False, # Dry run
        stdout=out
    )

    # Nothing should be in DB because dry run rolls back
    assert GRN.objects.filter(facility=default_facility).count() == 0
    assert Lot.objects.filter(facility=default_facility).count() == 0
    assert Party.objects.filter(facility=default_facility).count() == 0

    assert "DRY RUN - ROLLED BACK" in out.getvalue()


@pytest.mark.django_db
def test_include_referenced_lots_import(tmp_path, default_facility):
    # Setup:
    # GRN01 is inside FY (2026-06-01), LOT01
    # GRN02 is outside FY (2025-06-01), LOT02 and LOT03
    # DN01 is inside FY (2026-07-01), delivery line refers to LOT02
    setup_csv_files(
        tmp_path,
        grns=[
            {
                'grn_number': 'GRN01', 'party_code': 'P01', 'receipt_date': '2026-06-01',
                'vehicle_number': 'V1', 'remarks': '', 'status': 'POSTED'
            },
            {
                'grn_number': 'GRN02', 'party_code': 'P01', 'receipt_date': '2025-06-01',
                'vehicle_number': 'V2', 'remarks': '', 'status': 'POSTED'
            }
        ],
        lots=[
            {
                'lot_number': 'LOT01', 'grn_number': 'GRN01', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '80', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2026-06-01'
            },
            {
                'lot_number': 'LOT02', 'grn_number': 'GRN02', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '90', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2025-06-01'
            },
            {
                'lot_number': 'LOT03', 'grn_number': 'GRN02', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '50', 'remaining_qty': '50', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2025-06-01'
            }
        ],
        delivery_notes=[
            {
                'dn_number': 'DN01', 'party_code': 'P01', 'dispatch_date': '2026-07-01',
                'vehicle_number': 'V3', 'remarks': '', 'status': 'POSTED'
            }
        ],
        delivery_lines=[
            {
                'dn_number': 'DN01', 'lot_number': 'LOT02', 'qty': '10', 'balance_after': '90'
            }
        ]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        include_referenced_lots=True,
        commit=True,
        stdout=out
    )

    # GRN02 (out of FY) and LOT02 and LOT03 should be imported because LOT02 is referenced by DN01 (in FY)
    assert GRN.objects.filter(facility=default_facility, legacy_ref='GRN01').exists()
    assert GRN.objects.filter(facility=default_facility, legacy_ref='GRN02').exists()
    assert Lot.objects.filter(facility=default_facility, legacy_ref='LOT01').exists()
    assert Lot.objects.filter(facility=default_facility, legacy_ref='LOT02').exists()
    assert Lot.objects.filter(facility=default_facility, legacy_ref='LOT03').exists()
    assert DeliveryNote.objects.filter(facility=default_facility, legacy_ref='DN01').exists()

    output = out.getvalue()
    assert "Supporting Records : 1 GRNs were pulled in as supporting records" in output
    assert "Include Referenced Lots: Enabled" in output


@pytest.mark.django_db
def test_without_include_referenced_lots_skips(tmp_path, default_facility):
    setup_csv_files(
        tmp_path,
        grns=[
            {
                'grn_number': 'GRN01', 'party_code': 'P01', 'receipt_date': '2026-06-01',
                'vehicle_number': 'V1', 'remarks': '', 'status': 'POSTED'
            },
            {
                'grn_number': 'GRN02', 'party_code': 'P01', 'receipt_date': '2025-06-01',
                'vehicle_number': 'V2', 'remarks': '', 'status': 'POSTED'
            }
        ],
        lots=[
            {
                'lot_number': 'LOT01', 'grn_number': 'GRN01', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '80', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2026-06-01'
            },
            {
                'lot_number': 'LOT02', 'grn_number': 'GRN02', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '90', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2025-06-01'
            }
        ],
        delivery_notes=[
            {
                'dn_number': 'DN01', 'party_code': 'P01', 'dispatch_date': '2026-07-01',
                'vehicle_number': 'V3', 'remarks': '', 'status': 'POSTED'
            }
        ],
        delivery_lines=[
            {
                'dn_number': 'DN01', 'lot_number': 'LOT02', 'qty': '10', 'balance_after': '90'
            }
        ]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        include_referenced_lots=False,
        commit=True,
        stdout=out
    )

    # GRN02 and LOT02 should NOT be imported, DN01 should be skipped because it has no resolved lines
    assert not GRN.objects.filter(facility=default_facility, legacy_ref='GRN02').exists()
    assert not Lot.objects.filter(facility=default_facility, legacy_ref='LOT02').exists()
    assert not DeliveryNote.objects.filter(facility=default_facility, legacy_ref='DN01').exists()

    output = out.getvalue()
    assert "Skipped (Empty)    : 1" in output
    assert "lot's GRN falls outside the imported financial year: 1" in output


@pytest.mark.django_db
def test_include_referenced_lots_without_financial_year_rejected(tmp_path, default_facility):
    setup_csv_files(tmp_path)
    err = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        include_referenced_lots=True,
        stderr=err
    )
    assert "Cannot use --include-referenced-lots without --financial-year." in err.getvalue()


@pytest.mark.django_db
def test_skipped_reason_grouping_by_category(tmp_path, default_facility):
    # Setup: 2 different lines reference 2 different out-of-year lots (GRN02 and GRN03)
    setup_csv_files(
        tmp_path,
        grns=[
            {
                'grn_number': 'GRN02', 'party_code': 'P01', 'receipt_date': '2025-06-01',
                'vehicle_number': 'V2', 'remarks': '', 'status': 'POSTED'
            },
            {
                'grn_number': 'GRN03', 'party_code': 'P01', 'receipt_date': '2025-07-01',
                'vehicle_number': 'V3', 'remarks': '', 'status': 'POSTED'
            }
        ],
        lots=[
            {
                'lot_number': 'LOT02', 'grn_number': 'GRN02', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '90', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2025-06-01'
            },
            {
                'lot_number': 'LOT03', 'grn_number': 'GRN03', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '90', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2025-07-01'
            }
        ],
        delivery_notes=[
            {
                'dn_number': 'DN01', 'party_code': 'P01', 'dispatch_date': '2026-07-01',
                'vehicle_number': 'V3', 'remarks': '', 'status': 'POSTED'
            }
        ],
        delivery_lines=[
            {
                'dn_number': 'DN01', 'lot_number': 'LOT02', 'qty': '10', 'balance_after': '90'
            },
            {
                'dn_number': 'DN01', 'lot_number': 'LOT03', 'qty': '10', 'balance_after': '90'
            }
        ]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        include_referenced_lots=False,
        commit=True,
        stdout=out
    )

    output = out.getvalue()
    # Check that it produces one category line with a count of 2, not two separate lines
    assert "lot's GRN falls outside the imported financial year: 2" in output
    assert "Lot LOT02, GRN GRN02" in output
    assert "Lot LOT03, GRN GRN03" in output


@pytest.mark.django_db
def test_include_referenced_lots_idempotency(tmp_path, default_facility):
    setup_csv_files(
        tmp_path,
        grns=[
            {
                'grn_number': 'GRN02', 'party_code': 'P01', 'receipt_date': '2025-06-01',
                'vehicle_number': 'V2', 'remarks': '', 'status': 'POSTED'
            }
        ],
        lots=[
            {
                'lot_number': 'LOT02', 'grn_number': 'GRN02', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '90', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2025-06-01'
            }
        ],
        delivery_notes=[
            {
                'dn_number': 'DN01', 'party_code': 'P01', 'dispatch_date': '2026-07-01',
                'vehicle_number': 'V3', 'remarks': '', 'status': 'POSTED'
            }
        ],
        delivery_lines=[
            {
                'dn_number': 'DN01', 'lot_number': 'LOT02', 'qty': '10', 'balance_after': '90'
            }
        ]
    )

    out1 = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        include_referenced_lots=True,
        commit=True,
        stdout=out1
    )
    assert GRN.objects.filter(facility=default_facility, legacy_ref='GRN02').count() == 1
    assert Lot.objects.filter(facility=default_facility, legacy_ref='LOT02').count() == 1

    out2 = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        financial_year='2026-27',
        include_referenced_lots=True,
        commit=True,
        stdout=out2
    )

    assert GRN.objects.filter(facility=default_facility, legacy_ref='GRN02').count() == 1
    assert Lot.objects.filter(facility=default_facility, legacy_ref='LOT02').count() == 1

    output2 = out2.getvalue()
    assert "Skipped            : 1" in output2


@pytest.mark.django_db
def test_import_legacy_no_location(tmp_path, default_facility):
    # Setup CSV files where lots have NO location details
    setup_csv_files(
        tmp_path,
        grns=[{
            'grn_number': 'GRN_NOLOC', 'party_code': 'P01', 'receipt_date': '2026-06-01',
            'vehicle_number': 'UP15-1234', 'remarks': 'No Location Test', 'status': 'POSTED'
        }],
        lots=[{
            'lot_number': 'LOT_NOLOC', 'grn_number': 'GRN_NOLOC', 'commodity_code': 'C01',
            'chamber_ref_code': '', 'floor_ref_code': '', 'block_ref_code': '',
            'initial_qty': '100', 'remaining_qty': '100', 'rent_rate_per_unit': '1.50',
            'unit': 'BAGS', 'chamber': '', 'floor': '', 'rack': '', 'special_remarks': '',
            'unit_weight': '50.00', 'inward_date': '2026-06-01'
        }]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        commit=True,
        stdout=out
    )

    # Check that the GRN and Lot were imported successfully despite having no location block
    grn = GRN.objects.get(facility=default_facility, legacy_ref='GRN_NOLOC')
    lot = Lot.objects.get(facility=default_facility, legacy_ref='LOT_NOLOC')
    assert lot.grn == grn
    assert lot.block_ref is None
    assert lot.floor_ref is None
    assert lot.chamber_ref is None


@pytest.mark.django_db
def test_zero_stock_before_import(tmp_path, default_facility):
    # Setup CSV files where:
    # LOT01 inward_date is 2021-12-31 (before 2022-01-01) -> should be zeroed
    # LOT02 inward_date is 2022-01-01 (on/after 2022-01-01) -> should NOT be zeroed
    setup_csv_files(
        tmp_path,
        grns=[
            {
                'grn_number': 'GRN01', 'party_code': 'P01', 'receipt_date': '2021-12-31',
                'vehicle_number': 'V1', 'remarks': '', 'status': 'POSTED'
            },
            {
                'grn_number': 'GRN02', 'party_code': 'P01', 'receipt_date': '2022-01-01',
                'vehicle_number': 'V2', 'remarks': '', 'status': 'POSTED'
            }
        ],
        lots=[
            {
                'lot_number': 'LOT01', 'grn_number': 'GRN01', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '80', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2021-12-31'
            },
            {
                'lot_number': 'LOT02', 'grn_number': 'GRN02', 'commodity_code': 'C01',
                'chamber_ref_code': 'CH01', 'floor_ref_code': 'FL01', 'block_ref_code': 'BK01',
                'initial_qty': '100', 'remaining_qty': '90', 'rent_rate_per_unit': '1.50',
                'unit': 'BAGS', 'chamber': '1', 'floor': '1', 'rack': 'A', 'special_remarks': '',
                'unit_weight': '50.00', 'inward_date': '2022-01-01'
            }
        ]
    )

    out = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        zero_stock_before='2022-01-01',
        commit=True,
        stdout=out
    )

    # LOT01 should be zeroed out
    lot1 = Lot.objects.get(facility=default_facility, legacy_ref='LOT01')
    assert lot1.remaining_qty == 0
    # There should be exactly 1 StockAdjustment for LOT01
    assert lot1.adjustments.count() == 1
    adj = lot1.adjustments.first()
    assert adj.qty_delta == -80
    assert adj.qty_before == 80
    assert adj.qty_after == 0
    assert adj.reason == 'MIGRATION_OPENING_BALANCE'

    # LOT02 should not be zeroed out
    lot2 = Lot.objects.get(facility=default_facility, legacy_ref='LOT02')
    assert lot2.remaining_qty == 90
    assert lot2.adjustments.count() == 0

    # Verify idempotency on second run
    out2 = StringIO()
    call_command(
        'import_legacy',
        facility=default_facility.id,
        source=str(tmp_path),
        zero_stock_before='2022-01-01',
        commit=True,
        stdout=out2
    )

    lot1.refresh_from_db()
    assert lot1.remaining_qty == 0
    assert lot1.adjustments.count() == 1  # No new adjustments created!


