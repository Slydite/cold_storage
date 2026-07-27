from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0002_restructure_hierarchy'),
    ]

    operations = [
        migrations.AddField(
            model_name='chamber',
            name='code',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='floor',
            name='code',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='block',
            name='code',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
