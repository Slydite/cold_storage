from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.core.exceptions import ValidationError
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

    class DocumentType(models.TextChoices):
        TAX_INVOICE = 'TAX_INVOICE', 'Tax Invoice'
        BILL_OF_SUPPLY = 'BILL_OF_SUPPLY', 'Bill of Supply'

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

    # --- Financial Year (GST Rule 46(b): serials must restart each FY) ---
    financial_year = models.CharField(max_length=7, blank=True, db_index=True)

    # --- Amounts ---
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Flat discount (s.15(3)(a) CGST Act: reduces taxable value)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_reason = models.CharField(max_length=255, blank=True)

    # taxable_value = subtotal - discount_amount; stored so PDF/exporter always agree
    taxable_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # --- Tax: owner enters these manually; we do NOT auto-derive intra/inter-state ---
    # Compatibility: legacy gst_rate / gst_amount kept for existing rows.
    # gst_amount is always the SUM of the three component amounts below.
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Three independent GST component rates (entered by the owner)
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Three independent GST component amounts (taxable_value * rate / 100, ROUND_HALF_UP)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Place of supply (2-letter state code, informational for now)
    place_of_supply = models.CharField(max_length=2, blank=True)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # --- Document type (Tax Invoice vs Bill of Supply) ---
    # NOTE: The default is derived from whether tax is present, but the owner
    # is in charge of the tax position and can override this field.  The code
    # implements a mechanism — it does NOT give tax advice.  Confirm the correct
    # document type with the business's CA before filing.
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.TAX_INVOICE,
    )
    is_reverse_charge = models.BooleanField(default=False)
    exemption_reason = models.CharField(max_length=255, blank=True)

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

    def clean(self):
        super().clean()
        # Validate discount
        if self.discount_amount < Decimal('0.00'):
            raise ValidationError({'discount_amount': 'Discount amount cannot be negative.'})
        if self.discount_amount > self.subtotal:
            raise ValidationError({'discount_amount': 'Discount amount cannot exceed subtotal.'})


class InvoiceLine(models.Model):
    class ChargeType(models.TextChoices):
        RENT = 'RENT', 'Rent'
        LOADING_UNLOADING = 'LOADING_UNLOADING', 'Loading/Unloading'
        TRANSPORT = 'TRANSPORT', 'Transport'
        WEIGHING = 'WEIGHING', 'Weighing'
        OTHER = 'OTHER', 'Other'

    # Mapping from charge_type to default SAC code.
    # IMPORTANT: These SAC codes MUST be confirmed with the CA before the first
    # GST filing. Using a wrong SAC code is a compliance error.
    DEFAULT_SAC_CODES = {
        ChargeType.RENT: '996729',           # General warehousing and storage services
        ChargeType.LOADING_UNLOADING: '998619',  # Other support services to agriculture
        ChargeType.TRANSPORT: '',            # Confirm with CA
        ChargeType.WEIGHING: '',             # Confirm with CA
        ChargeType.OTHER: '',                # Confirm with CA
    }

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

    # Ledger / accounting classification
    charge_type = models.CharField(
        max_length=20,
        choices=ChargeType.choices,
        default=ChargeType.RENT,
    )
    sac_code = models.CharField(max_length=10, blank=True)

    # Rent lines must record the storage period billed so the customer can audit
    period_from = models.DateField(null=True, blank=True)
    period_to = models.DateField(null=True, blank=True)

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
