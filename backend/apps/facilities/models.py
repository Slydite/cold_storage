from django.db import models
from libs.validators import gstin_validator

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name_plural = "Facilities"

    def __str__(self):
        return f"{self.name} ({self.code})"
