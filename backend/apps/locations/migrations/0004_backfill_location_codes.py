from django.db import migrations

# Inlined copy of the DEFAULT_PREFIXES map from libs/sequences.py at the time
# this migration was written. Migrations must not import app code that may
# change later, so the relevant bits of the sequence-generation logic are
# duplicated here against historical models.
DEFAULT_PREFIXES = {
    'CHAMBER': 'CHM-',
    'FLOOR': 'FLR-',
    'BLOCK': 'BLK-',
}


def _next_code(Sequence, facility, sequence_type):
    prefix = DEFAULT_PREFIXES[sequence_type]
    seq, _created = Sequence.objects.select_for_update().get_or_create(
        facility=facility,
        sequence_type=sequence_type,
        defaults={'prefix': prefix, 'current_value': 0},
    )
    seq.current_value += 1
    seq.save()
    return f"{seq.prefix}{seq.current_value:06d}"


def backfill_codes(apps, schema_editor):
    Sequence = apps.get_model('inventory', 'Sequence')
    Chamber = apps.get_model('locations', 'Chamber')
    Floor = apps.get_model('locations', 'Floor')
    Block = apps.get_model('locations', 'Block')

    for chamber in Chamber.objects.filter(code__isnull=True).order_by('id'):
        chamber.code = _next_code(Sequence, chamber.facility, 'CHAMBER')
        chamber.save(update_fields=['code'])

    for floor in Floor.objects.filter(code__isnull=True).select_related('chamber').order_by('id'):
        floor.code = _next_code(Sequence, floor.chamber.facility, 'FLOOR')
        floor.save(update_fields=['code'])

    for block in Block.objects.filter(code__isnull=True).select_related('floor__chamber').order_by('id'):
        block.code = _next_code(Sequence, block.floor.chamber.facility, 'BLOCK')
        block.save(update_fields=['code'])


def noop_reverse(apps, schema_editor):
    # Codes are derived data; nothing to reverse.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0003_chamber_code_floor_code_block_code'),
        ('inventory', '0011_grn_loading_charge_invoiced_at_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_codes, noop_reverse),
    ]
