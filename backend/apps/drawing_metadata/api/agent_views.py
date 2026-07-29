"""図面メタデータAPIのagent_viewsを定義し、HTTP入出力をservice層へ接続する。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from __future__ import annotations

import hashlib
import secrets
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import APIException, AuthenticationFailed, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drawing_metadata.models import (
    DrawingMetadataAgentHeartbeat,
    DrawingMetadataExtractionJob,
)
from apps.drawing_metadata.services.source_formats import EXTRACTOR_SCOPE_SXNET
from apps.drawing_metadata.tasks.extraction_tasks import (
    claim_next_job,
    complete_claimed_job,
    fail_claimed_job,
    prepare_claimed_job,
    refresh_claimed_job_lease,
)


class AgentServerConfigurationError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "agent_token_not_configured"
    default_detail = "DRAWING_METADATA_AGENT_TOKENが設定されていません。"


class AgentJobConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "agent_job_ownership"


class AgentIdentity:
    is_authenticated = True

    def __init__(self, token_fingerprint: str):
        self.token_fingerprint = token_fingerprint


class DrawingMetadataAgentAuthentication(BaseAuthentication):
    """Windows agent専用Bearer tokenを検証し、worker名付きの認証主体を作る。"""

    keyword = "Bearer"

    def authenticate(self, request):
        expected_token = settings.DRAWING_METADATA_AGENT_TOKEN
        if not expected_token:
            raise AgentServerConfigurationError()

        authorization = get_authorization_header(request).decode("utf-8")
        scheme, separator, supplied_token = authorization.partition(" ")
        if separator != " " or scheme.lower() != self.keyword.lower() or not supplied_token:
            raise AuthenticationFailed("Bearer tokenが必要です。")
        if not secrets.compare_digest(supplied_token, expected_token):
            raise AuthenticationFailed("Bearer tokenが一致しません。")

        fingerprint = hashlib.sha256(expected_token.encode("utf-8")).hexdigest()[:12]
        return AgentIdentity(fingerprint), None

    def authenticate_header(self, request):
        return self.keyword


class AgentApiView(APIView):
    authentication_classes = [DrawingMetadataAgentAuthentication]
    permission_classes = [IsAuthenticated]


class AgentClaimSerializer(serializers.Serializer):
    workerName = serializers.CharField(max_length=255)
    mode = serializers.ChoiceField(choices=("2d", "3d", "all"), default="all")
    runnerVersion = serializers.CharField(max_length=64, required=False, allow_blank=True)
    processId = serializers.IntegerField(required=False, min_value=1, allow_null=True)


class AgentHeartbeatSerializer(AgentClaimSerializer):
    state = serializers.ChoiceField(choices=("starting", "claiming", "idle", "processing", "stopping", "error"))
    jobId = serializers.UUIDField(required=False, allow_null=True)
    lastError = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)


class AgentOwnedJobSerializer(serializers.Serializer):
    workerName = serializers.CharField(max_length=255)


class AgentCompleteSerializer(AgentOwnedJobSerializer):
    result = serializers.JSONField()

    def validate_result(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("resultはJSON objectで指定してください。")
        return value


class AgentFailSerializer(AgentOwnedJobSerializer):
    errorMessage = serializers.CharField(trim_whitespace=False, max_length=20000)


class AgentAssetSerializer(AgentOwnedJobSerializer):
    relativePath = serializers.CharField(max_length=1024)
    file = serializers.FileField()


def _owned_processing_job(job_id, worker_name: str) -> DrawingMetadataExtractionJob:
    try:
        job = DrawingMetadataExtractionJob.objects.select_related("drawing").get(pk=job_id)
    except DrawingMetadataExtractionJob.DoesNotExist as exc:
        raise NotFound("jobが見つかりません。") from exc
    if job.status != DrawingMetadataExtractionJob.STATUS_PROCESSING:
        raise AgentJobConflict("jobはprocessingではありません。")
    if job.worker_name != worker_name:
        raise AgentJobConflict("jobは別workerが所有しています。")
    return job


def _safe_server_source_path(job: DrawingMetadataExtractionJob) -> Path | None:
    source_path = Path(job.drawing.source_path)
    if not source_path.is_file():
        return None
    try:
        source_path.resolve().relative_to(settings.DRAWING_METADATA_STORAGE_ROOT.resolve())
    except ValueError:
        return None
    return source_path


def _agent_preview_root(job_id) -> Path:
    return settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT / str(job_id)


def _asset_target(job_id, relative_path: str) -> Path:
    normalized = PurePosixPath(relative_path.replace("\\", "/"))
    if normalized.is_absolute() or not normalized.parts or any(part in {"", ".", ".."} for part in normalized.parts):
        raise serializers.ValidationError({"relativePath": "安全な相対パスを指定してください。"})

    root = _agent_preview_root(job_id).resolve()
    target = (root / Path(*normalized.parts)).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise serializers.ValidationError({"relativePath": "asset保存先がjobディレクトリ外です。"}) from exc
    return target


def _write_uploaded_asset(job_id, relative_path: str, uploaded_file: UploadedFile) -> Path:
    if uploaded_file.size > settings.DRAWING_METADATA_AGENT_MAX_ASSET_BYTES:
        raise serializers.ValidationError({"file": "assetサイズが上限を超えています。"})

    target = _asset_target(job_id, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".uploading")
    try:
        with temporary.open("wb") as stream:
            for chunk in uploaded_file.chunks():
                stream.write(chunk)
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def _update_agent_heartbeat(validated_data: dict) -> DrawingMetadataAgentHeartbeat:
    job = None
    job_id = validated_data.get("jobId")
    if job_id is not None:
        job = _owned_processing_job(job_id, validated_data["workerName"])
        refresh_claimed_job_lease(job.id, validated_data["workerName"])

    heartbeat, _created = DrawingMetadataAgentHeartbeat.objects.update_or_create(
        worker_name=validated_data["workerName"],
        defaults={
            "state": validated_data["state"],
            "mode": validated_data["mode"],
            "current_job": job,
            "process_id": validated_data.get("processId"),
            "runner_version": validated_data.get("runnerVersion", ""),
            "last_error": validated_data.get("lastError", ""),
            "metadata_json": {},
        },
    )
    return heartbeat


class AgentClaimApiView(AgentApiView):
    """待機ジョブを排他的に確保し、入力取得先と抽出条件をagentへ返す。"""

    def post(self, request):
        serializer = AgentClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        job = claim_next_job(
            worker_name=values["workerName"],
            mode=values["mode"],
            extractor_scope=EXTRACTOR_SCOPE_SXNET,
        )
        if job is None:
            DrawingMetadataAgentHeartbeat.objects.update_or_create(
                worker_name=values["workerName"],
                defaults={
                    "state": "idle",
                    "mode": values["mode"],
                    "current_job": None,
                    "process_id": values.get("processId"),
                    "runner_version": values.get("runnerVersion", ""),
                    "last_error": "",
                    "metadata_json": {},
                },
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        prepare_claimed_job(job)
        DrawingMetadataAgentHeartbeat.objects.update_or_create(
            worker_name=values["workerName"],
            defaults={
                "state": "processing",
                "mode": values["mode"],
                "current_job": job,
                "process_id": values.get("processId"),
                "runner_version": values.get("runnerVersion", ""),
                "last_error": "",
                "metadata_json": {},
            },
        )
        source_url = request.build_absolute_uri(
            reverse("drawing-metadata-agent-job-source", kwargs={"job_id": job.id})
            + f"?workerName={quote(values['workerName'], safe='')}"
        )
        preview_base_url = request.build_absolute_uri(
            reverse(
                "drawing-metadata-preview-asset",
                kwargs={"job_id": job.id, "filename": "__asset__"},
            )
        ).rsplit("/", 1)[0]
        return Response(
            {
                "jobId": str(job.id),
                "drawingId": str(job.drawing_id),
                "extractionMode": job.extraction_mode,
                "extractionProfile": job.extraction_profile or "default",
                "extractionOptions": job.extraction_options_json or {},
                "leaseExpiresAt": job.lease_expires_at,
                "source": {
                    "path": job.drawing.source_path,
                    "filename": job.drawing.filename,
                    "format": job.drawing.source_format,
                    "sha256": job.drawing.source_content_sha256,
                    "downloadUrl": source_url,
                    "downloadAvailable": _safe_server_source_path(job) is not None,
                },
                "preview": {
                    "baseUrl": preview_base_url,
                },
            }
        )


class AgentHeartbeatApiView(AgentApiView):
    """agentの生存状態と現在処理中のジョブを記録する。"""

    def post(self, request):
        serializer = AgentHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            heartbeat = _update_agent_heartbeat(serializer.validated_data)
        except ValueError as exc:
            return Response(
                {"error": {"code": "agent_job_ownership", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {
                "workerName": heartbeat.worker_name,
                "state": heartbeat.state,
                "updatedAt": heartbeat.updated_at,
            }
        )


class AgentJobSourceApiView(AgentApiView):
    """共有パスを直接読めないagentへ、確保済みジョブの元CADを配信する。"""

    def get(self, request, job_id):
        serializer = AgentOwnedJobSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        job = _owned_processing_job(job_id, serializer.validated_data["workerName"])
        source_path = _safe_server_source_path(job)
        if source_path is None:
            return Response(
                {
                    "error": {
                        "code": "agent_source_not_on_server",
                        "message": "入力はDocker保存領域にありません。Windows側のsourcePathを使用してください。",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        response = FileResponse(source_path.open("rb"), as_attachment=True, filename=job.drawing.filename)
        if job.drawing.source_content_sha256:
            response["X-Content-SHA256"] = job.drawing.source_content_sha256
        return response


class AgentJobAssetApiView(AgentApiView):
    """agentが生成したSTLなどを、ジョブ専用の安全な相対パスへ保存する。"""

    def post(self, request, job_id):
        serializer = AgentAssetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        _owned_processing_job(job_id, values["workerName"])
        target = _write_uploaded_asset(job_id, values["relativePath"], values["file"])
        return Response(
            {
                "relativePath": values["relativePath"].replace("\\", "/"),
                "sizeBytes": target.stat().st_size,
            },
            status=status.HTTP_201_CREATED,
        )


class AgentJobCompleteApiView(AgentApiView):
    """所有権とresult JSONを検証し、snapshot保存後にジョブを完了へ遷移する。"""

    def post(self, request, job_id):
        serializer = AgentCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            job = complete_claimed_job(job_id, values["workerName"], values["result"])
        except ValueError as exc:
            return Response(
                {"error": {"code": "agent_job_ownership", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )
        DrawingMetadataAgentHeartbeat.objects.filter(worker_name=values["workerName"]).update(
            state="idle",
            current_job=None,
            last_error="",
            updated_at=timezone.now(),
        )
        return Response({"jobId": str(job.id), "status": job.status})


class AgentJobFailApiView(AgentApiView):
    """agentが返した失敗理由を保存し、ジョブを再確認可能な失敗状態へ遷移する。"""

    def post(self, request, job_id):
        serializer = AgentFailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            job = fail_claimed_job(job_id, values["workerName"], values["errorMessage"])
        except ValueError as exc:
            return Response(
                {"error": {"code": "agent_job_ownership", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )
        DrawingMetadataAgentHeartbeat.objects.filter(worker_name=values["workerName"]).update(
            state="error",
            current_job=None,
            last_error=values["errorMessage"],
            updated_at=timezone.now(),
        )
        return Response({"jobId": str(job.id), "status": job.status})
