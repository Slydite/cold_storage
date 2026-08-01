from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import DeliveryNote, DeliveryLine


@admin.register(DeliveryNote)
class DeliveryNoteAdmin(SimpleHistoryAdmin):
    list_display = ('dn_number', 'party', 'facility', 'dispatch_date', 'status')
    list_filter = ('facility', 'status', 'dispatch_date')
    search_fields = ('dn_number', 'party__name', 'vehicle_number', 'legacy_ref')


@admin.register(DeliveryLine)
class DeliveryLineAdmin(SimpleHistoryAdmin):
    list_display = ('delivery_note', 'lot', 'facility', 'qty')
    list_filter = ('facility',)
    search_fields = ('delivery_note__dn_number', 'lot__lot_number')
