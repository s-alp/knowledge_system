"""Serializer layer for the public viewer API.

Python model fields are converted here into the camelCase keys documented for
frontend and handover consumers.
"""

from rest_framework import serializers

from apps.viewer.models import Viewer2DSession, Viewer3DJob
from apps.viewer.domain.types import ResolvedDrawing


class OpenUrlSerializer(serializers.Serializer):
    url = serializers.URLField()


class UploadFileSerializer(serializers.Serializer):
    file = serializers.FileField()


class Viewer2DSessionSerializer(serializers.Serializer):
    # 内部 model の snake_case と、外部公開する API 項目名をここで切り分ける。
    sessionId = serializers.UUIDField(source="id")
    filename = serializers.CharField()
    extension = serializers.CharField()
    mimeType = serializers.CharField(source="mime_type")
    sourceUrl = serializers.CharField()
    pageCount = serializers.IntegerField()
    pageImageUrls = serializers.ListField(child=serializers.CharField(), required=False)


class Viewer3DJobSerializer(serializers.Serializer):
    jobId = serializers.UUIDField(source="id")
    filename = serializers.CharField()
    sourceExtension = serializers.CharField(source="source_extension")
    modelFormat = serializers.CharField(source="model_format", allow_blank=True)
    status = serializers.CharField()
    modelUrl = serializers.CharField(allow_blank=True)
    error = serializers.CharField(source="error_message", allow_blank=True)


class DrawingAvailabilitySerializer(serializers.Serializer):
    has2d = serializers.BooleanField()
    has3d = serializers.BooleanField()


class DrawingMetadataSerializer(serializers.Serializer):
    drawingNumber = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    drawingName = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    drawingType = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    paperSize = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    status = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    owner = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    designPurpose = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)


class DrawingBootstrapSerializer(serializers.Serializer):
    drawingId = serializers.CharField()
    title = serializers.CharField()
    version = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    defaultMode = serializers.ChoiceField(choices=["2d", "3d"])
    availability = DrawingAvailabilitySerializer()
    metadata = DrawingMetadataSerializer()


def serialize_2d_session(session: Viewer2DSession, source_url: str, page_image_urls: list[str] | None = None) -> dict:
    # FileResponse では返せない補助 URL 群を、画面がそのまま使える形へ整形する。
    return Viewer2DSessionSerializer(
        instance={
            "id": session.id,
            "filename": session.filename,
            "extension": session.extension,
            "mime_type": session.mime_type,
            "sourceUrl": source_url,
            "pageCount": session.page_count,
            "pageImageUrls": page_image_urls or [],
        }
    ).data


def serialize_3d_job(job: Viewer3DJob, model_url: str) -> dict:
    return Viewer3DJobSerializer(
        instance={
            "id": job.id,
            "filename": job.filename,
            "source_extension": job.source_extension,
            "model_format": job.model_format,
            "status": job.status,
            "modelUrl": model_url,
            "error_message": job.error_message,
        }
    ).data


def serialize_drawing_bootstrap(drawing: ResolvedDrawing) -> dict:
    has_2d = drawing.source_2d_url is not None
    has_3d = drawing.source_3d_url is not None
    default_mode = "2d" if has_2d or not has_3d else "3d"
    return DrawingBootstrapSerializer(
        instance={
            "drawingId": drawing.drawing_id,
            "title": drawing.title,
            "version": drawing.version,
            "defaultMode": default_mode,
            "availability": {
                "has2d": has_2d,
                "has3d": has_3d,
            },
            "metadata": drawing.metadata,
        }
    ).data
