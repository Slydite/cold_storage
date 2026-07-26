from django.contrib import admin
from .models import Chamber, Floor, Block


@admin.register(Chamber)
class ChamberAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'facility', 'sort_order', 'is_active', 'created_at')
    list_filter = ('facility', 'is_active')
    search_fields = ('name',)


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'chamber', 'sort_order', 'is_active', 'created_at')
    list_filter = ('chamber__facility', 'chamber', 'is_active')
    search_fields = ('name', 'chamber__name')


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'floor', 'sort_order', 'capacity_bags', 'is_active', 'created_at')
    list_filter = ('floor__chamber__facility', 'floor__chamber', 'floor', 'is_active')
    search_fields = ('name', 'floor__name', 'floor__chamber__name')

