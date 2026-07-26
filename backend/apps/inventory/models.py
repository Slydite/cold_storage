from decimal import Decimal
from django.db import models
from simple_history.models import HistoricalRecords
from apps.facilities.models import Facility
from apps.parties.models import Party

class Sequence(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='sequences')
    sequence_type = models.CharField(max_length=50)  # e.g., 'GRN', 'DN', 'INV'
    prefix = models.CharField(max_length=20, default='', blank=True)
    current_value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('facility', 'sequence_type')

    def __str__(self):
        return f"{self.facility.code} - {self.sequence_type}: {self.prefix}{self.current_value}"


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

    NOTE on loading_charge vs loading_unloading_rate_per_bag:
    loading_charge is the flat total amount actually charged.
    loading_unloading_rate_per_bag records the agreed per-bag rate captured from the paper form.
    Reconciling the two (total = rate * bags) is deliberately NOT enforced in v1 because the paper
    process allows a negotiated flat override.

    NOTE on preservation_rate_per_bag_per_month:
    Captured here at intake for documentary purposes to match the paper form.
    Billing does NOT read this field — apps.billing resolves rates from RateCard (including per-party overrides)
    at run time. This field is solely the documentary record of what was written on the receipt.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        POSTED = 'POSTED', 'Posted'
        CANCELLED = 'CANCELLED', 'Cancelled'

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='grns')
    grn_number = models.CharField(max_length=100, unique=True)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='grns')
    receipt_date = models.DateField()
    vehicle_number = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    loading_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.POSTED)

    bill_no = models.CharField(max_length=50, blank=True)
    bilty_no = models.CharField(max_length=50, blank=True)
    transporter = models.CharField(max_length=255, blank=True)
    preservation_rate_per_bag_per_month = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    loading_unloading_rate_per_bag = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    inward_time = models.TimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Goods Receipt Note"
        verbose_name_plural = "Goods Receipt Notes"

    def __str__(self):
        return f"GRN #{self.grn_number} - {self.party.name}"


class Lot(models.Model):
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
    unit_weight = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Weight in KG
    rent_rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    inward_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Lots"

    def __str__(self):
        return f"Lot {self.lot_number} ({self.commodity.name}) - Qty: {self.remaining_qty}/{self.initial_qty}"
