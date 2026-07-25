from django.db import models
from simple_history.models import HistoricalRecords
from apps.facilities.models import Facility
from apps.parties.models import Party
from apps.inventory.models import Lot


class DeliveryNote(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        POSTED = 'POSTED', 'Posted'
        CANCELLED = 'CANCELLED', 'Cancelled'

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='delivery_notes')
    dn_number = models.CharField(max_length=100, unique=True)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='delivery_notes')
    dispatch_date = models.DateField()
    vehicle_number = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    transporter = models.CharField(max_length=255, blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    pdf_file = models.FileField(upload_to='delivery_notes/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Delivery Note"
        verbose_name_plural = "Delivery Notes"

    def __str__(self):
        return f"DN #{self.dn_number} - {self.party.name}"


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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Delivery Line"
        verbose_name_plural = "Delivery Lines"

    def __str__(self):
        return f"DN #{self.delivery_note.dn_number} - Lot {self.lot.lot_number} ({self.qty})"
