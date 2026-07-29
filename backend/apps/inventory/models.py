from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from simple_history.models import HistoricalRecords
from apps.facilities.models import Facility
from apps.parties.models import Party
from libs.choices import ChargeMode

class Sequence(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True, related_name='sequences')
    sequence_type = models.CharField(max_length=50)  # e.g., 'GRN', 'DN', 'INV', 'PARTY', 'FACILITY'
    prefix = models.CharField(max_length=20, default='', blank=True)
    current_value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('facility', 'sequence_type')

    def __str__(self):
        fac_code = self.facility.code if self.facility else "GLOBAL"
        return f"{fac_code} - {self.sequence_type}: {self.prefix}{self.current_value}"



class Commodity(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='commodities')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    unit = models.CharField(max_length=50, default='BAGS')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Commodities"
        unique_together = ('facility', 'code')

    def __str__(self):
        return f"{self.name} ({self.code})"


class GRN(models.Model):
    """
    Goods Receipt Note model matching paper GRN ("रसीद") form.

    NOTE on loading_charge vs loading_unloading_rate_per_bag & loading_charge_mode:
    loading_charge is the FLAT total amount when mode is FLAT.
    loading_unloading_rate_per_bag is the PER_UNIT rate when mode is PER_UNIT.
    computed_loading_charge() derives the actual loading charge dynamically.

    NOTE on preservation_rate_per_bag_per_month:
    Captured here at intake for documentary purposes to match the paper form.
    Billing does NOT read this field — the negotiated rent rate lives on Lot.rent_rate_per_unit
    and is what apps.billing actually uses at invoicing time. This field is solely the
    documentary record of what was written on the receipt.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        POSTED = 'POSTED', 'Posted'
        CANCELLED = 'CANCELLED', 'Cancelled'

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='grns')
    grn_number = models.CharField(max_length=100)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='grns')
    receipt_date = models.DateField()
    vehicle_number = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    loading_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    loading_unloading_rate_per_bag = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    loading_charge_mode = models.CharField(max_length=20, choices=ChargeMode.choices, default=ChargeMode.FLAT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.POSTED)

    bill_no = models.CharField(max_length=50, blank=True)
    bilty_no = models.CharField(max_length=50, blank=True)
    transporter = models.CharField(max_length=255, blank=True)
    preservation_rate_per_bag_per_month = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    inward_time = models.TimeField(null=True, blank=True)
    loading_charge_invoiced_at = models.DateTimeField(null=True, blank=True)
    last_emailed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Goods Receipt Note"
        verbose_name_plural = "Goods Receipt Notes"
        # Sequences are per-facility (see libs.sequences), so grn_number alone
        # is not globally unique - a second facility's first GRN is
        # "GRN-000001" too. Scope the constraint to match.
        unique_together = ('facility', 'grn_number')

    def __str__(self):
        return f"GRN #{self.grn_number} - {self.party.name}"

    def computed_loading_charge(self) -> Decimal:
        if self.loading_charge_mode == ChargeMode.PER_UNIT:
            total_units = Decimal(sum(lot.initial_qty for lot in self.lots.all()))
            amount = self.loading_unloading_rate_per_bag * total_units
            return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return self.loading_charge.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class Lot(models.Model):
    class UnitType(models.TextChoices):
        BAGS = 'BAGS', 'Bags'
        BOXES = 'BOXES', 'Boxes'
        CRATES = 'CRATES', 'Crates'
        PACKETS = 'PACKETS', 'Packets'
        LOOSE = 'LOOSE', 'Loose'

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='lots')
    grn = models.ForeignKey(GRN, on_delete=models.CASCADE, related_name='lots')
    commodity = models.ForeignKey(Commodity, on_delete=models.PROTECT, related_name='lots')
    lot_number = models.CharField(max_length=100)
    
    chamber = models.CharField(max_length=50, blank=True)
    floor = models.CharField(max_length=50, blank=True)
    rack = models.CharField(max_length=50, blank=True)

    chamber_ref = models.ForeignKey('locations.Chamber', null=True, blank=True, on_delete=models.PROTECT, related_name='lots')
    floor_ref = models.ForeignKey('locations.Floor', null=True, blank=True, on_delete=models.PROTECT, related_name='lots')
    block_ref = models.ForeignKey('locations.Block', null=True, blank=True, on_delete=models.PROTECT, related_name='lots')

    special_remarks = models.CharField(max_length=255, blank=True)  # Paper form's "विशेष विवरण" column

    initial_qty = models.PositiveIntegerField()
    remaining_qty = models.PositiveIntegerField()
    unit = models.CharField(max_length=20, default=UnitType.BAGS)
    unit_weight = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Weight in KG
    rent_rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Negotiated rate per unit per month agreed with party at intake. Used by billing as single source of truth.

    inward_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Lots"
        unique_together = ('facility', 'lot_number')

    def __str__(self):
        return f"Lot {self.lot_number} ({self.commodity.name}) - Qty: {self.remaining_qty}/{self.initial_qty}"

    @property
    def location_display(self) -> str:
        parts = []
        c_name = self.chamber_ref.name if self.chamber_ref else self.chamber.strip()
        f_name = self.floor_ref.name if self.floor_ref else self.floor.strip()
        b_name = self.block_ref.name if self.block_ref else (self.rack.strip() if self.rack else '')

        if c_name:
            parts.append(c_name if any(c_name.lower().startswith(p) for p in ['chamber', 'कक्ष']) else f"Chamber {c_name}")
        if f_name:
            parts.append(f_name if any(f_name.lower().startswith(p) for p in ['floor', 'मंजिल']) else f"Floor {f_name}")
        if b_name:
            parts.append(b_name if any(b_name.lower().startswith(p) for p in ['block', 'rack']) else f"Block {b_name}")

        if parts:
            return " / ".join(parts)
        return "—"

