from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drawing_metadata", "0003_extraction_condition_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="drawingmetadatasnapshot",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("confirmed", "Confirmed"),
                    ("needs_correction", "Needs correction"),
                ],
                db_index=True,
                default="pending",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="drawingmetadatasnapshot",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="drawingmetadatasnapshot",
            name="reviewed_by",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="drawingmetadataauditlog",
            name="action_type",
            field=models.CharField(
                choices=[
                    ("extraction", "Extraction"),
                    ("override", "Override"),
                    ("requeue", "Requeue"),
                    ("review", "Review"),
                ],
                max_length=32,
            ),
        ),
    ]
