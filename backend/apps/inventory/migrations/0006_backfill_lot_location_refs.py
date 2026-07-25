from django.db import migrations

DEFAULT_FLOOR_NAME = "Ground Floor"


def backfill_location_refs(apps, schema_editor):
    """
    Promote Lot's free-text floor/chamber into the locations.Floor/Chamber
    master tables and point the new FKs at them.

    A lot may carry a chamber with no floor (the old model had no hierarchy),
    so those are parented to a per-facility DEFAULT_FLOOR_NAME rather than
    dropped -- losing a lot's physical location would be worse than inventing
    an obviously-named placeholder the operator can rename later.
    """
    Lot = apps.get_model('inventory', 'Lot')
    Floor = apps.get_model('locations', 'Floor')
    Chamber = apps.get_model('locations', 'Chamber')

    lots = Lot.objects.exclude(floor='', chamber='').only(
        'id', 'facility_id', 'floor', 'chamber'
    )

    floor_cache = {}
    chamber_cache = {}

    for lot in lots.iterator():
        floor_name = (lot.floor or '').strip() or DEFAULT_FLOOR_NAME
        chamber_name = (lot.chamber or '').strip()

        floor_key = (lot.facility_id, floor_name)
        floor = floor_cache.get(floor_key)
        if floor is None:
            floor, _ = Floor.objects.get_or_create(
                facility_id=lot.facility_id,
                name=floor_name,
                defaults={'sort_order': 0, 'is_active': True},
            )
            floor_cache[floor_key] = floor

        chamber = None
        if chamber_name:
            chamber_key = (floor.id, chamber_name)
            chamber = chamber_cache.get(chamber_key)
            if chamber is None:
                chamber, _ = Chamber.objects.get_or_create(
                    floor=floor,
                    name=chamber_name,
                    defaults={'sort_order': 0, 'is_active': True},
                )
                chamber_cache[chamber_key] = chamber

        Lot.objects.filter(pk=lot.pk).update(
            floor_ref=floor,
            chamber_ref=chamber,
        )


def unset_location_refs(apps, schema_editor):
    """
    Only clears the FKs. The Floor/Chamber rows created above are intentionally
    left in place: they may have been edited or had new lots attached since,
    and deleting them could cascade away data this migration never created.
    """
    Lot = apps.get_model('inventory', 'Lot')
    Lot.objects.update(floor_ref=None, chamber_ref=None)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_historicallot_chamber_ref_historicallot_floor_ref_and_more'),
        ('locations', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_location_refs, unset_location_refs),
    ]
