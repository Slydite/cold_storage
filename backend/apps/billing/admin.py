from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import RateCard, RentRun, RentRunLine


@admin.register(RateCard)
class RateCardAdmin(SimpleHistoryAdmin):
    list_display = ('commodity', 'party', 'facility', 'weight_category', 'rate_per_bag_per_month', 'effective_from', 'is_active')
    list_filter = ('facility', 'party', 'weight_category', 'is_active', 'effective_from')
    search_fields = ('commodity__name', 'commodity__code', 'party__name')


class RentRunLineInline(admin.TabularInline):
    model = RentRunLine
    extra = 0
    readonly_fields = (
        'lot',
        'party',
        'qty',
        'weight_category',
        'rate_per_bag_per_month',
        'days_stored',
        'amount',
        'created_at',
        'updated_at'
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RentRun)
class RentRunAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'facility', 'period_start', 'period_end', 'party', 'commodity', 'chamber', 'min_billing_days', 'status', 'run_date')
    list_filter = ('facility', 'party', 'commodity', 'status', 'period_start')
    search_fields = ('facility__name', 'facility__code', 'party__name', 'commodity__name')
    inlines = [RentRunLineInline]

