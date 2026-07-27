import django.db.models.deletion
from django.db import migrations, models


def clear_stale_location_data(apps, schema_editor):
    """
    The location hierarchy is being restructured from
    Facility -> Floor -> Chamber to Facility -> Chamber -> Floor -> Block
    (the old Chamber becomes the new Block, and a brand new top-level
    Chamber is introduced above Floor).

    Existing Chamber/Floor rows were created under the OLD hierarchy and are
    semantically invalid under the NEW one (e.g. an old "Chamber" row is
    really what the new model calls a "Block", and it has no facility of
    its own). There is no way to losslessly reinterpret them, so rather than
    leave inconsistent data behind, we clear the FKs pointing at them from
    Lot and delete the old rows outright.

    The project owner has explicitly confirmed all existing location data
    (and indeed all current app data) is disposable test data -- production
    has just 1 floor, 1 GRN, 1 lot, 1 DN and no invoices -- so discarding
    these rows is safe.
    """
    Lot = apps.get_model('inventory', 'Lot')
    Chamber = apps.get_model('locations', 'Chamber')
    Floor = apps.get_model('locations', 'Floor')

    # block_ref does not exist on Lot yet at this point in migration history.
    Lot.objects.update(chamber_ref=None, floor_ref=None)

    Chamber.objects.all().delete()
    Floor.objects.all().delete()

    # Django creates foreign keys as DEFERRABLE INITIALLY DEFERRED, so on
    # PostgreSQL the deletes above only queue trigger events -- they are not
    # checked until commit. The schema operations that follow in this same
    # transaction then fail with "cannot ALTER TABLE ... because it has
    # pending trigger events". Forcing the constraints to be checked now
    # drains that queue so the ALTER TABLEs can proceed.
    #
    # SQLite has no deferred trigger events and does not support the
    # statement, hence the vendor guard. This is why the bug only appeared
    # against production Postgres and not in local development.
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('SET CONSTRAINTS ALL IMMEDIATE')


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0001_initial'),
        ('inventory', '0006_backfill_lot_location_refs'),
        ('facilities', '0003_facility_bank_account_no_facility_bank_ifsc_and_more'),
    ]

    operations = [
        migrations.RunPython(clear_stale_location_data, migrations.RunPython.noop),

        # Drop the old unique_together constraints before touching the
        # fields they reference, so the SQLite table-recreation performed
        # by the RemoveField operations below never sees a UNIQUE
        # constraint pointing at a column that's about to disappear.
        migrations.AlterUniqueTogether(
            name='chamber',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='floor',
            unique_together=set(),
        ),

        # Old Chamber (floor -> chamber, with capacity_bags) becomes Block,
        # so strip the fields that no longer belong on the new top-level
        # Chamber.
        migrations.RemoveField(
            model_name='chamber',
            name='floor',
        ),
        migrations.RemoveField(
            model_name='chamber',
            name='capacity_bags',
        ),

        # Old Floor (facility -> floor) is reparented under the new Chamber.
        migrations.RemoveField(
            model_name='floor',
            name='facility',
        ),

        # New top-level Chamber sits directly under Facility. The table is
        # guaranteed empty at this point (see clear_stale_location_data
        # above), so the throwaway default is never actually persisted
        # anywhere -- it only satisfies Django's migration-time requirement
        # for a non-nullable field being added.
        migrations.AddField(
            model_name='chamber',
            name='facility',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='chambers', to='facilities.facility'),
            preserve_default=False,
        ),

        # Floor is reparented from Facility to the new Chamber. Same
        # empty-table reasoning as above applies to the throwaway default.
        migrations.AddField(
            model_name='floor',
            name='chamber',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='floors', to='locations.chamber'),
            preserve_default=False,
        ),

        migrations.CreateModel(
            name='Block',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('capacity_bags', models.PositiveIntegerField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('floor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocks', to='locations.floor')),
            ],
            options={
                'ordering': ('sort_order', 'name'),
                'unique_together': {('floor', 'name')},
            },
        ),

        migrations.AlterUniqueTogether(
            name='chamber',
            unique_together={('facility', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='floor',
            unique_together={('chamber', 'name')},
        ),

        migrations.AlterModelOptions(
            name='chamber',
            options={'ordering': ('sort_order', 'name')},
        ),
        migrations.AlterModelOptions(
            name='floor',
            options={'ordering': ('sort_order', 'name')},
        ),
    ]
