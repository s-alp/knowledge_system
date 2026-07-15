from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Viewer2DSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_url", models.URLField()),
                ("source_url_hash", models.CharField(db_index=True, max_length=64)),
                ("filename", models.CharField(max_length=255)),
                ("extension", models.CharField(max_length=32)),
                ("mime_type", models.CharField(max_length=255)),
                ("artifact_path", models.CharField(max_length=512)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Viewer3DJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_url", models.URLField()),
                ("source_url_hash", models.CharField(db_index=True, max_length=64)),
                ("filename", models.CharField(max_length=255)),
                ("source_extension", models.CharField(max_length=32)),
                ("source_mime_type", models.CharField(max_length=255)),
                ("source_artifact_path", models.CharField(max_length=512)),
                ("model_artifact_path", models.CharField(blank=True, max_length=512)),
                ("model_format", models.CharField(blank=True, max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("processing", "Processing"),
                            ("ready", "Ready"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=32,
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
