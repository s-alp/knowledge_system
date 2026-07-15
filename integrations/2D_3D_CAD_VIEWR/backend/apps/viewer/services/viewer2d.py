from __future__ import annotations

"""2D session creation flow.

The service owns the input side effects for 2D files:
fetch or receive bytes, resolve the file type, store the artifact, and register
the session metadata that the API later serializes.
"""

import hashlib
import logging

from apps.viewer.domain.types import FetchedSource
from apps.viewer.models import Viewer2DSession
from apps.viewer.services.filetypes import FileTypeResolver
from apps.viewer.services.fetchers import SourceFetcher
from apps.viewer.services.jobs import JobStore
from apps.viewer.services.storage import ArtifactStore
from apps.viewer.services.tiff_pages import get_tiff_page_count

logger = logging.getLogger("apps.viewer")


def open_2d_session(
    *,
    source_url: str,
    fetcher: SourceFetcher,
    resolver: FileTypeResolver,
    artifact_store: ArtifactStore,
    job_store: JobStore,
) -> Viewer2DSession:
    """Fetch a remote 2D source and hand it to the shared session pipeline."""
    fetched = fetcher.fetch(source_url)
    return open_2d_session_from_source(
        fetched=fetched,
        resolver=resolver,
        artifact_store=artifact_store,
        job_store=job_store,
    )


def open_2d_session_from_source(
    *,
    fetched: FetchedSource,
    resolver: FileTypeResolver,
    artifact_store: ArtifactStore,
    job_store: JobStore,
) -> Viewer2DSession:
    """Create one stable session record from already fetched 2D bytes."""
    # 一時保存は viewer 共通なので、2D でも新規受付前に期限切れを掃除する。
    cleanup_artifacts(job_store, artifact_store)
    resolved = resolver.resolve(fetched.filename, fetched.mime_type)
    if resolved.viewer_kind != "2d":
        raise ValueError("3D file provided to 2D session")

    # URL / upload の違いに関係なく、同じ入力なら同じ保存パスになるよう source_url ベースで固定化する。
    source_hash = hashlib.sha256(fetched.source_url.encode("utf-8")).hexdigest()
    stored = artifact_store.write_bytes("2d", source_hash, resolved.normalized_extension, fetched.content)
    # TIFF のみ複数ページなので、toolbar が使う pageCount をここで確定する。
    page_count = get_tiff_page_count(fetched.content) if resolved.normalized_extension == "tiff" else 1
    session = job_store.create_2d_session(
        source_url=fetched.source_url,
        source_url_hash=source_hash,
        filename=fetched.filename,
        extension=resolved.normalized_extension,
        mime_type=resolved.mime_type,
        artifact_path=stored.relative_path,
        page_count=page_count,
    )
    logger.info("viewer2d_opened session=%s filename=%s", session.id, session.filename)
    return session


def cleanup_artifacts(job_store: JobStore, artifact_store: ArtifactStore) -> None:
    """Keep the transient viewer storage bounded before storing a new artifact."""
    source_paths, model_paths = job_store.cleanup_expired()
    # DB 削除後に残ったファイルだけを後追いで消し、viewer ストレージの肥大化を防ぐ。
    for path in source_paths + model_paths:
        artifact_store.delete_relative_path(path)
