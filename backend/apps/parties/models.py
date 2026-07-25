from django.core.validators import RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords
from apps.facilities.models import Facility

gstin_validator = RegexValidator(
    regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
    message="Enter a valid 15-character GSTIN (e.g. 27ABCDE1234F1Z5)."
)

class Party(models.Model):
    class PartyType(models.TextChoices):
        DEPOSITOR = 'DEPOSITOR', 'Depositor/Customer'
        VENDOR = 'VENDOR', 'Vendor'
        TRANSPORTER = 'TRANSPORTER', 'Transporter'

    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name='parties')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    type = models.CharField(max_length=50, choices=PartyType.choices)
    
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    gstin = models.CharField(max_length=15, blank=True, verbose_name="GSTIN", validators=[gstin_validator])
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Parties"
        unique_together = ('facility', 'code')

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.type}"
