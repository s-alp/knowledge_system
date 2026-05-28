from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


EXTRACTION_MODE_CHOICES = [("2d", "2D"), ("3d", "3D")]


def copy_extraction_mode_from_registered_drawing(apps, schema_editor):
    RegisteredDrawing = apps.get_model("drawing_metadata", "RegisteredDrawing")
    DrawingMetadataExtractionJob = apps.get_model("drawing_metadata", "DrawingMetadataExtractionJob")
    DrawingMetadataSnapshot = apps.get_model("drawing_metadata", "DrawingMetadataSnapshot")
    DrawingMetadataAuditLog = apps.get_model("drawing_metadata", "DrawingMetadataAuditLog")

    drawing_kind_map = {str(drawing.id): drawing.source_kind for drawing in RegisteredDrawing.objects.all()}

    for job in DrawingMetadataExtractionJob.objects.select_related("drawing").all():
        job.extraction_mode = drawing_kind_map.get(str(job.drawing_id), "3d")
        job.save(update_fields=["extraction_mode"])

    for snapshot in DrawingMetadataSnapshot.objects.select_related("drawing").all():
        snapshot.extraction_mode = drawing_kind_map.get(str(snapshot.drawing_id), "3d")
        snapshot.save(update_fields=["extraction_mode"])

    for audit_log in DrawingMetadataAuditLog.objects.select_related("drawing").all():
        audit_log.extraction_mode = drawing_kind_map.get(str(audit_log.drawing_id), "3d")
        audit_log.save(update_fields=["extraction_mode"])


class Migration(migrations.Migration):

    dependencies = [
        ("drawing_metadata", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="drawingmetadatasnapshot",
            options={"ordering": ["drawing_id", "extraction_mode"]},
        ),
        migrations.AddField(
            model_name="drawingmetadataauditlog",
            name="extraction_mode",
            field=models.CharField(choices=EXTRACTION_MODE_CHOICES, default="3d", db_index=True, max_length=8),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="drawingmetadataextractionjob",
            name="extraction_mode",
            field=models.CharField(choices=EXTRACTION_MODE_CHOICES, default="3d", db_index=True, max_length=8),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="drawingmetadataextractionjob",
            name="lease_expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="drawingmetadataextractionjob",
            name="retry_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="drawingmetadataextractionjob",
            name="worker_name",
            field=models.CharField(blank=True, db_index=True, default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="drawingmetadatasnapshot",
            name="extraction_mode",
            field=models.CharField(choices=EXTRACTION_MODE_CHOICES, default="3d", db_index=True, max_length=8),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="drawingmetadatasnapshot",
            name="drawing",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="snapshots",
                to="drawing_metadata.registereddrawing",
            ),
        ),
        migrations.AlterField(
            model_name="drawingmetadatasnapshot",
            name="latest_job",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="latest_snapshots",
                to="drawing_metadata.drawingmetadataextractionjob",
            ),
        ),
        migrations.RunPython(copy_extraction_mode_from_registered_drawing, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="registereddrawing",
            name="source_kind",
        ),
        migrations.AddConstraint(
            model_name="drawingmetadatasnapshot",
            constraint=models.UniqueConstraint(
                fields=("drawing", "extraction_mode"),
                name="drawing_metadata_unique_snapshot_per_mode",
            ),
        ),
    ]
