from django.contrib import admin

from apps.drawing_metadata.models import (
    DrawingMetadataAuditLog,
    DrawingMetadataExtractionJob,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
)


@admin.register(RegisteredDrawing)
class RegisteredDrawingAdmin(admin.ModelAdmin):
    list_display = ("filename", "source_format", "host_drawing_id", "updated_at")
    search_fields = ("filename", "host_drawing_id", "source_path")
    list_filter = ("source_format",)


@admin.register(DrawingMetadataExtractionJob)
class DrawingMetadataExtractionJobAdmin(admin.ModelAdmin):
    list_display = (
        "drawing",
        "extraction_mode",
        "extraction_profile",
        "status",
        "worker_name",
        "retry_count",
        "started_at",
        "finished_at",
    )
    search_fields = ("drawing__filename", "drawing__host_drawing_id", "error_message", "extraction_profile")
    list_filter = ("status", "extraction_mode", "extraction_profile")


@admin.register(DrawingMetadataSnapshot)
class DrawingMetadataSnapshotAdmin(admin.ModelAdmin):
    list_display = ("drawing", "extraction_mode", "normalizer_version", "tag_rule_version", "updated_at", "updated_by")
    search_fields = ("drawing__filename", "drawing__host_drawing_id")


@admin.register(DrawingMetadataAuditLog)
class DrawingMetadataAuditLogAdmin(admin.ModelAdmin):
    list_display = ("drawing", "extraction_mode", "action_type", "executed_by", "executed_at")
    search_fields = ("drawing__filename", "reason", "executed_by")
    list_filter = ("action_type", "extraction_mode")
