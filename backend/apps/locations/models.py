from django.db import models
from apps.facilities.models import Facility


class Floor(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='floors')
    name = models.CharField(max_length=50)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('facility', 'name')
        ordering = ('sort_order', 'name')

    def __str__(self):
        return f"{self.facility.name} - {self.name}"


class Chamber(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='chambers')
    name = models.CharField(max_length=50)
    sort_order = models.PositiveIntegerField(default=0)
    capacity_bags = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('floor', 'name')
        ordering = ('sort_order', 'name')

    @property
    def facility_id(self) -> int:
        return self.floor.facility_id

    def __str__(self):
        return f"{self.floor.name} / {self.name}"
