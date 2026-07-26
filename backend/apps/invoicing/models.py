from decimal import Decimal
from django.db import models
from simple_history.models import HistoricalRecords
from apps.facilities.models import Facility
from apps.parties.models import Party
from apps.billing.models import RentRun, RentRunLine


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        POSTED = 'POSTED', 'Posted'
        CANCELLED = 'CANCELLED', 'Cancelled'

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=100, unique=True)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='invoices')
    rent_run = models.ForeignKey(
        RentRun,
        on_delete=models.PROTECT,
        related_name='invoices',
        null=True,
        blank=True
    )
    invoice_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    party_gstin_snapshot = models.CharField(max_length=15, blank=True)
    party_name_snapshot = models.CharField(max_length=255, blank=True)
    party_address_snapshot = models.TextField(blank=True)
    facility_name_snapshot = models.CharField(max_length=255, blank=True)
    facility_address_snapshot = models.TextField(blank=True)
    facility_gstin_snapshot = models.CharField(max_length=15, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Invoice"

    def __str__(self):
        return f"Invoice {self.invoice_number} ({self.party.name}) [{self.status}]"


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=500)
    rent_run_line = models.ForeignKey(
        RentRunLine,
        on_delete=models.PROTECT,
        related_name='invoice_lines',
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"InvoiceLine #{self.id} for {self.invoice.invoice_number}: {self.amount}"
