from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from libs.choices import ChargeMode
from apps.facilities.models import Facility
from apps.facilities.services import create_facility
from apps.locations.models import Chamber, Floor, Block
from apps.locations.services import create_chamber, create_floor, create_block
from apps.inventory.models import Commodity, GRN, Lot, Sequence
from apps.inventory.services import create_commodity, create_grn
from apps.parties.models import Party
from apps.parties.services import create_party
from apps.delivery.models import DeliveryNote, DeliveryLine
from apps.delivery.services import create_delivery_note
from apps.invoicing.models import Invoice, InvoiceLine, Payment
from apps.invoicing.services import (
    generate_invoices_for_uninvoiced_deliveries,
    post_invoice,
    record_payment,
)


class Command(BaseCommand):
    help = "Seed demo dataset for Jaipur Cold Storage Pvt. Ltd."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Allow running against a non-empty database.',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo/business data before seeding.',
        )

    def handle(self, *args, **options):
        force = options['force']
        reset = options['reset']

        # Safety Check: Refuse to run if database contains non-default facilities without --force or --reset
        existing_non_default = Facility.objects.exclude(name="Default Facility")

        if existing_non_default.exists() and not force and not reset:
            fac_names = ", ".join([f"'{f.name}' (ID {f.id})" for f in existing_non_default])
            self.stdout.write(
                self.style.ERROR(
                    f"Refusing to run: Database already contains non-default facility data: {fac_names}.\n"
                    "Use --reset to delete existing demo data, or --force to run without resetting."
                )
            )
            return

        with transaction.atomic():
            deleted_counts = {}
            if reset:
                self.stdout.write("Resetting existing demo/business data...")
                deleted_counts = self._delete_data(target_facilities=None)
            else:
                default_fac = Facility.objects.filter(name="Default Facility")
                if default_fac.exists():
                    self.stdout.write("Deleting 'Default Facility' placeholder and dependent rows...")
                    deleted_counts = self._delete_data(target_facilities=default_fac)

            if deleted_counts and any(c > 0 for c in deleted_counts.values()):
                self.stdout.write(self.style.WARNING("Deleted existing records:"))
                for entity, count in deleted_counts.items():
                    if count > 0:
                        self.stdout.write(f"  - {entity}: {count}")

            self.stdout.write("Populating demo dataset for Jaipur Cold Storage Pvt. Ltd....")
            summary = self._seed_demo_data()

        # Printing happens only after the transaction has committed. Inside the
        # atomic block a console encoding error would roll back the entire seed.
        self._print_summary(summary)

    def _delete_data(self, target_facilities=None) -> dict[str, int]:
        """
        Delete existing business data in strict FK-safe order (child to parent).
        Never touches the auth user table (django User).
        Never touches Sequence rows for facilities it is not deleting.
        """
        counts = {}
        if target_facilities is not None:
            fac_ids = list(target_facilities.values_list('id', flat=True))
            if not fac_ids:
                return counts

            counts['Payments'] = Payment.objects.filter(invoice__facility_id__in=fac_ids).delete()[0]
            counts['Invoice Lines'] = InvoiceLine.objects.filter(invoice__facility_id__in=fac_ids).delete()[0]
            counts['Invoices'] = Invoice.objects.filter(facility_id__in=fac_ids).delete()[0]
            counts['Delivery Lines'] = DeliveryLine.objects.filter(facility_id__in=fac_ids).delete()[0]
            counts['Delivery Notes'] = DeliveryNote.objects.filter(facility_id__in=fac_ids).delete()[0]
            counts['Lots'] = Lot.objects.filter(facility_id__in=fac_ids).delete()[0]
            counts['Goods Receipt Notes (GRNs)'] = GRN.objects.filter(facility_id__in=fac_ids).delete()[0]
            counts['Commodities'] = Commodity.objects.filter(facility_id__in=fac_ids).delete()[0]
            counts['Parties'] = Party.objects.filter(facility_id__in=fac_ids).delete()[0]
            counts['Location Blocks'] = Block.objects.filter(floor__chamber__facility_id__in=fac_ids).delete()[0]
            counts['Location Floors'] = Floor.objects.filter(chamber__facility_id__in=fac_ids).delete()[0]
            counts['Location Chambers'] = Chamber.objects.filter(facility_id__in=fac_ids).delete()[0]
            counts['Sequences'] = Sequence.objects.filter(facility_id__in=fac_ids).delete()[0]
            counts['Facilities'] = Facility.objects.filter(id__in=fac_ids).delete()[0]
        else:
            counts['Payments'] = Payment.objects.all().delete()[0]
            counts['Invoice Lines'] = InvoiceLine.objects.all().delete()[0]
            counts['Invoices'] = Invoice.objects.all().delete()[0]
            counts['Delivery Lines'] = DeliveryLine.objects.all().delete()[0]
            counts['Delivery Notes'] = DeliveryNote.objects.all().delete()[0]
            counts['Lots'] = Lot.objects.all().delete()[0]
            counts['Goods Receipt Notes (GRNs)'] = GRN.objects.all().delete()[0]
            counts['Commodities'] = Commodity.objects.all().delete()[0]
            counts['Parties'] = Party.objects.all().delete()[0]
            counts['Location Blocks'] = Block.objects.all().delete()[0]
            counts['Location Floors'] = Floor.objects.all().delete()[0]
            counts['Location Chambers'] = Chamber.objects.all().delete()[0]
            counts['Sequences'] = Sequence.objects.all().delete()[0]
            counts['Facilities'] = Facility.objects.all().delete()[0]

        return counts

    def _seed_demo_data(self) -> dict:
        today = timezone.now().date()

        facility = self._create_facility()
        blocks = self._create_locations(facility)
        commodities = self._create_commodities(facility)
        parties = self._create_parties(facility)
        grn_info = self._create_grns(facility, parties, commodities, blocks, today)
        dn_list = self._create_deliveries(facility, grn_info['lots'], today)
        invoices = self._create_invoices_and_payments(facility, parties, today)

        return {
            'facility': facility,
            'chambers_count': 3,
            'floors_count': 6,
            'blocks_count': len(blocks),
            'commodities_count': len(commodities),
            'parties_count': len(parties),
            'grns_count': len(grn_info['grns']),
            'lots_count': len(grn_info['lots']),
            'dns_count': len(dn_list),
            'invoices': invoices,
        }

    def _create_facility(self) -> Facility:
        return create_facility(
            name="Jaipur Cold Storage Pvt. Ltd.",
            address="Plot No. C-48, VKIA Phase 1, Road No. 5, Vishwakarma Industrial Area, Jaipur, Rajasthan 302013",
            gstin="08AAACJ1234K1Z2",
            phone="+91 141 2334455",
            factory_phone="+91 141 2334456",
            bank_account_no="920020048571234",
            bank_ifsc="UTIB0000123",
            terms_and_conditions=(
                "1. Goods stored at owner's risk regarding natural decay/weight loss. "
                "2. Storage charges calculated on monthly/slab basis. "
                "3. Delivery issued only against original GRN receipt or authorized order."
            )
        )

    def _create_locations(self, facility: Facility) -> list[Block]:
        blocks = []
        for c_idx in range(1, 4):
            chamber = create_chamber(
                facility_id=facility.id,
                name=f"Chamber {c_idx}",
                sort_order=c_idx
            )
            for f_idx in range(1, 3):
                floor = create_floor(
                    facility_id=facility.id,
                    chamber_id=chamber.id,
                    name=f"Floor {f_idx}",
                    sort_order=f_idx
                )
                for b_idx in range(1, 5):
                    block = create_block(
                        facility_id=facility.id,
                        chamber_id=chamber.id,
                        floor_id=floor.id,
                        name=f"Block {b_idx}",
                        sort_order=b_idx,
                        capacity_bags=5000
                    )
                    blocks.append(block)
        return blocks

    def _create_commodities(self, facility: Facility) -> list[Commodity]:
        specs = [
            ("Potato (Kufri Pukhraj)", "BAGS", "Cold storage table potatoes from Agra/Agra-Jaipur belt"),
            ("Green Peas", "BAGS", "Fresh green peas packed in mesh bags"),
            ("Sweet Corn", "BOXES", "Processed sweet corn in refrigerated corrugated boxes"),
            ("Cauliflower", "CRATES", "Fresh farm cauliflower packed in plastic crates"),
            ("Red Carrot", "BAGS", "Local desi red carrots in 50kg bags"),
            ("Green Chilli", "CRATES", "Teja variety green chillies in vented crates"),
            ("Fresh Ginger", "BOXES", "High grade ginger from North-East in 20kg boxes"),
            ("Garlic (Kota Brand)", "BAGS", "Dried garlic bulbs in mesh bags"),
            ("Shimla Apple", "BOXES", "Royal Delicious apples in corrugated cartons"),
        ]
        commodities = []
        for name, unit, desc in specs:
            c = create_commodity(
                facility_id=facility.id,
                name=name,
                unit=unit,
                description=desc
            )
            commodities.append(c)
        return commodities

    def _create_parties(self, facility: Facility) -> list[Party]:
        specs = [
            ("Sharma Traders", Party.PartyType.DEPOSITOR, "+91 9829012345", "sharma.traders@example.com", "Shop 12, Muhana Mandi, Jaipur, Rajasthan", "08AABCS5678D1Z9"),
            ("GD Foods Pvt Ltd", Party.PartyType.DEPOSITOR, "+91 9414012345", "info@gdfoods.example.com", "Industrial Area, Chomu, Jaipur, Rajasthan", "08AAACG8910E1Z3"),
            ("Ramu Ram Farmer", Party.PartyType.DEPOSITOR, "+91 9782012345", "", "Village Rampura, Tehsil Chomu, Jaipur, Rajasthan", ""),
            ("Shekhawat Cold Logistics", Party.PartyType.TRANSPORTER, "+91 9828012345", "dispatch@shekhawatlogistics.example.com", "Near Transport Nagar, Jaipur, Rajasthan", "08AABCS1122F1Z8"),
            ("Rajasthan Agro Supplies", Party.PartyType.VENDOR, "+91 9413012345", "sales@rajagro.example.com", "Grain Market, Surajpole, Jaipur, Rajasthan", "08AAACR3344G1Z7"),
            ("Rameshwar Lal & Sons", Party.PartyType.DEPOSITOR, "+91 9829554433", "rameshwar.sons@example.com", "Gate No. 2, Muhana Mandi, Jaipur, Rajasthan", "08ABCDE4455H1Z6"),
            ("Jaipur Fresh Produce Co.", Party.PartyType.DEPOSITOR, "+91 9829112233", "contact@jaipurfresh.example.com", "Lal Kothi Mandi, Jaipur, Rajasthan", "08AABCF6677J1Z4"),
            ("Hanuman Prasad Farmer", Party.PartyType.DEPOSITOR, "+91 9602033445", "", "Village Bassi, Jaipur, Rajasthan", ""),
            ("Kedia Vegetable Trading", Party.PartyType.DEPOSITOR, "+91 9829223344", "kedia.veg@example.com", "Terminal Market, Muhana, Jaipur, Rajasthan", "08AAACK8899K1Z1"),
            ("Mohan Singh Farmer", Party.PartyType.DEPOSITOR, "+91 9414556677", "", "Village Kalwar, Jaipur, Rajasthan", ""),
            ("Bairwa Organic Farms", Party.PartyType.DEPOSITOR, "+91 9782889900", "bairwa.farms@example.com", "Phulera Road, Sambhar, Jaipur, Rajasthan", ""),
            ("Marwar Spice & Cold Co.", Party.PartyType.DEPOSITOR, "+91 9829778899", "admin@marwarspice.example.com", "Road No. 14, VKIA, Jaipur, Rajasthan", "08AAACM9911L1Z0"),
        ]
        parties = []
        for name, ptype, phone, email, addr, gstin in specs:
            p = create_party(
                facility_id=facility.id,
                name=name,
                type=ptype,
                phone=phone,
                email=email,
                address=addr,
                gstin=gstin
            )
            parties.append(p)
        return parties

    def _create_grns(self, facility: Facility, parties: list[Party], commodities: list[Commodity], blocks: list[Block], today) -> dict:
        comm_map = {c.name: c for c in commodities}
        party_map = {p.name: p for p in parties}

        grn_specs = [
            {
                'party': party_map["Sharma Traders"],
                'days_ago': 115,
                'vehicle': "RJ14 GC 1234",
                'driver': "Rajesh Kumar",
                'transporter': "Shekhawat Cold Logistics",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('800.00'),
                'rate_per_bag': Decimal('0.00'),
                'preservation': Decimal('12.00'),
                'items': [
                    {'commodity': comm_map["Potato (Kufri Pukhraj)"], 'qty': 400, 'rate': Decimal('12.00'), 'block': blocks[0], 'unit_weight': Decimal('50.00'), 'remarks': "A-grade Agra origin"},
                    {'commodity': comm_map["Red Carrot"], 'qty': 250, 'rate': Decimal('14.00'), 'block': blocks[1], 'unit_weight': Decimal('40.00'), 'remarks': "Desi red carrots"},
                ]
            },
            {
                'party': party_map["GD Foods Pvt Ltd"],
                'days_ago': 105,
                'vehicle': "RJ14 GD 5678",
                'driver': "Suresh Singh",
                'transporter': "Self Transport",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_bag': Decimal('3.50'),
                'preservation': Decimal('18.00'),
                'items': [
                    {'commodity': comm_map["Sweet Corn"], 'qty': 500, 'rate': Decimal('18.00'), 'block': blocks[2], 'unit_weight': Decimal('20.00'), 'remarks': "Vacuum sealed boxes"},
                ]
            },
            {
                'party': party_map["Ramu Ram Farmer"],
                'days_ago': 95,
                'vehicle': "RJ14 TA 9012",
                'driver': "Ramu Ram",
                'transporter': "Tractor Trolley",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('600.00'),
                'rate_per_bag': Decimal('0.00'),
                'preservation': Decimal('10.00'),
                'items': [
                    {'commodity': comm_map["Potato (Kufri Pukhraj)"], 'qty': 300, 'rate': Decimal('10.00'), 'block': blocks[3], 'unit_weight': Decimal('50.00'), 'remarks': "Chomu farm fresh"},
                ]
            },
            {
                'party': party_map["Rameshwar Lal & Sons"],
                'days_ago': 85,
                'vehicle': "RJ14 GB 3456",
                'driver': "Mahesh Lal",
                'transporter': "Shekhawat Cold Logistics",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_bag': Decimal('4.00'),
                'preservation': Decimal('16.00'),
                'items': [
                    {'commodity': comm_map["Garlic (Kota Brand)"], 'qty': 350, 'rate': Decimal('16.00'), 'block': blocks[4], 'unit_weight': Decimal('30.00'), 'remarks': "Kota dry garlic"},
                    {'commodity': comm_map["Fresh Ginger"], 'qty': 200, 'rate': Decimal('20.00'), 'block': blocks[5], 'unit_weight': Decimal('25.00'), 'remarks': "Assam ginger boxes"},
                ]
            },
            {
                'party': party_map["Jaipur Fresh Produce Co."],
                'days_ago': 75,
                'vehicle': "HP63 A 7890",
                'driver': "Virender Sharma",
                'transporter': "Himalayan Express",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('900.00'),
                'rate_per_bag': Decimal('0.00'),
                'preservation': Decimal('15.00'),
                'items': [
                    {'commodity': comm_map["Shimla Apple"], 'qty': 450, 'rate': Decimal('15.00'), 'block': blocks[6], 'unit_weight': Decimal('18.00'), 'remarks': "Royal Delicious grade A"},
                ]
            },
            {
                'party': party_map["Hanuman Prasad Farmer"],
                'days_ago': 65,
                'vehicle': "RJ14 TA 1122",
                'driver': "Hanuman Prasad",
                'transporter': "Tractor Trolley",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_bag': Decimal('3.00'),
                'preservation': Decimal('12.00'),
                'items': [
                    {'commodity': comm_map["Green Peas"], 'qty': 280, 'rate': Decimal('12.00'), 'block': blocks[7], 'unit_weight': Decimal('40.00'), 'remarks': "Bassi green harvest"},
                ]
            },
            {
                'party': party_map["Kedia Vegetable Trading"],
                'days_ago': 55,
                'vehicle': "RJ14 GE 4455",
                'driver': "Dinesh Kedia",
                'transporter': "City Tempo",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('1000.00'),
                'rate_per_bag': Decimal('0.00'),
                'preservation': Decimal('14.00'),
                'items': [
                    {'commodity': comm_map["Cauliflower"], 'qty': 320, 'rate': Decimal('14.00'), 'block': blocks[8], 'unit_weight': Decimal('15.00'), 'remarks': "Vented crates"},
                    {'commodity': comm_map["Green Chilli"], 'qty': 180, 'rate': Decimal('15.00'), 'block': blocks[9], 'unit_weight': Decimal('12.00'), 'remarks': "Teja spicy chilli"},
                ]
            },
            {
                'party': party_map["Mohan Singh Farmer"],
                'days_ago': 45,
                'vehicle': "RJ14 TA 3344",
                'driver': "Mohan Singh",
                'transporter': "Tractor Trolley",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_bag': Decimal('2.50'),
                'preservation': Decimal('9.00'),
                'items': [
                    {'commodity': comm_map["Potato (Kufri Pukhraj)"], 'qty': 500, 'rate': Decimal('9.00'), 'block': blocks[10], 'unit_weight': Decimal('50.00'), 'remarks': "Kalwar harvest"},
                ]
            },
            {
                'party': party_map["Marwar Spice & Cold Co."],
                'days_ago': 35,
                'vehicle': "RJ19 GA 9988",
                'driver': "Gopal Ram",
                'transporter': "Marwar Cargo",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('1500.00'),
                'rate_per_bag': Decimal('0.00'),
                'preservation': Decimal('18.00'),
                'items': [
                    {'commodity': comm_map["Garlic (Kota Brand)"], 'qty': 600, 'rate': Decimal('18.00'), 'block': blocks[11], 'unit_weight': Decimal('30.00'), 'remarks': "Premium dry garlic"},
                    {'commodity': comm_map["Fresh Ginger"], 'qty': 300, 'rate': Decimal('20.00'), 'block': blocks[12], 'unit_weight': Decimal('25.00'), 'remarks': "Ginger crates"},
                ]
            },
            {
                'party': party_map["Bairwa Organic Farms"],
                'days_ago': 25,
                'vehicle': "RJ14 GD 7788",
                'driver': "Kalyan Bairwa",
                'transporter': "Local PickUp",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_bag': Decimal('3.00'),
                'preservation': Decimal('11.00'),
                'items': [
                    {'commodity': comm_map["Red Carrot"], 'qty': 350, 'rate': Decimal('11.00'), 'block': blocks[13], 'unit_weight': Decimal('40.00'), 'remarks': "Organic carrots"},
                ]
            },
            {
                'party': party_map["Sharma Traders"],
                'days_ago': 18,
                'vehicle': "RJ14 GC 5544",
                'driver': "Rajesh Kumar",
                'transporter': "Shekhawat Cold Logistics",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('800.00'),
                'rate_per_bag': Decimal('0.00'),
                'preservation': Decimal('13.00'),
                'items': [
                    {'commodity': comm_map["Green Peas"], 'qty': 400, 'rate': Decimal('13.00'), 'block': blocks[14], 'unit_weight': Decimal('40.00'), 'remarks': "Agra fresh peas"},
                ]
            },
            {
                'party': party_map["GD Foods Pvt Ltd"],
                'days_ago': 12,
                'vehicle': "RJ14 GD 9900",
                'driver': "Suresh Singh",
                'transporter': "Self Transport",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_bag': Decimal('3.50'),
                'preservation': Decimal('17.00'),
                'items': [
                    {'commodity': comm_map["Sweet Corn"], 'qty': 450, 'rate': Decimal('18.00'), 'block': blocks[15], 'unit_weight': Decimal('20.00'), 'remarks': "Batch 2 sweet corn"},
                    {'commodity': comm_map["Shimla Apple"], 'qty': 300, 'rate': Decimal('16.00'), 'block': blocks[16], 'unit_weight': Decimal('18.00'), 'remarks': "Apples for juice line"},
                ]
            },
            {
                'party': party_map["Rameshwar Lal & Sons"],
                'days_ago': 7,
                'vehicle': "RJ14 GB 6677",
                'driver': "Mahesh Lal",
                'transporter': "Shekhawat Cold Logistics",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('1200.00'),
                'rate_per_bag': Decimal('0.00'),
                'preservation': Decimal('10.00'),
                'items': [
                    {'commodity': comm_map["Potato (Kufri Pukhraj)"], 'qty': 600, 'rate': Decimal('10.00'), 'block': blocks[17], 'unit_weight': Decimal('50.00'), 'remarks': "New potato lot"},
                ]
            },
            {
                'party': party_map["Jaipur Fresh Produce Co."],
                'days_ago': 4,
                'vehicle': "RJ14 GE 1122",
                'driver': "Virender Sharma",
                'transporter': "City Tempo",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_bag': Decimal('4.00'),
                'preservation': Decimal('14.00'),
                'items': [
                    {'commodity': comm_map["Cauliflower"], 'qty': 250, 'rate': Decimal('14.00'), 'block': blocks[18], 'unit_weight': Decimal('15.00'), 'remarks': "Fresh crates"},
                    {'commodity': comm_map["Green Chilli"], 'qty': 200, 'rate': Decimal('15.00'), 'block': blocks[19], 'unit_weight': Decimal('12.00'), 'remarks': "Chilli crates"},
                ]
            },
            {
                'party': party_map["Marwar Spice & Cold Co."],
                'days_ago': 2,
                'vehicle': "RJ19 GA 3322",
                'driver': "Gopal Ram",
                'transporter': "Marwar Cargo",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('1000.00'),
                'rate_per_bag': Decimal('0.00'),
                'preservation': Decimal('17.00'),
                'items': [
                    {'commodity': comm_map["Garlic (Kota Brand)"], 'qty': 400, 'rate': Decimal('17.00'), 'block': blocks[20], 'unit_weight': Decimal('30.00'), 'remarks': "Kota garlic lot 2"},
                ]
            },
        ]

        grns = []
        created_lots = []
        for spec in grn_specs:
            receipt_date = today - timedelta(days=spec['days_ago'])
            item_dicts = []
            for item in spec['items']:
                item_dicts.append({
                    'commodity_id': item['commodity'].id,
                    'initial_qty': item['qty'],
                    'rent_rate_per_unit': item['rate'],
                    'unit': item['commodity'].unit,
                    'chamber_id': item['block'].floor.chamber_id,
                    'floor_id': item['block'].floor_id,
                    'block_id': item['block'].id,
                    'unit_weight': item['unit_weight'],
                    'special_remarks': item['remarks'],
                })

            grn = create_grn(
                facility_id=facility.id,
                party_id=spec['party'].id,
                receipt_date=receipt_date,
                vehicle_number=spec['vehicle'],
                driver_name=spec['driver'],
                transporter=spec['transporter'],
                remarks="Intake verified and placed in chamber",
                loading_charge=spec['charge'],
                loading_unloading_rate_per_bag=spec['rate_per_bag'],
                loading_charge_mode=spec['mode'],
                preservation_rate_per_bag_per_month=spec['preservation'],
                status=GRN.Status.POSTED,
                items=item_dicts
            )
            grns.append(grn)
            for lot in grn.lots.all():
                created_lots.append(lot)

        return {'grns': grns, 'lots': created_lots}

    def _create_deliveries(self, facility: Facility, lots: list[Lot], today) -> list[DeliveryNote]:
        sharma_potato = [l for l in lots if l.grn.party.name == "Sharma Traders" and l.commodity.name == "Potato (Kufri Pukhraj)"][0]
        sharma_carrot = [l for l in lots if l.grn.party.name == "Sharma Traders" and l.commodity.name == "Red Carrot"][0]
        gdfoods_corn = [l for l in lots if l.grn.party.name == "GD Foods Pvt Ltd" and l.commodity.name == "Sweet Corn"][0]
        ramuram_potato = [l for l in lots if l.grn.party.name == "Ramu Ram Farmer" and l.commodity.name == "Potato (Kufri Pukhraj)"][0]
        rameshwar_garlic = [l for l in lots if l.grn.party.name == "Rameshwar Lal & Sons" and l.commodity.name == "Garlic (Kota Brand)"][0]
        rameshwar_ginger = [l for l in lots if l.grn.party.name == "Rameshwar Lal & Sons" and l.commodity.name == "Fresh Ginger"][0]
        jaipurfresh_apple = [l for l in lots if l.grn.party.name == "Jaipur Fresh Produce Co." and l.commodity.name == "Shimla Apple"][0]
        hanuman_peas = [l for l in lots if l.grn.party.name == "Hanuman Prasad Farmer" and l.commodity.name == "Green Peas"][0]
        kedia_cauli = [l for l in lots if l.grn.party.name == "Kedia Vegetable Trading" and l.commodity.name == "Cauliflower"][0]

        dn_specs = [
            # DN 1: Sharma Traders (80 days ago) - Partial withdrawal
            {
                'party': sharma_potato.grn.party,
                'days_ago': 80,
                'vehicle': "RJ14 GC 7788",
                'driver': "Rajesh Kumar",
                'transporter': "Shekhawat Cold Logistics",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('500.00'),
                'rate_per_unit': Decimal('0.00'),
                'lines': [
                    {'lot': sharma_potato, 'qty': 150},
                    {'lot': sharma_carrot, 'qty': 100},
                ]
            },
            # DN 2: Sharma Traders (50 days ago) - Full withdrawal of remaining 250 potato
            {
                'party': sharma_potato.grn.party,
                'days_ago': 50,
                'vehicle': "RJ14 GC 9900",
                'driver': "Rajesh Kumar",
                'transporter': "Shekhawat Cold Logistics",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_unit': Decimal('3.00'),
                'lines': [
                    {'lot': sharma_potato, 'qty': 250},
                ]
            },
            # DN 3: GD Foods Pvt Ltd (55 days ago) - Partial withdrawal
            {
                'party': gdfoods_corn.grn.party,
                'days_ago': 55,
                'vehicle': "RJ14 GD 1122",
                'driver': "Suresh Singh",
                'transporter': "Self Transport",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('600.00'),
                'rate_per_unit': Decimal('0.00'),
                'lines': [
                    {'lot': gdfoods_corn, 'qty': 200},
                ]
            },
            # DN 4: Ramu Ram Farmer (60 days ago) - Full withdrawal of 300 potato
            {
                'party': ramuram_potato.grn.party,
                'days_ago': 60,
                'vehicle': "RJ14 TA 5566",
                'driver': "Ramu Ram",
                'transporter': "Tractor Trolley",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_unit': Decimal('2.50'),
                'lines': [
                    {'lot': ramuram_potato, 'qty': 300},
                ]
            },
            # DN 5: Rameshwar Lal & Sons (70 days ago) - Partial withdrawal
            {
                'party': rameshwar_garlic.grn.party,
                'days_ago': 70,
                'vehicle': "RJ14 GB 1122",
                'driver': "Mahesh Lal",
                'transporter': "Shekhawat Cold Logistics",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('450.00'),
                'rate_per_unit': Decimal('0.00'),
                'lines': [
                    {'lot': rameshwar_garlic, 'qty': 150},
                    {'lot': rameshwar_ginger, 'qty': 100},
                ]
            },
            # DN 6: Jaipur Fresh Produce Co. (25 days ago) - Partial withdrawal
            {
                'party': jaipurfresh_apple.grn.party,
                'days_ago': 25,
                'vehicle': "RJ14 GE 3344",
                'driver': "Virender Sharma",
                'transporter': "City Tempo",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_unit': Decimal('3.50'),
                'lines': [
                    {'lot': jaipurfresh_apple, 'qty': 200},
                ]
            },
            # DN 7: Hanuman Prasad Farmer (10 days ago) - Full withdrawal of 280 green peas
            {
                'party': hanuman_peas.grn.party,
                'days_ago': 10,
                'vehicle': "RJ14 TA 8899",
                'driver': "Hanuman Prasad",
                'transporter': "Tractor Trolley",
                'mode': ChargeMode.FLAT,
                'charge': Decimal('500.00'),
                'rate_per_unit': Decimal('0.00'),
                'lines': [
                    {'lot': hanuman_peas, 'qty': 280},
                ]
            },
            # DN 8: Kedia Vegetable Trading (15 days ago) - Partial withdrawal
            {
                'party': kedia_cauli.grn.party,
                'days_ago': 15,
                'vehicle': "RJ14 GE 6677",
                'driver': "Dinesh Kedia",
                'transporter': "City Tempo",
                'mode': ChargeMode.PER_UNIT,
                'charge': Decimal('0.00'),
                'rate_per_unit': Decimal('3.00'),
                'lines': [
                    {'lot': kedia_cauli, 'qty': 150},
                ]
            },
        ]

        dns = []
        for spec in dn_specs:
            dispatch_date = today - timedelta(days=spec['days_ago'])
            line_dicts = [{'lot_id': line['lot'].id, 'qty': line['qty']} for line in spec['lines']]
            dn = create_delivery_note(
                facility_id=facility.id,
                party_id=spec['party'].id,
                dispatch_date=dispatch_date,
                vehicle_number=spec['vehicle'],
                driver_name=spec['driver'],
                transporter=spec['transporter'],
                remarks="Dispatch completed cleanly",
                loading_charge=spec['charge'],
                loading_unloading_rate_per_unit=spec['rate_per_unit'],
                loading_charge_mode=spec['mode'],
                status=DeliveryNote.Status.POSTED,
                lines=line_dicts
            )
            dns.append(dn)
        return dns

    def _create_invoices_and_payments(self, facility: Facility, parties: list[Party], today) -> list[Invoice]:
        party_map = {p.name: p for p in parties}
        target_parties = [
            party_map["Sharma Traders"],
            party_map["GD Foods Pvt Ltd"],
            party_map["Ramu Ram Farmer"],
            party_map["Rameshwar Lal & Sons"],
        ]

        generated_invoices = []
        for p in target_parties:
            invs = generate_invoices_for_uninvoiced_deliveries(
                facility_id=facility.id,
                party_id=p.id
            )
            for inv in invs:
                posted_inv = post_invoice(invoice_id=inv.id)
                generated_invoices.append(posted_inv)

        inv_sharma = [inv for inv in generated_invoices if inv.party.name == "Sharma Traders"][0]
        inv_gdfoods = [inv for inv in generated_invoices if inv.party.name == "GD Foods Pvt Ltd"][0]
        inv_rameshwar = [inv for inv in generated_invoices if inv.party.name == "Rameshwar Lal & Sons"][0]

        # 1. Sharma Traders: PAID
        record_payment(
            invoice_id=inv_sharma.id,
            amount=inv_sharma.total_amount,
            payment_date=today - timedelta(days=45),
            method=Payment.Method.BANK_TRANSFER,
            reference="NEFT-RTGS-998811",
            notes="Full invoice payment received via NEFT"
        )

        # 2. GD Foods Pvt Ltd: PARTIAL (50%)
        partial_amt = (inv_gdfoods.total_amount / Decimal('2.00')).quantize(Decimal('0.01'))
        record_payment(
            invoice_id=inv_gdfoods.id,
            amount=partial_amt,
            payment_date=today - timedelta(days=40),
            method=Payment.Method.CHEQUE,
            reference="CHQ-445566",
            notes="50% advance payment cheque"
        )

        # 3. Ramu Ram Farmer: UNPAID (No payment recorded)

        # 4. Rameshwar Lal & Sons: PAID
        record_payment(
            invoice_id=inv_rameshwar.id,
            amount=inv_rameshwar.total_amount,
            payment_date=today - timedelta(days=60),
            method=Payment.Method.CASH,
            reference="CASH-REC-001",
            notes="Full payment received in cash"
        )

        return generated_invoices

    def _print_summary(self, summary: dict):
        facility = summary['facility']
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=================================================="))
        self.stdout.write(self.style.SUCCESS(" DEMO DATASET SEEDED SUCCESSFULLY"))
        self.stdout.write(self.style.SUCCESS("=================================================="))
        self.stdout.write(f"Facility Name : {facility.name} ({facility.code})")
        self.stdout.write(f"GSTIN         : {facility.gstin}")
        self.stdout.write(f"Address       : {facility.address}")
        self.stdout.write("--------------------------------------------------")
        self.stdout.write(self.style.HTTP_INFO("Entity Counts:"))
        self.stdout.write(f"  - Facilities         : 1")
        self.stdout.write(f"  - Location Chambers  : {summary['chambers_count']}")
        self.stdout.write(f"  - Location Floors    : {summary['floors_count']}")
        self.stdout.write(f"  - Location Blocks    : {summary['blocks_count']}")
        self.stdout.write(f"  - Commodities        : {summary['commodities_count']}")
        self.stdout.write(f"  - Parties            : {summary['parties_count']}")
        self.stdout.write(f"  - Goods Receipt Notes: {summary['grns_count']}")
        self.stdout.write(f"  - Lots Created       : {summary['lots_count']}")
        self.stdout.write(f"  - Delivery Notes     : {summary['dns_count']}")
        self.stdout.write(f"  - Invoices Generated : {len(summary['invoices'])}")
        self.stdout.write("--------------------------------------------------")
        self.stdout.write(self.style.HTTP_INFO("Sample Invoices:"))
        for inv in summary['invoices']:
            inv.refresh_from_db()
            st = inv.payment_status
            if st == 'PAID':
                status_text = self.style.SUCCESS(f"[{st}]")
            elif st == 'PARTIAL':
                status_text = self.style.WARNING(f"[{st}]")
            else:
                status_text = self.style.ERROR(f"[{st}]")

            self.stdout.write(
                f"  Invoice #{inv.invoice_number:<12} | Party: {inv.party.name:<24} | "
                f"Total: Rs.{inv.total_amount:>9.2f} | Status: {status_text}"
            )
        self.stdout.write(self.style.SUCCESS("=================================================="))
