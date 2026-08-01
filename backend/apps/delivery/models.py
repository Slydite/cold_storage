from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from simple_history.models import HistoricalRecords
from apps.facilities.models import Facility
from apps.parties.models import Party
from apps.inventory.models import Lot
from libs.choices import ChargeMode


class DeliveryNote(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        POSTED = 'POSTED', 'Posted'
        CANCELLED = 'CANCELLED', 'Cancelled'

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='delivery_notes')
    dn_number = models.CharField(max_length=100)
    # Holds the FAS voucher/lot identifier for records imported from the legacy Access system, and is empty for anything created in this app.
    legacy_ref = models.CharField(max_length=100, blank=True, db_index=True)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='delivery_notes')
    dispatch_date = models.DateField()
    vehicle_number = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    transporter = models.CharField(max_length=255, blank=True)
    remarks = models.TextField(blank=True)
    loading_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    loading_unloading_rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    loading_charge_mode = models.CharField(max_length=20, choices=ChargeMode.choices, default=ChargeMode.FLAT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    loading_charge_invoiced_at = models.DateTimeField(null=True, blank=True)
    last_emailed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Delivery Note"
        verbose_name_plural = "Delivery Notes"
        # Sequences are per-facility (see libs.sequences); scope the
        # uniqueness constraint to match, same reasoning as GRN.grn_number.
        unique_together = ('facility', 'dn_number')

    def __str__(self):
        return f"DN #{self.dn_number} - {self.party.name}"

    def computed_loading_charge(self) -> Decimal:
        if self.loading_charge_mode == ChargeMode.PER_UNIT:
            total_units = Decimal(sum(line.qty for line in self.lines.all()))
            amount = self.loading_unloading_rate_per_unit * total_units
            return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return self.loading_charge.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class DeliveryLine(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='delivery_lines')
    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, related_name='lines')
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, related_name='delivery_lines')
    qty = models.PositiveIntegerField()
    balance_after = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Lot remaining_qty immediately AFTER this line was posted (paper form Balance column). NULL for draft lines."
    )
    invoiced_at = models.DateTimeField(null=True, blank=True)
    invoice_line = models.ForeignKey(
        'invoicing.InvoiceLine',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='delivery_lines'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Delivery Line"
        verbose_name_plural = "Delivery Lines"

    def __str__(self):
        return f"DN #{self.delivery_note.dn_number} - Lot {self.lot.lot_number} ({self.qty})"
