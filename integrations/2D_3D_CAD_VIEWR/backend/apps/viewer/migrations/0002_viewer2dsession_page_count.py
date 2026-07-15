from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("viewer", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="viewer2dsession",
            name="page_count",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
