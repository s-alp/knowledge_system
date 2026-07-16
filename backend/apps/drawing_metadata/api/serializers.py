from __future__ import annotations

from rest_framework import serializers

from apps.drawing_metadata.models import (
    DrawingMetadataExtractionJob,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
    EXTRACTION_MODE_CHOICES,
)
from apps.drawing_metadata.services.composition import compose_drawing_metadata
from apps.drawing_metadata.services.knowledge_payload_preview import build_knowledge_system_payload_preview


class RegisteredDrawingCreateSerializer(serializers.ModelSerializer):
    hostDrawingId = serializers.CharField(source="host_drawing_id", allow_blank=True, required=False)
    sourcePath = serializers.CharField(source="source_path")
    sourceFormat = serializers.CharField(source="source_format")

    class Meta:
        model = RegisteredDrawing
        fields = ("id", "hostDrawingId", "filename", "sourcePath", "sourceFormat")
        read_only_fields = ("id",)


class ExtractRequestSerializer(serializers.Serializer):
    extractionMode = serializers.ChoiceField(choices=EXTRACTION_MODE_CHOICES)
    extractionProfile = serializers.CharField(required=False, allow_blank=True, default="default")
    extractionOptions = serializers.JSONField(required=False, default=dict)

    def validate_extractionOptions(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("extractionOptions は object で指定してください。")
        return value


class ReviewDecisionSerializer(serializers.Serializer):
    extractionMode = serializers.ChoiceField(choices=EXTRACTION_MODE_CHOICES)
    decision = serializers.ChoiceField(choices=DrawingMetadataSnapshot.REVIEW_STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class DrawingMetadataExtractionJobSerializer(serializers.ModelSerializer):
    jobId = serializers.UUIDField(source="id")
    drawingId = serializers.UUIDField(source="drawing_id")
    extractionMode = serializers.CharField(source="extraction_mode")
    workerName = serializers.CharField(source="worker_name", allow_blank=True)
    leaseExpiresAt = serializers.DateTimeField(source="lease_expires_at", allow_null=True)
    retryCount = serializers.IntegerField(source="retry_count")
    startedAt = serializers.DateTimeField(source="started_at", allow_null=True)
    finishedAt = serializers.DateTimeField(source="finished_at", allow_null=True)
    elapsedMs = serializers.IntegerField(source="elapsed_ms", allow_null=True)
    errorMessage = serializers.CharField(source="error_message", allow_blank=True)
    warnings = serializers.JSONField(source="warnings_json")
    extractionProfile = serializers.CharField(source="extraction_profile", allow_blank=True)
    extractionOptions = serializers.JSONField(source="extraction_options_json")
    diagnostics = serializers.JSONField(source="diagnostics_json")
    extractorName = serializers.CharField(source="extractor_name", allow_blank=True)
    extractorVersion = serializers.CharField(source="extractor_version", allow_blank=True)
    schemaVersion = serializers.CharField(source="schema_version", allow_blank=True)
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = DrawingMetadataExtractionJob
        fields = (
            "jobId",
            "drawingId",
            "extractionMode",
            "status",
            "workerName",
            "leaseExpiresAt",
            "retryCount",
            "startedAt",
            "finishedAt",
            "elapsedMs",
            "errorMessage",
            "warnings",
            "extractionProfile",
            "extractionOptions",
            "diagnostics",
            "extractorName",
            "extractorVersion",
            "schemaVersion",
            "createdAt",
            "updatedAt",
        )


class SnapshotSerializer(serializers.ModelSerializer):
    extractionMode = serializers.CharField(source="extraction_mode")
    latestJob = serializers.SerializerMethodField()
    rawExtract = serializers.JSONField(source="raw_extract_json")
    canonicalAttributes = serializers.JSONField(source="canonical_attributes_json")
    derivedTags = serializers.JSONField(source="derived_tags_json")
    manualOverrides = serializers.JSONField(source="manual_overrides_json")
    updatedAt = serializers.DateTimeField(source="updated_at")
    updatedBy = serializers.CharField(source="updated_by", allow_blank=True)
    reviewStatus = serializers.CharField(source="review_status")
    reviewedAt = serializers.DateTimeField(source="reviewed_at", allow_null=True)
    reviewedBy = serializers.CharField(source="reviewed_by", allow_blank=True)

    class Meta:
        model = DrawingMetadataSnapshot
        fields = (
            "extractionMode",
            "latestJob",
            "rawExtract",
            "canonicalAttributes",
            "derivedTags",
            "manualOverrides",
            "updatedAt",
            "updatedBy",
            "reviewStatus",
            "reviewedAt",
            "reviewedBy",
        )

    def get_latestJob(self, obj: DrawingMetadataSnapshot) -> dict | None:
        if not obj.latest_job:
            return None
        return DrawingMetadataExtractionJobSerializer(obj.latest_job).data


class RegisteredDrawingListSerializer(serializers.ModelSerializer):
    drawingId = serializers.UUIDField(source="id")
    hostDrawingId = serializers.CharField(source="host_drawing_id")
    sourcePath = serializers.CharField(source="source_path")
    sourceFormat = serializers.CharField(source="source_format")
    snapshotModes = serializers.SerializerMethodField()
    latestJobStatusByMode = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = RegisteredDrawing
        fields = (
            "drawingId",
            "hostDrawingId",
            "filename",
            "sourcePath",
            "sourceFormat",
            "snapshotModes",
            "latestJobStatusByMode",
            "createdAt",
            "updatedAt",
        )

    def get_snapshotModes(self, obj: RegisteredDrawing) -> list[str]:
        return sorted(snapshot.extraction_mode for snapshot in obj.snapshots.all())

    def get_latestJobStatusByMode(self, obj: RegisteredDrawing) -> dict[str, str | None]:
        statuses: dict[str, str | None] = {}
        prefetched_jobs = list(obj.jobs.all())
        for mode in ("2d", "3d"):
            latest_job = next((job for job in prefetched_jobs if job.extraction_mode == mode), None)
            statuses[mode] = latest_job.status if latest_job else None
        return statuses


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _first_value(*values):
    for value in values:
        if _has_value(value):
            return value
    return None


def _as_optional_string(value) -> str | None:
    if not _has_value(value):
        return None
    return str(value)


def _tag_names(tags: list[dict]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        name = tag.get("tag")
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(str(name))
    return names


def _viewer_tag_attribute_targets(knowledge_payload_preview: dict) -> list[dict]:
    targets: list[dict] = []
    for target in knowledge_payload_preview.get("targets", []) or []:
        attributes = []
        for attribute in (target.get("attributes") or [])[:12]:
            attributes.append(
                {
                    "name": attribute.get("attributeName"),
                    "value": attribute.get("attributeValue"),
                    "sourcePath": attribute.get("sourcePath"),
                    "entityHint": attribute.get("entityHint"),
                    "bindingStatus": attribute.get("bindingStatus"),
                }
            )

        targets.append(
            {
                "targetKey": target.get("targetKey"),
                "label": target.get("label"),
                "existingReception": target.get("existingReception"),
                "tagApiStatus": target.get("tagApiStatus"),
                "writePolicy": target.get("writePolicy"),
                "tags": (target.get("tags") or [])[:20],
                "attributes": attributes,
                "reviewRequired": bool(target.get("reviewRequired")),
                "notes": target.get("notes") or [],
            }
        )
    return targets


def _viewer_tag_attributes_payload(knowledge_payload_preview: dict) -> dict:
    targets = _viewer_tag_attribute_targets(knowledge_payload_preview)
    return {
        "schemaVersion": "viewer_tag_attributes.v1",
        "sourceSchemaVersion": knowledge_payload_preview.get("schemaVersion"),
        "displayPolicy": "タグ・属性候補は図面管理で確認し、必要に応じて再抽出・手直しします。",
        "targets": targets,
        "targetCount": len(targets),
        "reviewRequired": any(target.get("reviewRequired") for target in targets),
    }


def _viewer_extraction_diagnostics(has_2d: bool, has_3d: bool) -> dict:
    missing_modes: list[str] = []
    if not has_2d:
        missing_modes.append("2d")
    if not has_3d:
        missing_modes.append("3d")

    status = "extracted"
    if len(missing_modes) == 2:
        status = "not_extracted"
    elif missing_modes:
        status = "partial"

    return {
        "schemaVersion": "viewer_extraction_diagnostics.v1",
        "status": status,
        "missingModes": missing_modes,
        "policy": "未抽出は確定不可ではなく、ビュー差・レイヤー差・印刷枠差・パーツ付加情報差を条件別に再試行する。",
        "requiredConditionChecks": [
            {
                "key": "allViews",
                "label": "全ビュー走査",
                "reason": "ICADは1データ内に複数枚・複数ビューを内包するため、初期ビューだけでは図枠・寸法・表題欄を取り逃がす。",
            },
            {
                "key": "allLayers",
                "label": "全レイヤー走査",
                "reason": "寸法、表題欄、訂正履歴、材質、パーツ付加情報が客先や図面種別で別レイヤーに分かれる可能性がある。",
            },
            {
                "key": "printFrame",
                "label": "印刷枠判定",
                "reason": "図枠外の作業メモや退避形状を本番タグ候補へ混入させないため、印刷範囲内外を分けて記録する。",
            },
            {
                "key": "partAttributes",
                "label": "パーツ付加情報",
                "reason": "2D/3D形状とは別の情報源として、ニッケ・澁谷などの客先データに存在する付加情報を個別に読む。",
            },
        ],
    }


class RegisteredDrawingDetailSerializer(serializers.ModelSerializer):
    drawingId = serializers.UUIDField(source="id")
    hostDrawingId = serializers.CharField(source="host_drawing_id")
    sourcePath = serializers.CharField(source="source_path")
    sourceFormat = serializers.CharField(source="source_format")
    snapshotsByMode = serializers.SerializerMethodField()
    composedMetadata = serializers.SerializerMethodField()
    viewerBootstrap = serializers.SerializerMethodField()
    knowledgeSystemPayloadPreview = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = RegisteredDrawing
        fields = (
            "drawingId",
            "hostDrawingId",
            "filename",
            "sourcePath",
            "sourceFormat",
            "snapshotsByMode",
            "composedMetadata",
            "viewerBootstrap",
            "knowledgeSystemPayloadPreview",
            "createdAt",
            "updatedAt",
        )

    def get_snapshotsByMode(self, obj: RegisteredDrawing) -> dict[str, dict]:
        snapshots_by_mode: dict[str, dict] = {}
        for snapshot in obj.snapshots.all():
            snapshots_by_mode[snapshot.extraction_mode] = SnapshotSerializer(snapshot).data
        return snapshots_by_mode

    def get_composedMetadata(self, obj: RegisteredDrawing) -> dict:
        return compose_drawing_metadata(obj)

    def get_knowledgeSystemPayloadPreview(self, obj: RegisteredDrawing) -> dict:
        return build_knowledge_system_payload_preview(drawing=obj, composed_metadata=compose_drawing_metadata(obj))

    def get_viewerBootstrap(self, obj: RegisteredDrawing) -> dict:
        snapshots_by_mode = {snapshot.extraction_mode: snapshot for snapshot in obj.snapshots.all()}
        composed_metadata = compose_drawing_metadata(obj)
        knowledge_payload_preview = build_knowledge_system_payload_preview(
            drawing=obj,
            composed_metadata=composed_metadata,
        )
        canonical_attributes = composed_metadata.get("canonicalAttributes", {}) or {}
        has_2d = "2d" in snapshots_by_mode
        has_3d = "3d" in snapshots_by_mode
        drawing_name = _first_value(canonical_attributes.get("drawing_name"), obj.filename)
        drawing_number = _first_value(
            canonical_attributes.get("drawing_number"),
            canonical_attributes.get("part_number"),
        )
        return {
            "drawingId": str(obj.id),
            "title": _as_optional_string(drawing_name) or obj.filename,
            "version": _as_optional_string(canonical_attributes.get("revision")),
            "defaultMode": "2d" if has_2d else "3d",
            "availability": {
                "has2d": has_2d,
                "has3d": has_3d,
            },
            "metadata": {
                "drawingNumber": _as_optional_string(drawing_number),
                "drawingName": _as_optional_string(drawing_name),
                "drawingType": _as_optional_string(
                    _first_value(canonical_attributes.get("drawing_type"), canonical_attributes.get("equipment_category"))
                ),
                "paperSize": _as_optional_string(
                    _first_value(canonical_attributes.get("paper_size"), canonical_attributes.get("drawing_size"))
                ),
                "status": _as_optional_string(canonical_attributes.get("status")),
                "owner": _as_optional_string(
                    _first_value(canonical_attributes.get("owner"), canonical_attributes.get("designer"))
                ),
                "designPurpose": _as_optional_string(
                    _first_value(canonical_attributes.get("intention"), canonical_attributes.get("design_purpose"))
                ),
                "tags": _tag_names(composed_metadata.get("derivedTags", []) or []),
                "tagAttributes": _viewer_tag_attributes_payload(knowledge_payload_preview),
                "extractionDiagnostics": _viewer_extraction_diagnostics(has_2d, has_3d),
            },
        }


class KnowledgeEntityBusinessFieldsSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    partNumber = serializers.CharField(required=False, allow_blank=True, max_length=255)
    category = serializers.CharField(required=False, allow_blank=True, max_length=255)
    entityKind = serializers.ChoiceField(choices=("assembly", "subassembly", "part"), required=False)
    phase = serializers.CharField(required=False, allow_blank=True, max_length=100)
    status = serializers.CharField(required=False, allow_blank=True, max_length=100)
    owner = serializers.CharField(required=False, allow_blank=True, max_length=255)
    supplier = serializers.CharField(required=False, allow_blank=True, max_length=255)
    unitPrice = serializers.CharField(required=False, allow_blank=True, max_length=100)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=100)
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("businessFields はオブジェクトで指定してください。")
        unknown_fields = sorted(set(data) - set(self.fields))
        if unknown_fields:
            raise serializers.ValidationError(
                {"unknownFields": f"未対応の業務項目です: {', '.join(unknown_fields)}"}
            )
        return super().to_internal_value(data)


class ManualOverrideSerializer(serializers.Serializer):
    extractionMode = serializers.ChoiceField(choices=EXTRACTION_MODE_CHOICES)
    canonicalAttributes = serializers.JSONField(required=False)
    derivedTags = serializers.JSONField(required=False)
    businessFields = KnowledgeEntityBusinessFieldsSerializer(required=False)
    relatedDrawingIds = serializers.ListField(child=serializers.UUIDField(), required=False)
    knowledgeEntityTarget = serializers.ChoiceField(choices=("product", "part"), required=False)
    knowledgeEntityKind = serializers.ChoiceField(
        choices=("assembly", "subassembly", "part"),
        required=False,
    )
    reason = serializers.CharField(required=False, allow_blank=True)
