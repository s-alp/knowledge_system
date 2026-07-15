from __future__ import annotations

"""3D job creation flow.

The service keeps conversion-specific work behind a small entry point so the API
layer can treat STL passthrough and STEP -> STL conversion uniformly.
"""

import hashlib
import logging
from time import perf_counter

from apps.viewer.domain.types import FetchedSource
from apps.viewer.models import Viewer3DJob
from apps.viewer.services.errors import ConversionError
from apps.viewer.services.converters import ThreeDConversionBackend
from apps.viewer.services.errors import UnsupportedFormatError
from apps.viewer.services.filetypes import FileTypeResolver
from apps.viewer.services.fetchers import SourceFetcher
from apps.viewer.services.jobs import JobStore
from apps.viewer.services.storage import ArtifactStore
from apps.viewer.services.viewer2d import cleanup_artifacts

logger = logging.getLogger("apps.viewer")


def open_3d_job(
    *,
    source_url: str,
    fetcher: SourceFetcher,
    resolver: FileTypeResolver,
    artifact_store: ArtifactStore,
    job_store: JobStore,
    conversion_backend: ThreeDConversionBackend,
) -> Viewer3DJob:
    """Fetch a remote 3D source, then reuse the common job pipeline."""
    fetch_started_at = perf_counter()
    fetched = fetcher.fetch(source_url)
    fetch_ms = (perf_counter() - fetch_started_at) * 1000
    logger.info("viewer3d_fetch_complete filename=%s fetch_ms=%.2f bytes=%s", fetched.filename, fetch_ms, len(fetched.content))
    return open_3d_job_from_source(
        fetched=fetched,
        resolver=resolver,
        artifact_store=artifact_store,
        job_store=job_store,
        conversion_backend=conversion_backend,
    )


def open_3d_job_from_source(
    *,
    fetched: FetchedSource,
    resolver: FileTypeResolver,
    artifact_store: ArtifactStore,
    job_store: JobStore,
    conversion_backend: ThreeDConversionBackend,
) -> Viewer3DJob:
    """Create a 3D job, reusing cached conversions when the input matches."""
    cleanup_artifacts(job_store, artifact_store)
    resolved = resolver.resolve(fetched.filename, fetched.mime_type)
    if resolved.viewer_kind != "3d":
        raise UnsupportedFormatError("2D file provided to 3D viewer")

    # 変換条件が変わると同じ URL でも別結果になり得るため、profile も hash に含める。
    conversion_profile = "direct-stl" if resolved.normalized_extension == "stl" else "step-to-stl-v2"
    source_hash = hashlib.sha256(f"{fetched.source_url}|{conversion_profile}".encode("utf-8")).hexdigest()
    cached = job_store.get_cached_ready_job(source_hash)
    if cached:
        logger.info("viewer3d_cache_hit job=%s filename=%s", cached.id, cached.filename)
        return cached

    source_artifact = artifact_store.write_bytes("3d/sources", source_hash, resolved.normalized_extension, fetched.content)
    job = job_store.create_3d_job(
        source_url=fetched.source_url,
        source_url_hash=source_hash,
        filename=fetched.filename,
        source_extension=resolved.normalized_extension,
        source_mime_type=resolved.mime_type,
        source_artifact_path=source_artifact.relative_path,
    )
    job_store.mark_processing(job)

    if resolved.normalized_extension == "stl":
        # STL はそのまま表示できるので、変換ジョブを経由せず ready へ進める。
        ready_job = job_store.mark_ready(
            job,
            model_artifact_path=source_artifact.relative_path,
            model_format="stl",
        )
        logger.info("viewer3d_ready job=%s filename=%s", ready_job.id, ready_job.filename)
        return ready_job

    model_extension = "stl"
    output_artifact = artifact_store.reserve_path("3d/models", source_hash, model_extension)
    try:
        # STEP 系だけ backend に変換を委ね、viewer 本体は artifact の受け取りだけを知ればよい構造にする。
        convert_started_at = perf_counter()
        result = conversion_backend.convert(source_artifact.absolute_path, resolved.normalized_extension, output_artifact)
        convert_ms = (perf_counter() - convert_started_at) * 1000
        ready_job = job_store.mark_ready(
            job,
            model_artifact_path=result.artifact.relative_path,
            model_format=result.model_format,
        )
        artifact_size_bytes = result.artifact.absolute_path.stat().st_size if result.artifact.absolute_path.exists() else 0
        logger.info(
            "viewer3d_convert_complete job=%s format=%s convert_ms=%.2f artifact_bytes=%s",
            ready_job.id,
            result.model_format,
            convert_ms,
            artifact_size_bytes,
        )
    except ConversionError as exc:
        # failed にしておくと polling API が理由付きで UI へ返せる。
        job_store.mark_failed(job, exc.message)
        raise

    logger.info("viewer3d_ready job=%s filename=%s", ready_job.id, ready_job.filename)
    return ready_job
