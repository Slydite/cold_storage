from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Sequence, Commodity, GRN, Lot

@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    list_display = ('facility', 'sequence_type', 'prefix', 'current_value')

@admin.register(Commodity)
class CommodityAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'code', 'facility', 'unit', 'is_active')
    list_filter = ('facility', 'is_active')
    search_fields = ('name', 'code')

@admin.register(GRN)
class GRNAdmin(SimpleHistoryAdmin):
    list_display = ('grn_number', 'party', 'facility', 'receipt_date', 'status')
    list_filter = ('facility', 'status', 'receipt_date')
    search_fields = ('grn_number', 'party__name', 'vehicle_number')

@admin.register(Lot)
class LotAdmin(SimpleHistoryAdmin):
    list_display = ('lot_number', 'grn', 'commodity', 'chamber', 'remaining_qty', 'initial_qty')
    list_filter = ('facility', 'commodity', 'chamber')
    search_fields = ('lot_number', 'grn__grn_number')
