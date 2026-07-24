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
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.POSTED)

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

    initial_qty = models.PositiveIntegerField()
    remaining_qty = models.PositiveIntegerField()
    unit_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Weight in KG
    rent_rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    inward_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Lots"

    def __str__(self):
        return f"Lot {self.lot_number} ({self.commodity.name}) - Qty: {self.remaining_qty}/{self.initial_qty}"
