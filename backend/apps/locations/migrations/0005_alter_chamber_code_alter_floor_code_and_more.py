from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0004_backfill_location_codes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chamber',
            name='code',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='floor',
            name='code',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='block',
            name='code',
            field=models.CharField(max_length=50),
        ),
    ]
