from django.contrib import admin
from .models import Floor, Chamber


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'facility', 'sort_order', 'is_active', 'created_at')
    list_filter = ('facility', 'is_active')
    search_fields = ('name',)


@admin.register(Chamber)
class ChamberAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'floor', 'sort_order', 'capacity_bags', 'is_active', 'created_at')
    list_filter = ('floor__facility', 'floor', 'is_active')
    search_fields = ('name', 'floor__name')
