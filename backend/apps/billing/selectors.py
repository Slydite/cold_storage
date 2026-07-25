from django.db.models import QuerySet
from .models import RateCard, RentRun


def get_rate_cards_list(
    facility_id: int,
    commodity_id: int = None,
    party_id: int | str = None,
    is_default: bool = None,
    is_active: bool = None
) -> QuerySet[RateCard]:
    """
    Fetch all rate cards for a facility with optional commodity, party, is_default, and is_active filters.
    """
    qs = RateCard.objects.filter(facility_id=facility_id).select_related('facility', 'commodity', 'party')
    if commodity_id:
        qs = qs.filter(commodity_id=commodity_id)
    if is_default:
        qs = qs.filter(party__isnull=True)
    elif party_id is not None:
        if str(party_id).lower() == 'null':
            qs = qs.filter(party__isnull=True)
        else:
            qs = qs.filter(party_id=int(party_id))
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs.order_by('-effective_from')


def get_rate_card_by_id(rate_card_id: int) -> RateCard:
    """
    Fetch a single RateCard by ID.
    """
    return RateCard.objects.select_related('facility', 'commodity', 'party').get(pk=rate_card_id)


def get_rent_runs_list(facility_id: int, status: str = None) -> QuerySet[RentRun]:
    """
    Fetch rent runs for a facility with preloaded lines, lots, commodities, and parties.
    """
    qs = RentRun.objects.filter(facility_id=facility_id).select_related('facility', 'party', 'commodity').prefetch_related(
        'lines__lot',
        'lines__party',
        'lines__lot__commodity'
    )
    if status:
        qs = qs.filter(status=status)
    return qs.order_by('-period_end', '-id')


def get_rent_run_by_id(rent_run_id: int) -> RentRun:
    """
    Fetch a single RentRun by ID with preloaded lines, lots, commodities, and parties.
    """
    return RentRun.objects.select_related('facility', 'party', 'commodity').prefetch_related(
        'lines__lot',
        'lines__party',
        'lines__lot__commodity'
    ).get(pk=rent_run_id)

