from decimal import Decimal
from django.db import models
from simple_history.models import HistoricalRecords
from apps.facilities.models import Facility
from apps.parties.models import Party


class PaymentStatus(models.TextChoices):
    UNPAID = 'UNPAID', 'Unpaid'
    PARTIAL = 'PARTIAL', 'Partial'
    PAID = 'PAID', 'Paid'


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        POSTED = 'POSTED', 'Posted'
        CANCELLED = 'CANCELLED', 'Cancelled'

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=100)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='invoices')
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
    last_emailed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Invoice"
        # Sequences are per-facility (see libs.sequences); scope the
        # uniqueness constraint to match, same reasoning as GRN.grn_number.
        unique_together = ('facility', 'invoice_number')

    def __str__(self):
        return f"Invoice {self.invoice_number} ({self.party.name}) [{self.status}]"

    @property
    def amount_paid(self) -> Decimal:
        paid = sum((p.amount for p in self.payments.all()), Decimal('0.00'))
        return paid.quantize(Decimal('0.01'))

    @property
    def amount_due(self) -> Decimal:
        # Decision: If amount_paid > total_amount (overpayment), amount_due is clamped to Decimal('0.00')
        # rather than returning a negative amount, since a negative "due" would read as a credit balance
        # which the system does not currently model.
        due = self.total_amount - self.amount_paid
        if due < Decimal('0.00'):
            return Decimal('0.00')
        return due.quantize(Decimal('0.01'))

    @property
    def payment_status(self) -> str:
        paid = self.amount_paid
        if paid == Decimal('0.00'):
            return PaymentStatus.UNPAID
        elif paid < self.total_amount:
            return PaymentStatus.PARTIAL
        else:
            return PaymentStatus.PAID


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Snapshot of the qty/unit/rate a rent or per-unit charge line was billed
    # at, so the customer can verify the amount. Null for flat charge lines,
    # which have no per-unit rate to show. Deliberately stored here rather
    # than re-derived from the Lot/GRN/DN at display time: those can change
    # after the invoice is generated, but what was actually billed must not.
    quantity = models.PositiveIntegerField(null=True, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"InvoiceLine #{self.id} for {self.invoice.invoice_number}: {self.amount}"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = 'CASH', 'Cash'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
        CHEQUE = 'CHEQUE', 'Cheque'
        UPI = 'UPI', 'UPI'
        OTHER = 'OTHER', 'Other'

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.CASH)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ('-payment_date', '-id')

    def __str__(self):
        return f"Payment #{self.id} (₹{self.amount}) for Invoice {self.invoice.invoice_number}"

