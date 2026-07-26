from django.db import models

class ChargeMode(models.TextChoices):
    FLAT = 'FLAT', 'Flat'
    PER_UNIT = 'PER_UNIT', 'Per Unit'
