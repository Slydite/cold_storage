from django.db import models
from django.db.models import Q, UniqueConstraint
from simple_history.models import HistoricalRecords
from apps.facilities.models import Facility
from apps.inventory.models import Commodity, Lot
from apps.parties.models import Party


class RateCard(models.Model):
    class WeightCategory(models.TextChoices):
        KG_20 = 'KG_20', '20 kg bag'
        KG_50 = 'KG_50', '50 kg bag'
        OTHER = 'OTHER', 'Other'

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='rate_cards')
    party = models.ForeignKey(Party, null=True, blank=True, on_delete=models.PROTECT, related_name='rate_cards')
    commodity = models.ForeignKey(Commodity, on_delete=models.PROTECT, related_name='rate_cards')
    weight_category = models.CharField(max_length=20, choices=WeightCategory.choices)
    rate_per_bag_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['facility', 'commodity', 'weight_category', 'effective_from'],
                condition=Q(party__isnull=True),
                name='uniq_default_rate_card'
            ),
            UniqueConstraint(
                fields=['facility', 'party', 'commodity', 'weight_category', 'effective_from'],
                condition=Q(party__isnull=False),
                name='uniq_party_rate_card'
            ),
        ]

    def __str__(self):
        party_str = f" for {self.party.name}" if self.party else " [DEFAULT]"
        return f"{self.commodity.code} / {self.weight_category}{party_str} @ {self.rate_per_bag_per_month} from {self.effective_from}"


class RentRun(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        POSTED = 'POSTED', 'Posted'
        CANCELLED = 'CANCELLED', 'Cancelled'

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='rent_runs')
    period_start = models.DateField()
    period_end = models.DateField()
    party = models.ForeignKey(Party, null=True, blank=True, on_delete=models.PROTECT, related_name='rent_runs')
    commodity = models.ForeignKey(Commodity, null=True, blank=True, on_delete=models.PROTECT, related_name='rent_runs')
    chamber = models.CharField(max_length=50, blank=True, default='')
    min_billing_days = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    run_date = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Rent Run"

    def __str__(self):
        return f"RentRun #{self.id} ({self.facility.code}) - {self.period_start} to {self.period_end} [{self.status}]"


class RentRunLine(models.Model):
    rent_run = models.ForeignKey(RentRun, on_delete=models.CASCADE, related_name='lines')
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, related_name='rent_run_lines')
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='rent_run_lines')

    qty = models.PositiveIntegerField()
    weight_category = models.CharField(max_length=20, choices=RateCard.WeightCategory.choices)
    rate_per_bag_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    days_stored = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('rent_run', 'lot')

    def __str__(self):
        return f"RentRun #{self.rent_run_id} - Lot {self.lot.lot_number}: {self.amount}"

