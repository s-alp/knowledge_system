from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("drawing_metadata", "0007_tagdictionaryentry_part_name_kind"),
    ]

    operations = [
        migrations.CreateModel(
            name="DrawingMetadataAgentHeartbeat",
            fields=[
                ("worker_name", models.CharField(max_length=255, primary_key=True, serialize=False)),
                ("state", models.CharField(db_index=True, max_length=32)),
                ("mode", models.CharField(default="all", max_length=8)),
                ("process_id", models.PositiveIntegerField(blank=True, null=True)),
                ("runner_version", models.CharField(blank=True, max_length=64)),
                ("last_error", models.TextField(blank=True)),
                ("metadata_json", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                (
                    "current_job",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="agent_heartbeats",
                        to="drawing_metadata.drawingmetadataextractionjob",
                    ),
                ),
            ],
            options={
                "ordering": ("worker_name",),
            },
        ),
    ]
