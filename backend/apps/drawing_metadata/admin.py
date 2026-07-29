"""Django backendのadminに関する入口またはデータ定義を提供する。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from django.contrib import admin

from apps.drawing_metadata.models import (
    TagDictionaryEntry,
    DrawingMetadataAgentHeartbeat,
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


@admin.register(DrawingMetadataAgentHeartbeat)
class DrawingMetadataAgentHeartbeatAdmin(admin.ModelAdmin):
    list_display = ("worker_name", "state", "mode", "current_job", "runner_version", "updated_at")
    search_fields = ("worker_name", "last_error")
    list_filter = ("state", "mode")
    readonly_fields = ("updated_at",)


@admin.register(DrawingMetadataSnapshot)
class DrawingMetadataSnapshotAdmin(admin.ModelAdmin):
    list_display = ("drawing", "extraction_mode", "normalizer_version", "tag_rule_version", "updated_at", "updated_by")
    search_fields = ("drawing__filename", "drawing__host_drawing_id")


@admin.register(DrawingMetadataAuditLog)
class DrawingMetadataAuditLogAdmin(admin.ModelAdmin):
    list_display = ("drawing", "extraction_mode", "action_type", "executed_by", "executed_at")
    search_fields = ("drawing__filename", "reason", "executed_by")
    list_filter = ("action_type", "extraction_mode")


@admin.register(TagDictionaryEntry)
class TagDictionaryEntryAdmin(admin.ModelAdmin):
    list_display = ("kind", "canonical_value", "aliases_json", "priority", "enabled", "updated_at")
    search_fields = ("canonical_value", "note")
    list_filter = ("kind", "enabled")
    list_editable = ("priority", "enabled")
