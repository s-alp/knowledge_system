from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("drawing_metadata", "0004_snapshot_review_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="registereddrawing",
            name="source_content_sha256",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
    ]
