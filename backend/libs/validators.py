from django.core.validators import RegexValidator

gstin_validator = RegexValidator(
    regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
    message="Enter a valid 15-character GSTIN (e.g. 27ABCDE1234F1Z5)."
)
