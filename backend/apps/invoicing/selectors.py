from django.db.models import QuerySet
from .models import Invoice


def get_invoices_list(
    facility_id: int,
    party_id: int = None,
    status: str = None
) -> QuerySet[Invoice]:
    """
    Fetch all invoices for a facility with optional party_id and status filters.
    Preloads facility, party, rent_run, and lines.
    Ordered by -invoice_date, -id.
    """
    qs = Invoice.objects.filter(facility_id=facility_id).select_related(
        'facility', 'party', 'rent_run'
    ).prefetch_related('lines')

    if party_id:
        qs = qs.filter(party_id=party_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by('-invoice_date', '-id')


def get_invoice_by_id(invoice_id: int) -> Invoice:
    """
    Fetch a single Invoice by ID with preloaded facility, party, rent_run, and lines.
    """
    return Invoice.objects.select_related(
        'facility', 'party', 'rent_run'
    ).prefetch_related('lines').get(pk=invoice_id)
