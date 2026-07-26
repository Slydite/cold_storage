from django.db.models import QuerySet
from .models import DeliveryNote, DeliveryLine


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


def get_uninvoiced_delivery_lines(
    *,
    facility_id: int,
    party_id: int | None = None,
    lot_ids: list[int] | None = None
) -> QuerySet[DeliveryLine]:
    """
    Fetch lines from POSTED delivery notes in a facility that have not yet been invoiced.
    CRITICAL: Only lines from POSTED DeliveryNotes are billable.
    """
    qs = DeliveryLine.objects.filter(
        delivery_note__facility_id=facility_id,
        delivery_note__status=DeliveryNote.Status.POSTED,
        invoiced_at__isnull=True
    ).select_related(
        'lot',
        'lot__commodity',
        'delivery_note',
        'delivery_note__party'
    )
    if party_id is not None:
        qs = qs.filter(delivery_note__party_id=party_id)
    if lot_ids is not None:
        qs = qs.filter(lot_id__in=lot_ids)
    return qs.order_by('delivery_note__dispatch_date', 'id')

