from django.db.models import QuerySet
from django.core.exceptions import ObjectDoesNotExist
from .models import Commodity, GRN, Lot

def get_commodities_list(facility_id: int, is_active: bool = None) -> QuerySet[Commodity]:
    """
    Fetch all commodities for a facility.
    """
    qs = Commodity.objects.filter(facility_id=facility_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs.order_by('name')


def get_commodity_by_id(commodity_id: int) -> Commodity:
    """
    Fetch a commodity by ID.
    """
    return Commodity.objects.get(pk=commodity_id)


def get_grns_list(facility_id: int, party_id: int = None, status: str = None) -> QuerySet[GRN]:
    """
    Fetch GRNs for a facility with optional party and status filters.
    """
    qs = GRN.objects.filter(facility_id=facility_id).select_related('facility', 'party').prefetch_related('lots__commodity')
    if party_id:
        qs = qs.filter(party_id=party_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by('-receipt_date', '-id')


def get_grn_by_id(grn_id: int) -> GRN:
    """
    Fetch a GRN by ID with preloaded lots and party details.
    """
    return GRN.objects.select_related('facility', 'party').prefetch_related('lots__commodity').get(pk=grn_id)


def get_lots_list(
    facility_id: int,
    party_id: int = None,
    commodity_id: int = None,
    chamber: str = None,
    in_stock_only: bool = False
) -> QuerySet[Lot]:
    """
    Fetch lots for a facility with optional filters.
    """
    qs = Lot.objects.filter(facility_id=facility_id).select_related('grn', 'grn__party', 'commodity')
    
    if party_id:
        qs = qs.filter(grn__party_id=party_id)
    if commodity_id:
        qs = qs.filter(commodity_id=commodity_id)
    if chamber:
        qs = qs.filter(chamber__iexact=chamber)
    if in_stock_only:
        qs = qs.filter(remaining_qty__gt=0)

    return qs.order_by('-inward_date', '-id')


def get_lot_by_id(lot_id: int) -> Lot:
    """
    Fetch a lot by ID.
    """
    return Lot.objects.select_related('grn', 'grn__party', 'commodity').get(pk=lot_id)
