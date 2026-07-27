from django.db.models import QuerySet
from .models import Invoice


def get_invoices_list(
    facility_id: int,
    party_id: int = None,
    status: str = None,
    payment_status: str = None
) -> list[Invoice]:
    """
    Fetch all invoices for a facility with optional party_id, status, and payment_status filters.
    Preloads facility, party, lines, and payments.
    Ordered by -invoice_date, -id.
    """
    qs = Invoice.objects.filter(facility_id=facility_id).select_related(
        'facility', 'party'
    ).prefetch_related('lines', 'payments')

    if party_id:
        qs = qs.filter(party_id=party_id)
    if status:
        qs = qs.filter(status=status)

    invoices = list(qs.order_by('-invoice_date', '-id'))

    if payment_status:
        invoices = [inv for inv in invoices if inv.payment_status == payment_status]

    return invoices


def get_invoice_by_id(invoice_id: int) -> Invoice:
    """
    Fetch a single Invoice by ID with preloaded facility, party, lines, and payments.
    """
    return Invoice.objects.select_related(
        'facility', 'party'
    ).prefetch_related('lines', 'payments').get(pk=invoice_id)

