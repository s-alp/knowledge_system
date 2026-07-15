from __future__ import annotations

"""Runtime factories that keep Django settings access at the application edge."""

from django.conf import settings

from apps.viewer.services.pdm import PdmDrawingResolver, PdmResolverConfig
from apps.viewer.services.converters import CadQueryOcctBackend, ThreeDConversionBackend
from apps.viewer.services.fetchers import SourceFetcher, build_default_source_fetcher
from apps.viewer.services.filetypes import FileTypeResolver
from apps.viewer.services.jobs import JobStore
from apps.viewer.services.storage import ArtifactStore


def get_source_fetcher() -> SourceFetcher:
    # settings 依存の組み立てはここへ集め、他レイヤーは具象生成を知らなくて済むようにする。
    return build_default_source_fetcher()


def get_file_type_resolver() -> FileTypeResolver:
    return FileTypeResolver()


def get_artifact_store() -> ArtifactStore:
    # 保存先の実パス変更を Django settings だけで吸収できるようにする。
    return ArtifactStore(settings.VIEWER_STORAGE_ROOT)


def get_job_store() -> JobStore:
    # TTL は保存期限の一元設定値。service は秒数だけ受け取る。
    return JobStore(ttl_seconds=settings.VIEWER_ARTIFACT_TTL_SECONDS)


def get_conversion_backend() -> ThreeDConversionBackend:
    # 将来 backend 差し替え時も呼び出し側の import を増やさないための境界。
    return CadQueryOcctBackend()


def get_pdm_drawing_resolver(request) -> PdmDrawingResolver:
    base_url = settings.PDM_API_BASE_URL.strip() if settings.PDM_API_BASE_URL else ""
    if not base_url:
        base_url = request.build_absolute_uri("/api")
    return PdmDrawingResolver(
        config=PdmResolverConfig(
            base_url=base_url,
            drawing_resolve_path_template=settings.PDM_DRAWING_RESOLVE_PATH_TEMPLATE,
            timeout_seconds=settings.PDM_REQUEST_TIMEOUT_SECONDS,
        ),
        request=request,
    )
