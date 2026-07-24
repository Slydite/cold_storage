from django.db.models import QuerySet
from .models import DeliveryNote


def get_delivery_notes_list(facility_id: int, party_id: int = None, status: str = None) -> QuerySet[DeliveryNote]:
    """
    Fetch Delivery Notes for a facility with optional party and status filters.
    Optimized with select_related and prefetch_related to avoid N+1 queries.
    """
    qs = DeliveryNote.objects.filter(facility_id=facility_id).select_related('facility', 'party').prefetch_related('lines__lot__commodity')
    if party_id:
        qs = qs.filter(party_id=party_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by('-dispatch_date', '-id')


def get_delivery_note_by_id(dn_id: int) -> DeliveryNote:
    """
    Fetch a Delivery Note by ID with preloaded party, facility, and line details.
    """
    return DeliveryNote.objects.select_related('facility', 'party').prefetch_related('lines__lot__commodity').get(pk=dn_id)
