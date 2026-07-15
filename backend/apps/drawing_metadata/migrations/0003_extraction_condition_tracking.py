from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drawing_metadata", "0002_mode_aware_refactor"),
    ]

    operations = [
        migrations.AddField(
            model_name="drawingmetadataextractionjob",
            name="diagnostics_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="drawingmetadataextractionjob",
            name="extraction_options_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="drawingmetadataextractionjob",
            name="extraction_profile",
            field=models.CharField(blank=True, db_index=True, default="default", max_length=64),
        ),
    ]
