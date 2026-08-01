from django.db import models
from simple_history.models import HistoricalRecords
from apps.facilities.models import Facility
from libs.validators import gstin_validator
from libs.fiscal import state_code_from_gstin


class Party(models.Model):
    class PartyType(models.TextChoices):
        DEPOSITOR = 'DEPOSITOR', 'Depositor/Customer'
        VENDOR = 'VENDOR', 'Vendor'
        TRANSPORTER = 'TRANSPORTER', 'Transporter'

    class GstRegistrationType(models.TextChoices):
        REGULAR = 'REGULAR', 'Regular'
        COMPOSITION = 'COMPOSITION', 'Composition'
        UNREGISTERED = 'UNREGISTERED', 'Unregistered'
        CONSUMER = 'CONSUMER', 'Consumer'

    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name='parties')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    type = models.CharField(max_length=50, choices=PartyType.choices)

    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    gstin = models.CharField(max_length=15, blank=True, verbose_name="GSTIN", validators=[gstin_validator])
    is_active = models.BooleanField(default=True)

    # GST registration type: default UNREGISTERED because historically only ~18%
    # of this business's bills carried GST at all.
    gst_registration_type = models.CharField(
        max_length=20,
        choices=GstRegistrationType.choices,
        default=GstRegistrationType.UNREGISTERED,
    )

    # State code derived from GSTIN when blank — informational only, does NOT
    # drive any automatic tax decision.
    state_code = models.CharField(max_length=2, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Parties"
        unique_together = ('facility', 'code')

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.type}"

    def save(self, *args, **kwargs):
        # Auto-populate state_code from GSTIN when blank, so it is never typed twice.
        # Informational only — does NOT drive any automatic tax decision.
        if not self.state_code and self.gstin:
            self.state_code = state_code_from_gstin(self.gstin)
        super().save(*args, **kwargs)
