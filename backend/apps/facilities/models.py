from decimal import Decimal

from django.db import models
from libs.validators import gstin_validator
from libs.fiscal import state_code_from_gstin


class Facility(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    gstin = models.CharField(max_length=15, blank=True, verbose_name="GSTIN", validators=[gstin_validator])
    phone = models.CharField(max_length=20, blank=True)
    factory_phone = models.CharField(max_length=20, blank=True)
    bank_account_no = models.CharField(max_length=40, blank=True)
    bank_ifsc = models.CharField(max_length=20, blank=True)
    terms_and_conditions = models.TextField(blank=True)

    # State code derived from GSTIN when blank — informational only, does NOT
    # drive any automatic tax decision.
    state_code = models.CharField(max_length=2, blank=True)

    # Tax rate applied when invoices are generated without explicit rates.
    # Split evenly across CGST/SGST at generation time; the owner can override
    # per invoice while it is still a DRAFT.
    #
    # The correct value depends on what this facility actually stores —
    # storage of agricultural produce is largely exempt — and must be
    # confirmed with the business's CA. The default here preserves prior
    # behaviour; it is not a recommendation.
    default_gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name_plural = "Facilities"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        # Auto-populate state_code from GSTIN when blank, so it is never typed twice.
        # Informational only — does NOT drive any automatic tax decision.
        if not self.state_code and self.gstin:
            self.state_code = state_code_from_gstin(self.gstin)
        super().save(*args, **kwargs)
