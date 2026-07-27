from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ('description', 'amount', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('amount', 'payment_date', 'method', 'reference', 'notes', 'created_at')


@admin.register(Invoice)
class InvoiceAdmin(SimpleHistoryAdmin):
    list_display = ('invoice_number', 'party', 'status', 'total_amount', 'amount_paid', 'amount_due', 'payment_status', 'invoice_date')
    list_filter = ('facility', 'status', 'invoice_date')
    search_fields = ('invoice_number', 'party__name')
    inlines = [InvoiceLineInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'invoice', 'amount', 'payment_date', 'method', 'reference', 'created_at')
    list_filter = ('method', 'payment_date')
    search_fields = ('invoice__invoice_number', 'reference')

