from __future__ import annotations

"""Public API views for the 2D/3D viewer.

The views stay intentionally thin: serializers validate payloads, service
functions perform the side effects, and this layer only maps them to stable
HTTP responses for the handover package.
"""

from io import BytesIO

from django.http import FileResponse
from django.urls import reverse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.viewer.api.serializers import (
    OpenUrlSerializer,
    UploadFileSerializer,
    serialize_drawing_bootstrap,
    serialize_2d_session,
    serialize_3d_job,
)
from apps.viewer.models import Viewer2DSession, Viewer3DJob
from apps.viewer.services.errors import NotFoundError, ViewerError
from apps.viewer.services.source_adapters import uploaded_file_to_fetched_source
from apps.viewer.services.runtime import (
    get_artifact_store,
    get_conversion_backend,
    get_file_type_resolver,
    get_job_store,
    get_pdm_drawing_resolver,
    get_source_fetcher,
)
from apps.viewer.services.tiff_pages import render_tiff_page_png
from apps.viewer.services.viewer2d import open_2d_session, open_2d_session_from_source
from apps.viewer.services.viewer3d import open_3d_job, open_3d_job_from_source


class ViewerBaseApiView(APIView):
    """Shared HTTP helpers used by both 2D and 3D endpoints."""

    def handle_exception(self, exc):  # type: ignore[override]
        # service 層の独自例外を HTTP レスポンスへ寄せ、各 View の post/get を薄く保つ。
        if isinstance(exc, ViewerError):
            return Response({"error": {"code": exc.code, "message": exc.message}}, status=exc.status_code)
        if isinstance(exc, ValueError):
            return Response(
                {"error": {"code": "validation_error", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().handle_exception(exc)

    def ensure_local_file_enabled(self) -> None:
        from django.conf import settings

        if not settings.VIEWER_LOCAL_FILE_ENABLED:
            raise NotFoundError("Local file upload is disabled")

    @staticmethod
    def _validate(serializer_class, data: object) -> dict:
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    @staticmethod
    def _source_url(request, session: Viewer2DSession) -> str:
        return request.build_absolute_uri(reverse("viewer2d-source", kwargs={"session_id": session.id}))

    @staticmethod
    def _model_url(request, job: Viewer3DJob) -> str:
        if job.status != Viewer3DJob.STATUS_READY:
            return ""
        return request.build_absolute_uri(reverse("viewer3d-model", kwargs={"job_id": job.id}))

    def _page_image_urls(self, request, session: Viewer2DSession) -> list[str]:
        # TIFF だけはページ単位の画像 URL が必要なので、ここで API 契約へ展開する。
        if session.extension != "tiff":
            return []
        return [
            request.build_absolute_uri(
                reverse("viewer2d-page-image", kwargs={"session_id": session.id, "page_number": page_number})
            )
            for page_number in range(1, session.page_count + 1)
        ]

    def _serialize_2d_session_response(self, request, session: Viewer2DSession) -> Response:
        return Response(
            serialize_2d_session(
                session,
                self._source_url(request, session),
                page_image_urls=self._page_image_urls(request, session),
            ),
            status=status.HTTP_201_CREATED,
        )

    def _serialize_3d_job_response(self, request, job: Viewer3DJob, *, status_code: int) -> Response:
        return Response(serialize_3d_job(job, self._model_url(request, job)), status=status_code)

    def _resolve_drawing(self, request, drawing_id: str):
        return get_pdm_drawing_resolver(request).resolve(str(drawing_id))

    @staticmethod
    def _get_2d_session_or_404(session_id: str) -> Viewer2DSession:
        try:
            return get_job_store().get_2d_session(session_id)
        except Viewer2DSession.DoesNotExist as exc:
            raise NotFoundError("2D session not found") from exc

    @staticmethod
    def _get_3d_job_or_404(job_id: str) -> Viewer3DJob:
        try:
            return get_job_store().get_3d_job(job_id)
        except Viewer3DJob.DoesNotExist as exc:
            raise NotFoundError("3D job not found") from exc

    @staticmethod
    def _artifact_path_or_404(relative_path: str, *, missing_message: str):
        artifact = get_artifact_store().root / relative_path
        if not artifact.exists():
            raise NotFoundError(missing_message)
        return artifact


class Viewer2DOpenView(ViewerBaseApiView):
    def post(self, request):
        # URL 入力は serializer で検証し、その後は service に副作用を委譲する。
        validated_data = self._validate(OpenUrlSerializer, request.data)
        session = open_2d_session(
            source_url=validated_data["url"],
            fetcher=get_source_fetcher(),
            resolver=get_file_type_resolver(),
            artifact_store=get_artifact_store(),
            job_store=get_job_store(),
        )
        return self._serialize_2d_session_response(request, session)


class DrawingBootstrapView(ViewerBaseApiView):
    def get(self, request, drawing_id: str):
        drawing = self._resolve_drawing(request, drawing_id)
        return Response(serialize_drawing_bootstrap(drawing), status=status.HTTP_200_OK)


class DrawingViewer2DOpenView(ViewerBaseApiView):
    def post(self, request, drawing_id: str):
        drawing = self._resolve_drawing(request, drawing_id)
        if not drawing.source_2d_url:
            raise NotFoundError("2D source is not available for this drawing")
        session = open_2d_session(
            source_url=drawing.source_2d_url,
            fetcher=get_source_fetcher(),
            resolver=get_file_type_resolver(),
            artifact_store=get_artifact_store(),
            job_store=get_job_store(),
        )
        return self._serialize_2d_session_response(request, session)


class Viewer2DUploadView(ViewerBaseApiView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # upload も最終的には FetchedSource に寄せ、URL 入力と同じ後段処理を再利用する。
        self.ensure_local_file_enabled()
        validated_data = self._validate(UploadFileSerializer, request.data)
        fetched = uploaded_file_to_fetched_source(validated_data["file"])
        session = open_2d_session_from_source(
            fetched=fetched,
            resolver=get_file_type_resolver(),
            artifact_store=get_artifact_store(),
            job_store=get_job_store(),
        )
        return self._serialize_2d_session_response(request, session)


class Viewer2DSourceView(ViewerBaseApiView):
    def get(self, request, session_id: str):
        session = self._get_2d_session_or_404(session_id)
        artifact = self._artifact_path_or_404(session.artifact_path, missing_message="2D source artifact not found")

        # 元ファイルをそのまま返し、PDF/JPEG/TIFF ごとの描画差分は frontend adapter に任せる。
        return FileResponse(
            artifact.open("rb"),
            content_type=session.mime_type,
            filename=session.filename,
            as_attachment=False,
        )


class Viewer2DPageImageView(ViewerBaseApiView):
    def get(self, request, session_id: str, page_number: int):
        session = self._get_2d_session_or_404(session_id)

        if session.extension != "tiff":
            raise NotFoundError("Page image is only available for TIFF sessions")

        artifact = self._artifact_path_or_404(session.artifact_path, missing_message="2D source artifact not found")

        png_bytes = render_tiff_page_png(artifact.read_bytes(), page_number - 1)

        # TIFF はブラウザ差分を避けるため、backend でページごとの PNG にして返す。
        return FileResponse(
            BytesIO(png_bytes),
            content_type="image/png",
            filename=f"{session.filename}-page-{page_number}.png",
            as_attachment=False,
        )


class Viewer3DOpenView(ViewerBaseApiView):
    def post(self, request):
        # 3D では URL 取得に加えて変換が入り得るが、View からは 1 つの service 呼び出しに見せる。
        validated_data = self._validate(OpenUrlSerializer, request.data)
        job = open_3d_job(
            source_url=validated_data["url"],
            fetcher=get_source_fetcher(),
            resolver=get_file_type_resolver(),
            artifact_store=get_artifact_store(),
            job_store=get_job_store(),
            conversion_backend=get_conversion_backend(),
        )
        return self._serialize_3d_job_response(request, job, status_code=status.HTTP_201_CREATED)


class DrawingViewer3DOpenView(ViewerBaseApiView):
    def post(self, request, drawing_id: str):
        drawing = self._resolve_drawing(request, drawing_id)
        if not drawing.source_3d_url:
            raise NotFoundError("3D source is not available for this drawing")
        job = open_3d_job(
            source_url=drawing.source_3d_url,
            fetcher=get_source_fetcher(),
            resolver=get_file_type_resolver(),
            artifact_store=get_artifact_store(),
            job_store=get_job_store(),
            conversion_backend=get_conversion_backend(),
        )
        return self._serialize_3d_job_response(request, job, status_code=status.HTTP_201_CREATED)


class Viewer3DUploadView(ViewerBaseApiView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        self.ensure_local_file_enabled()
        validated_data = self._validate(UploadFileSerializer, request.data)
        fetched = uploaded_file_to_fetched_source(validated_data["file"])
        job = open_3d_job_from_source(
            fetched=fetched,
            resolver=get_file_type_resolver(),
            artifact_store=get_artifact_store(),
            job_store=get_job_store(),
            conversion_backend=get_conversion_backend(),
        )
        return self._serialize_3d_job_response(request, job, status_code=status.HTTP_201_CREATED)


class Viewer3DJobView(ViewerBaseApiView):
    def get(self, request, job_id: str):
        # polling 用 API。frontend はこの状態だけ見て ready/failed を判断する。
        job = self._get_3d_job_or_404(job_id)
        return self._serialize_3d_job_response(request, job, status_code=status.HTTP_200_OK)


class Viewer3DModelView(ViewerBaseApiView):
    def get(self, request, job_id: str):
        job = self._get_3d_job_or_404(job_id)

        if job.status != Viewer3DJob.STATUS_READY or not job.model_artifact_path:
            raise NotFoundError("3D model artifact is not ready")

        artifact = self._artifact_path_or_404(job.model_artifact_path, missing_message="3D model artifact not found")

        # 表示用 artifact だけを公開し、元の STEP/STL 保存場所は API から隠す。
        return FileResponse(
            artifact.open("rb"),
            content_type="model/stl",
            filename=artifact.name,
            as_attachment=False,
        )
