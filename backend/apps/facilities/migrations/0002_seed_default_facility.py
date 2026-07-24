from django.db import migrations

def seed_default_facility(apps, schema_editor):
    Facility = apps.get_model('facilities', 'Facility')
    Facility.objects.get_or_create(
        code="FAC-01",
        defaults={
            "name": "Default Facility",
            "address": "123 Cold Chain Road, Logistics Park"
        }
    )

def reverse_seed(apps, schema_editor):
    Facility = apps.get_model('facilities', 'Facility')
    Facility.objects.filter(code="FAC-01").delete()

class Migration(migrations.Migration):
    dependencies = [
        ('facilities', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_default_facility, reverse_code=reverse_seed),
    ]
