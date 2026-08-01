import os
import csv
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.facilities.models import Facility
from apps.locations.models import Chamber, Floor, Block
from apps.inventory.models import Commodity, GRN, Lot
from apps.inventory.services import create_grn
from apps.parties.models import Party
from apps.delivery.models import DeliveryNote, DeliveryLine
from apps.delivery.services import create_delivery_note
from libs.sanitizers import clean_text, title_name, clean_gstin, clean_phone, clean_email
from libs.fiscal import fy_bounds

class DryRunRollback(Exception):
    pass

class Command(BaseCommand):
    help = "Import legacy FAS stock data from cleaned CSVs."

    def add_arguments(self, parser):
        parser.add_argument(
            '--facility',
            type=int,
            required=True,
            help='Target Facility ID to import data into.',
        )
        parser.add_argument(
            '--source',
            type=str,
            default='FASstuff/code/exports/cleaned',
            help='Directory containing cleaned CSV files.',
        )
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Commit the transaction to the database. If not specified, runs in dry-run mode.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=True,
            help='Execute everything but roll back changes at the end. (Default)',
        )
        parser.add_argument(
            '--full-history',
            action='store_true',
            help='Import all historical records instead of only open stock.',
        )
        parser.add_argument(
            '--open-stock-only',
            action='store_true',
            default=True,
            help='Import only lots with remaining stock > 0 and their GRNs. (Default)',
        )
        parser.add_argument(
            '--parties-only',
            action='store_true',
            help='Import parties, commodities, chambers, floors and blocks, and stop.',
        )
        parser.add_argument(
            '--financial-year',
            type=str,
            help='Import only documents dated within that financial year YYYY-YY.',
        )
        parser.add_argument(
            '--include-referenced-lots',
            action='store_true',
            help='Include GRNs and lots referenced by in-range delivery notes.',
        )

    def handle(self, *args, **options):
        facility_id = options['facility']
        source_dir = options['source']
        commit = options['commit']
        # If --commit is passed, dry_run is False; otherwise it is True.
        dry_run = not commit
        full_history = options['full_history']
        parties_only = options.get('parties_only', False)
        financial_year = options.get('financial_year')
        include_referenced_lots = options.get('include_referenced_lots', False)

        # Validation checks
        if financial_year and full_history:
            self.stderr.write(self.style.ERROR("Cannot combine --financial-year with --full-history."))
            return

        if include_referenced_lots and not financial_year:
            self.stderr.write(self.style.ERROR("Cannot use --include-referenced-lots without --financial-year."))
            return

        fy_start = None
        fy_end = None
        if financial_year:
            try:
                fy_start, fy_end = fy_bounds(financial_year)
            except ValueError as e:
                self.stderr.write(self.style.ERROR(f"Invalid financial year label '{financial_year}': {e}"))
                return

        if financial_year:
            open_stock_only = False
        else:
            open_stock_only = not full_history

        # Resolve relative source directory path
        if not os.path.isabs(source_dir):
            from django.conf import settings
            project_root = settings.BASE_DIR.parent
            source_dir = os.path.join(project_root, source_dir)

        # 1. Fetch Facility
        try:
            facility = Facility.objects.get(pk=facility_id)
        except Facility.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Facility with ID {facility_id} does not exist."))
            return

        # Helper to read CSV
        def read_csv(filename):
            path = os.path.join(source_dir, filename)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Required CSV file not found: {path}")
            with open(path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)

        # 2. Load CSV files
        try:
            parties_csv = read_csv('cleaned_parties.csv')
            commodities_csv = read_csv('cleaned_commodities.csv')
            chambers_csv = read_csv('cleaned_chambers.csv')
            floors_csv = read_csv('cleaned_floors.csv')
            blocks_csv = read_csv('cleaned_blocks.csv')
            if not parties_only:
                grns_csv = read_csv('cleaned_grns.csv')
                lots_csv = read_csv('cleaned_lots.csv')
                delivery_notes_csv = read_csv('cleaned_delivery_notes.csv')
                delivery_lines_csv = read_csv('cleaned_delivery_lines.csv')
            else:
                grns_csv = []
                lots_csv = []
                delivery_notes_csv = []
                delivery_lines_csv = []
        except FileNotFoundError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        # Metrics trackers
        summary = {
            'parties_created': 0,
            'parties_matched': 0,
            'parties_failed': 0,
            'commodities_created': 0,
            'commodities_matched': 0,
            'commodities_failed': 0,
            'chambers_created': 0,
            'chambers_matched': 0,
            'chambers_failed': 0,
            'floors_created': 0,
            'floors_matched': 0,
            'floors_failed': 0,
            'blocks_created': 0,
            'blocks_matched': 0,
            'blocks_failed': 0,
            'grns_created': 0,
            'grns_skipped': 0,
            'grns_failed': 0,
            'lots_created': 0,
            'lots_skipped': 0,
            'lots_failed': 0,
            'dns_created': 0,
            'dns_skipped': 0,
            'dns_failed': 0,
            'lines_created': 0,
            'lines_skipped': 0,
            'lines_failed': 0,
            'total_initial_qty': 0,
            'total_remaining_qty': 0,
            'grns_skipped_fy': 0,
            'dns_skipped_fy': 0,
            'lines_skipped_no_lot': 0,
            'dns_skipped_no_lines': 0,
            'supporting_grns_pulled': 0,
        }

        failures = {}
        skipped_lines_reasons = {}

        def record_failure(reason):
            failures[reason] = failures.get(reason, 0) + 1

        # Maps lot_number -> lot row
        lot_by_number = {row['lot_number']: row for row in lots_csv}
        # Maps grn_number -> grn row
        grn_by_number = {row['grn_number']: row for row in grns_csv}

        referenced_grn_numbers = set()
        if not parties_only and include_referenced_lots:
            # 1. Determine the set of delivery notes in range
            in_range_dn_numbers = set()
            for dn_row in delivery_notes_csv:
                try:
                    dispatch_date = datetime.strptime(dn_row['dispatch_date'], '%Y-%m-%d').date()
                except ValueError:
                    continue
                if fy_start and fy_end and fy_start <= dispatch_date <= fy_end:
                    in_range_dn_numbers.add(dn_row['dn_number'])

            # 2. Collect the lot_numbers their lines reference
            referenced_lot_numbers = set()
            for line_row in delivery_lines_csv:
                if line_row['dn_number'] in in_range_dn_numbers:
                    referenced_lot_numbers.add(line_row['lot_number'])

            # 3. Resolve those to their GRNs via the lots CSV
            for lot_num in referenced_lot_numbers:
                lot_row = lot_by_number.get(lot_num)
                if lot_row and lot_row.get('grn_number'):
                    referenced_grn_numbers.add(lot_row['grn_number'])

        # Run within transactional atomic block
        try:
            with transaction.atomic():
                # --- A. Parties ---
                for row in parties_csv:
                    code = row['code']
                    if Party.objects.filter(facility=facility, code=code).exists():
                        summary['parties_matched'] += 1
                    else:
                        try:
                            email_val = clean_email(row['email'])
                            if email_val and '@' not in email_val:
                                email_val = ""
                            
                            phone_val = clean_phone(row['phone'])
                            phone_val = phone_val.replace(' ', '')
                            if len(phone_val) > 20:
                                phone_val = phone_val[:20]

                            party = Party(
                                facility=facility,
                                name=title_name(row['name']),
                                code=code,
                                type=row['type'],
                                phone=phone_val,
                                email=email_val,
                                address=clean_text(row['address']),
                                gstin=clean_gstin(row['gstin']),
                                is_active=row['is_active'].lower() == 'true'
                            )
                            party.full_clean()
                            party.save()
                            summary['parties_created'] += 1
                        except DjangoValidationError as e:
                            summary['parties_failed'] += 1
                            record_failure(f"Party Validation: {e.messages if hasattr(e, 'messages') else str(e)}")

                # --- B. Commodities ---
                for row in commodities_csv:
                    code = row['code']
                    if Commodity.objects.filter(facility=facility, code=code).exists():
                        summary['commodities_matched'] += 1
                    else:
                        try:
                            commodity = Commodity(
                                facility=facility,
                                name=title_name(row['name']),
                                code=code,
                                unit=row['unit'],
                                description=clean_text(row['description']),
                                is_active=row['is_active'].lower() == 'true'
                            )
                            commodity.full_clean()
                            commodity.save()
                            summary['commodities_created'] += 1
                        except DjangoValidationError as e:
                            summary['commodities_failed'] += 1
                            record_failure(f"Commodity Validation: {e.messages if hasattr(e, 'messages') else str(e)}")

                # --- C. Locations (Chambers, Floors, Blocks) ---
                for row in chambers_csv:
                    code = row['code']
                    if Chamber.objects.filter(facility=facility, code=code).exists():
                        summary['chambers_matched'] += 1
                    else:
                        try:
                            chamber = Chamber(
                                facility=facility,
                                name=title_name(row['name']),
                                code=code,
                                is_active=row['is_active'].lower() == 'true'
                            )
                            chamber.full_clean()
                            chamber.save()
                            summary['chambers_created'] += 1
                        except DjangoValidationError as e:
                            summary['chambers_failed'] += 1
                            record_failure(f"Chamber Validation: {e.messages if hasattr(e, 'messages') else str(e)}")

                for row in floors_csv:
                    code = row['code']
                    if Floor.objects.filter(chamber__facility=facility, code=code).exists():
                        summary['floors_matched'] += 1
                    else:
                        try:
                            chamber = Chamber.objects.get(facility=facility, code=row['chamber_code'])
                        except Chamber.DoesNotExist:
                            summary['floors_failed'] += 1
                            record_failure(f"Floor Import: Chamber '{row['chamber_code']}' not found")
                            continue
                        try:
                            floor = Floor(
                                chamber=chamber,
                                name=title_name(row['name']),
                                code=code,
                                is_active=row['is_active'].lower() == 'true'
                            )
                            floor.full_clean()
                            floor.save()
                            summary['floors_created'] += 1
                        except DjangoValidationError as e:
                            summary['floors_failed'] += 1
                            record_failure(f"Floor Validation: {e.messages if hasattr(e, 'messages') else str(e)}")

                for row in blocks_csv:
                    code = row['code']
                    if Block.objects.filter(floor__chamber__facility=facility, code=code).exists():
                        summary['blocks_matched'] += 1
                    else:
                        try:
                            floor = Floor.objects.get(chamber__facility=facility, code=row['floor_code'])
                        except Floor.DoesNotExist:
                            summary['blocks_failed'] += 1
                            record_failure(f"Block Import: Floor '{row['floor_code']}' not found")
                            continue
                        capacity = int(row['capacity_bags']) if row.get('capacity_bags') else None
                        try:
                            block = Block(
                                floor=floor,
                                name=title_name(row['name']),
                                code=code,
                                capacity_bags=capacity,
                                is_active=row['is_active'].lower() == 'true'
                            )
                            block.full_clean()
                            block.save()
                            summary['blocks_created'] += 1
                        except DjangoValidationError as e:
                            summary['blocks_failed'] += 1
                            record_failure(f"Block Validation: {e.messages if hasattr(e, 'messages') else str(e)}")

                if not parties_only:
                    # --- D. GRNs and Lots ---
                    # Group lots by GRN legacy reference
                    lots_by_grn = {}
                    for lot_row in lots_csv:
                        # Apply --open-stock-only logic
                        if open_stock_only and int(lot_row['remaining_qty']) <= 0:
                            continue
                        lots_by_grn.setdefault(lot_row['grn_number'], []).append(lot_row)

                    for grn_row in grns_csv:
                        grn_ref = grn_row['grn_number']
                        if open_stock_only and grn_ref not in lots_by_grn:
                            continue

                        # Parse receipt_date early to apply year filter
                        try:
                            receipt_date = datetime.strptime(grn_row['receipt_date'], '%Y-%m-%d').date()
                        except ValueError:
                            summary['grns_failed'] += 1
                            record_failure(f"GRN Import: Invalid receipt_date format '{grn_row['receipt_date']}'")
                            continue

                        is_supporting_grn = False
                        if fy_start and fy_end:
                            is_in_fy = (fy_start <= receipt_date <= fy_end)
                            is_referenced = include_referenced_lots and (grn_ref in referenced_grn_numbers)
                            if not is_in_fy and not is_referenced:
                                summary['grns_skipped_fy'] += 1
                                continue
                            if is_referenced and not is_in_fy:
                                is_supporting_grn = True

                        # Idempotency check:
                        if GRN.objects.filter(facility=facility, legacy_ref=grn_ref).exists():
                            summary['grns_skipped'] += 1
                            if is_supporting_grn:
                                summary['supporting_grns_pulled'] += 1
                            for lot_row in lots_by_grn.get(grn_ref, []):
                                if Lot.objects.filter(facility=facility, legacy_ref=lot_row['lot_number']).exists():
                                    summary['lots_skipped'] += 1
                                else:
                                    summary['lots_failed'] += 1
                                    record_failure("Lot Import: Cannot add lot to already existing GRN")
                            continue

                        # Lookup Party
                        try:
                            party = Party.objects.get(facility=facility, code=grn_row['party_code'])
                        except Party.DoesNotExist:
                            summary['grns_failed'] += 1
                            for lot_row in lots_by_grn.get(grn_ref, []):
                                summary['lots_failed'] += 1
                                record_failure(f"Lot Import: GRN Party '{grn_row['party_code']}' not found")
                            record_failure(f"GRN Import: Party '{grn_row['party_code']}' not found")
                            continue

                        # Prepare lot items
                        items_data = []
                        imported_lot_rows = []
                        has_error = False

                        for lot_row in lots_by_grn.get(grn_ref, []):
                            if Lot.objects.filter(facility=facility, legacy_ref=lot_row['lot_number']).exists():
                                summary['lots_skipped'] += 1
                                continue

                            # Lookup Commodity
                            try:
                                commodity = Commodity.objects.get(facility=facility, code=lot_row['commodity_code'])
                            except Commodity.DoesNotExist:
                                summary['lots_failed'] += 1
                                record_failure(f"Lot Import: Commodity '{lot_row['commodity_code']}' not found")
                                has_error = True
                                break

                            # Resolve location references
                            chamber_ref = None
                            floor_ref = None
                            block_ref = None

                            if lot_row.get('block_ref_code'):
                                try:
                                    block_ref = Block.objects.get(floor__chamber__facility=facility, code=lot_row['block_ref_code'])
                                    floor_ref = block_ref.floor
                                    chamber_ref = floor_ref.chamber
                                except Block.DoesNotExist:
                                    summary['lots_failed'] += 1
                                    record_failure(f"Lot Import: Block '{lot_row['block_ref_code']}' not found")
                                    has_error = True
                                    break
                            elif lot_row.get('floor_ref_code'):
                                try:
                                    floor_ref = Floor.objects.get(chamber__facility=facility, code=lot_row['floor_ref_code'])
                                    chamber_ref = floor_ref.chamber
                                except Floor.DoesNotExist:
                                    summary['lots_failed'] += 1
                                    record_failure(f"Lot Import: Floor '{lot_row['floor_ref_code']}' not found")
                                    has_error = True
                                    break
                            elif lot_row.get('chamber_ref_code'):
                                try:
                                    chamber_ref = Chamber.objects.get(facility=facility, code=lot_row['chamber_ref_code'])
                                except Chamber.DoesNotExist:
                                    summary['lots_failed'] += 1
                                    record_failure(f"Lot Import: Chamber '{lot_row['chamber_ref_code']}' not found")
                                    has_error = True
                                    break

                            item_dict = {
                                'commodity_id': commodity.id,
                                'initial_qty': int(lot_row['initial_qty']),
                                'rent_rate_per_unit': Decimal(lot_row['rent_rate_per_unit']),
                                'unit': lot_row['unit'] or commodity.unit,
                                'chamber': lot_row['chamber'],
                                'floor': lot_row['floor'],
                                'rack': lot_row['rack'],
                                'special_remarks': lot_row['special_remarks'],
                                'unit_weight': Decimal(lot_row.get('unit_weight') or '0.00'),
                            }
                            if block_ref:
                                item_dict['block_id'] = block_ref.id
                            if floor_ref:
                                item_dict['floor_id'] = floor_ref.id
                            if chamber_ref:
                                item_dict['chamber_id'] = chamber_ref.id

                            items_data.append(item_dict)
                            imported_lot_rows.append(lot_row)

                        if has_error:
                            summary['grns_failed'] += 1
                            record_failure("GRN Import: One or more lots failed verification")
                            continue

                        if not items_data:
                            summary['grns_skipped'] += 1
                            continue

                        # Call service to create GRN and Lots
                        try:
                            grn = create_grn(
                                facility_id=facility.id,
                                party_id=party.id,
                                receipt_date=receipt_date,
                                vehicle_number=grn_row['vehicle_number'],
                                remarks=grn_row['remarks'],
                                status=grn_row['status'],
                                items=items_data,
                                require_location=False  # Legacy imports genuinely have no location recorded and must bypass this requirement
                            )
                            # Set legacy_ref on GRN
                            grn.legacy_ref = grn_ref
                            grn.save(update_fields=['legacy_ref'])
                            summary['grns_created'] += 1
                            if is_supporting_grn:
                                summary['supporting_grns_pulled'] += 1

                            # Set legacy_ref, remaining_qty, and inward_date on created Lots
                            created_lots = list(grn.lots.order_by('id'))
                            for lot_obj, lot_row in zip(created_lots, imported_lot_rows):
                                lot_obj.legacy_ref = lot_row['lot_number']
                                lot_obj.remaining_qty = int(lot_row['remaining_qty'])
                                if lot_row.get('inward_date'):
                                    try:
                                        lot_obj.inward_date = datetime.strptime(lot_row['inward_date'], '%Y-%m-%d').date()
                                    except ValueError:
                                        pass
                                lot_obj.save(update_fields=['legacy_ref', 'remaining_qty', 'inward_date'])
                                summary['lots_created'] += 1
                                summary['total_initial_qty'] += lot_obj.initial_qty
                                summary['total_remaining_qty'] += lot_obj.remaining_qty
                        except DjangoValidationError as e:
                            summary['grns_failed'] += 1
                            for lot_row in imported_lot_rows:
                                summary['lots_failed'] += 1
                            record_failure(f"GRN/Lot Validation: {e.messages if hasattr(e, 'messages') else str(e)}")

                    # --- E. Delivery Notes and Delivery Lines ---
                    if not open_stock_only:
                        # Calculate sum of delivery line quantities for each lot to temporarily adjust remaining_qty
                        del_sum_by_lot = {}
                        for line_row in delivery_lines_csv:
                            lot_num = line_row['lot_number']
                            del_sum_by_lot[lot_num] = del_sum_by_lot.get(lot_num, 0) + int(line_row['qty'])

                        # Boost the remaining_qty of all lots in the database to prevent validation failures during note creation
                        for lot_row in lots_csv:
                            lot_num = lot_row['lot_number']
                            final_rem = int(lot_row['remaining_qty'])
                            sum_del = del_sum_by_lot.get(lot_num, 0)
                            temp_rem = final_rem + sum_del
                            Lot.objects.filter(facility=facility, legacy_ref=lot_num).update(remaining_qty=temp_rem)

                        # Group delivery lines by DN legacy reference
                        lines_by_dn = {}
                        for line_row in delivery_lines_csv:
                            lines_by_dn.setdefault(line_row['dn_number'], []).append(line_row)

                        for dn_row in delivery_notes_csv:
                            dn_ref = dn_row['dn_number']

                            # Parse dispatch_date early to apply year filter
                            try:
                                dispatch_date = datetime.strptime(dn_row['dispatch_date'], '%Y-%m-%d').date()
                            except ValueError:
                                summary['dns_failed'] += 1
                                record_failure(f"DeliveryNote Import: Invalid dispatch_date format '{dn_row['dispatch_date']}'")
                                continue

                            if fy_start and fy_end:
                                if not (fy_start <= dispatch_date <= fy_end):
                                    summary['dns_skipped_fy'] += 1
                                    continue

                            if DeliveryNote.objects.filter(facility=facility, legacy_ref=dn_ref).exists():
                                summary['dns_skipped'] += 1
                                for line_row in lines_by_dn.get(dn_ref, []):
                                    summary['lines_skipped'] += 1
                                continue

                            # Find Party
                            try:
                                party = Party.objects.get(facility=facility, code=dn_row['party_code'])
                            except Party.DoesNotExist:
                                summary['dns_failed'] += 1
                                for line_row in lines_by_dn.get(dn_ref, []):
                                    summary['lines_failed'] += 1
                                    record_failure(f"DeliveryLine Import: DN Party '{dn_row['party_code']}' not found")
                                record_failure(f"DeliveryNote Import: Party '{dn_row['party_code']}' not found")
                                continue

                            # Prepare delivery lines
                            lines_data = []
                            imported_line_rows = []
                            lines_for_this_dn = lines_by_dn.get(dn_ref, [])
                            resolved_lines_count = 0

                            for line_row in lines_for_this_dn:
                                lot_num = line_row['lot_number']
                                try:
                                    lot = Lot.objects.get(facility=facility, legacy_ref=lot_num)
                                    lines_data.append({
                                        'lot_id': lot.id,
                                        'qty': int(line_row['qty'])
                                    })
                                    imported_line_rows.append(line_row)
                                    resolved_lines_count += 1
                                except Lot.DoesNotExist:
                                    # Determine category and example info for missing lot
                                    lot_csv_row = lot_by_number.get(lot_num)
                                    if not lot_csv_row:
                                        category = "lot not present in the lots CSV"
                                        example_info = f"Lot {lot_num}, GRN N/A"
                                    else:
                                        grn_num = lot_csv_row.get('grn_number') or "N/A"
                                        grn_csv_row = grn_by_number.get(grn_num) if grn_num != "N/A" else None
                                        if grn_num == "N/A" or not grn_csv_row:
                                            category = "lot's GRN not present in the GRN CSV"
                                            example_info = f"Lot {lot_num}, GRN {grn_num}"
                                        else:
                                            try:
                                                grn_receipt_date = datetime.strptime(grn_csv_row['receipt_date'], '%Y-%m-%d').date()
                                                if fy_start and fy_end and not (fy_start <= grn_receipt_date <= fy_end):
                                                    category = "lot's GRN falls outside the imported financial year"
                                                    example_info = f"Lot {lot_num}, GRN {grn_num}"
                                                else:
                                                    category = "any other/unknown reason"
                                                    example_info = f"Lot {lot_num}, GRN {grn_num}"
                                            except ValueError:
                                                category = "any other/unknown reason"
                                                example_info = f"Lot {lot_num}, GRN {grn_num}"

                                    summary['lines_skipped_no_lot'] += 1
                                    if category not in skipped_lines_reasons:
                                        skipped_lines_reasons[category] = {'count': 0, 'examples': []}
                                    skipped_lines_reasons[category]['count'] += 1
                                    if example_info not in skipped_lines_reasons[category]['examples']:
                                        skipped_lines_reasons[category]['examples'].append(example_info)

                            if len(lines_for_this_dn) > 0 and resolved_lines_count == 0:
                                summary['dns_skipped_no_lines'] += 1
                                continue

                            if not lines_data:
                                summary['dns_skipped'] += 1
                                continue

                            # Create DeliveryNote
                            try:
                                dn = create_delivery_note(
                                    facility_id=facility.id,
                                    party_id=party.id,
                                    dispatch_date=dispatch_date,
                                    vehicle_number=dn_row['vehicle_number'],
                                    remarks=dn_row['remarks'],
                                    status=dn_row['status'],
                                    lines=lines_data
                                )
                                dn.legacy_ref = dn_ref
                                dn.save(update_fields=['legacy_ref'])
                                summary['dns_created'] += 1

                                # Update created lines with CSV's balance_after
                                created_lines = list(dn.lines.order_by('id'))
                                for line_obj, line_row in zip(created_lines, imported_line_rows):
                                    line_obj.balance_after = int(line_row['balance_after']) if line_row['balance_after'] else None
                                    line_obj.save(update_fields=['balance_after'])
                                    summary['lines_created'] += 1
                            except DjangoValidationError as e:
                                summary['dns_failed'] += 1
                                for line_row in imported_line_rows:
                                    summary['lines_failed'] += 1
                                record_failure(f"DeliveryNote/Line Validation: {e.messages if hasattr(e, 'messages') else str(e)}")

                    # --- F. Force Align Remaining Quantities ---
                    # This aligns remaining_qty exactly to the legacy values, compensating for any potential deviations
                    for lot_row in lots_csv:
                        Lot.objects.filter(facility=facility, legacy_ref=lot_row['lot_number']).update(
                            remaining_qty=int(lot_row['remaining_qty'])
                        )

                if dry_run:
                    raise DryRunRollback()

        except DryRunRollback:
            pass

        # Print summary after atomic block is fully completed and exited
        self._print_summary(
            summary, failures, dry_run, open_stock_only,
            parties_only=parties_only,
            financial_year=financial_year,
            fy_start=fy_start,
            fy_end=fy_end,
            skipped_lines_reasons=skipped_lines_reasons,
            include_referenced_lots=include_referenced_lots
        )

    def _print_summary(
        self, summary, failures, dry_run, open_stock_only,
        parties_only=False, financial_year=None, fy_start=None, fy_end=None,
        skipped_lines_reasons=None, include_referenced_lots=False
    ):
        self.stdout.write("")
        self.stdout.write("==================================================")
        if dry_run:
            self.stdout.write(" LEGACY IMPORT SUMMARY (DRY RUN - ROLLED BACK)")
        else:
            self.stdout.write(" LEGACY IMPORT SUMMARY (COMMITTED)")
        self.stdout.write("==================================================")
        
        # Mode information
        if parties_only:
            self.stdout.write("Mode: Parties Only")
        elif financial_year:
            self.stdout.write(f"Mode: Financial Year ({financial_year})")
            self.stdout.write(f"  - Bounds             : {fy_start} to {fy_end}")
            if include_referenced_lots:
                self.stdout.write("  - Include Referenced Lots: Enabled")
        elif not open_stock_only:
            self.stdout.write("Mode: Full History")
        else:
            self.stdout.write("Mode: Open Stock Only")
        self.stdout.write("--------------------------------------------------")

        self.stdout.write("Parties:")
        self.stdout.write(f"  - Created            : {summary['parties_created']}")
        self.stdout.write(f"  - Matched            : {summary['parties_matched']}")
        self.stdout.write(f"  - Failed             : {summary['parties_failed']}")
        
        self.stdout.write("Commodities:")
        self.stdout.write(f"  - Created            : {summary['commodities_created']}")
        self.stdout.write(f"  - Matched            : {summary['commodities_matched']}")
        self.stdout.write(f"  - Failed             : {summary['commodities_failed']}")
        
        self.stdout.write("Locations:")
        self.stdout.write(f"  - Chambers (New/Match): {summary['chambers_created']} / {summary['chambers_matched']}")
        self.stdout.write(f"  - Floors (New/Match)  : {summary['floors_created']} / {summary['floors_matched']}")
        self.stdout.write(f"  - Blocks (New/Match)  : {summary['blocks_created']} / {summary['blocks_matched']}")
        
        if not parties_only:
            self.stdout.write("Goods Receipt Notes (GRNs):")
            self.stdout.write(f"  - Created            : {summary['grns_created']}")
            self.stdout.write(f"  - Skipped            : {summary['grns_skipped']}")
            if financial_year:
                self.stdout.write(f"  - Skipped (FY Filter): {summary['grns_skipped_fy']}")
            self.stdout.write(f"  - Failed             : {summary['grns_failed']}")
            if include_referenced_lots:
                self.stdout.write(f"  - Supporting Records : {summary.get('supporting_grns_pulled', 0)} GRNs were pulled in as supporting records; their remaining quantities reflect only the imported movements.")
            
            self.stdout.write("Lots:")
            self.stdout.write(f"  - Created            : {summary['lots_created']}")
            self.stdout.write(f"  - Skipped            : {summary['lots_skipped']}")
            self.stdout.write(f"  - Failed             : {summary['lots_failed']}")
            self.stdout.write(f"  - Initial Qty (Bags) : {summary['total_initial_qty']}")
            self.stdout.write(f"  - Remaining Qty (Bags): {summary['total_remaining_qty']}")

            if not open_stock_only:
                self.stdout.write("Delivery Notes:")
                self.stdout.write(f"  - Created            : {summary['dns_created']}")
                self.stdout.write(f"  - Skipped            : {summary['dns_skipped']}")
                if financial_year:
                    self.stdout.write(f"  - Skipped (FY Filter): {summary['dns_skipped_fy']}")
                    self.stdout.write(f"  - Skipped (Empty)    : {summary['dns_skipped_no_lines']}")
                self.stdout.write(f"  - Failed             : {summary['dns_failed']}")
                
                self.stdout.write("Delivery Lines:")
                self.stdout.write(f"  - Created            : {summary['lines_created']}")
                self.stdout.write(f"  - Skipped            : {summary['lines_skipped']}")
                if financial_year:
                    self.stdout.write(f"  - Skipped (No Lot)   : {summary['lines_skipped_no_lot']}")
                self.stdout.write(f"  - Failed             : {summary['lines_failed']}")

                if skipped_lines_reasons:
                    self.stdout.write("  Skipped Lines Reasons Breakdown:")
                    for category, data in sorted(skipped_lines_reasons.items()):
                        count = data.get('count', 0)
                        if count == 0:
                            continue
                        self.stdout.write(f"    * {category}: {count}")
                        examples = data.get('examples', [])
                        for example in examples[:5]:
                            self.stdout.write(f"      - {example}")
                        if count > 5:
                            self.stdout.write(f"      - ... and {count - 5} more")

        if failures:
            self.stdout.write("--------------------------------------------------")
            self.stdout.write("Grouped Failures Summary:")
            for reason, count in sorted(failures.items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f"  - {reason}: {count}")

        self.stdout.write("==================================================")
