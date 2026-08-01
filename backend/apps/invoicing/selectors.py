from datetime import date
from django.db.models import QuerySet
from .models import Invoice, Payment


def get_invoices_list(
    facility_id: int,
    party_id: int = None,
    status: str = None,
    payment_status: str = None,
    financial_year: str = None,
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
    if financial_year:
        qs = qs.filter(financial_year=financial_year)

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


def get_payments_list(
    *,
    facility_id: int,
    party_id: int | None = None,
    method: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None
) -> QuerySet:
    """
    Fetch payments list for a facility with optional party_id, method, date_from, and date_to filters.
    Preloads invoice and party to prevent N+1 queries.
    Ordered by -payment_date, -id.
    """
    qs = Payment.objects.filter(invoice__facility_id=facility_id).select_related(
        'invoice', 'invoice__party'
    )

    if party_id:
        qs = qs.filter(invoice__party_id=party_id)
    if method:
        qs = qs.filter(method=method)
    if date_from:
        qs = qs.filter(payment_date__gte=date_from)
    if date_to:
        qs = qs.filter(payment_date__lte=date_to)

    return qs.order_by('-payment_date', '-id')


