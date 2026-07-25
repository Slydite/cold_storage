from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Invoice, InvoiceLine


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ('description', 'rent_run_line', 'amount', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(SimpleHistoryAdmin):
    list_display = ('invoice_number', 'party', 'status', 'total_amount', 'invoice_date')
    list_filter = ('facility', 'status', 'invoice_date')
    search_fields = ('invoice_number', 'party__name')
    inlines = [InvoiceLineInline]
