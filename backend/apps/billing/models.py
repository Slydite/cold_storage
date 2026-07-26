from django.db import models

# apps.billing contains no database models under the withdrawal-based billing architecture.
# All rent calculations are pure functions in services.py based on Lot.rent_rate_per_unit
# and DeliveryNote dispatch dates.
