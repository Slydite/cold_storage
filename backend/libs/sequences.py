from django.db import transaction
from django.core.exceptions import ValidationError
from apps.facilities.models import Facility
from apps.inventory.models import Sequence

DEFAULT_PREFIXES = {
    'PARTY': 'PRT-',
    'COMMODITY': 'CMD-',
    'CHAMBER': 'CHM-',
    'FLOOR': 'FLR-',
    'BLOCK': 'BLK-',
    'FACILITY': 'FAC-',
    'GRN': 'GRN-',
    'DN': 'DN-',
    'INV': 'INV-',
    'LOT': 'LOT-',
}

@transaction.atomic
def get_next_sequence_number(
    facility_id: int = None,
    sequence_type: str = '',
    prefix: str = None,
    facility: Facility = None,
    financial_year: str = '',
) -> str:
    """
    Generate the next sequence number for a given facility and sequence type (e.g. 'GRN', 'DN', 'INV', 'PARTY', 'FACILITY')
    using select_for_update() on the Sequence model inside an atomic transaction.

    When `financial_year` is empty (the default), the format and behaviour are
    **byte-for-byte identical** to the previous version — e.g. GRN-000001, LOT-000001.
    The legacy import depends on this exact format; do not change it.

    When `financial_year` is supplied (e.g. '2026-27'), the counter is scoped to
    that FY and the number is formatted as INV-2026-27-000001 per GST Rule 46(b).
    Only invoice sequences are FY-scoped; all other sequence types keep flat numbering.

    Pass an already-loaded `facility` to skip a redundant lookup when the caller
    has one on hand; otherwise pass `facility_id` and it will be fetched here.
    If both `facility` and `facility_id` are None, a global sequence (facility=None) is used.
    """
    if facility is None and facility_id is not None:
        try:
            facility = Facility.objects.get(pk=facility_id)
        except Facility.DoesNotExist:
            raise ValidationError(f"Facility with ID {facility_id} does not exist.")

    if prefix is not None:
        default_prefix = prefix
    else:
        default_prefix = DEFAULT_PREFIXES.get(sequence_type, f"{sequence_type}-")

    seq, created = Sequence.objects.select_for_update().get_or_create(
        facility=facility,
        sequence_type=sequence_type,
        financial_year=financial_year,
        defaults={'prefix': default_prefix, 'current_value': 0}
    )

    if prefix is not None and seq.prefix != prefix:
        seq.prefix = prefix

    seq.current_value += 1
    seq.save()

    if financial_year:
        # FY-scoped format: INV-2026-27-000001
        return f"{seq.prefix}{financial_year}-{seq.current_value:06d}"
    else:
        # Legacy flat format: GRN-000001
        return f"{seq.prefix}{seq.current_value:06d}"
