from __future__ import annotations

"""Transient artifact storage for source files and converted models."""

import shutil
from dataclasses import dataclass
from pathlib import Path

from apps.viewer.domain.types import StoredArtifact


@dataclass(slots=True)
class ArtifactStore:
    root: Path

    def ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, category: str, stem: str, extension: str, content: bytes) -> StoredArtifact:
        # DB には relative path だけを持たせ、保存先の実パスは store 側で吸収する。
        self.ensure_dirs()
        directory = self.root / category
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{stem}.{extension}"
        path.write_bytes(content)
        return StoredArtifact(relative_path=str(path.relative_to(self.root)), absolute_path=path)

    def reserve_path(self, category: str, stem: str, extension: str) -> StoredArtifact:
        # 変換 backend には書き込み先だけを渡し、保存ルールはここで統一する。
        self.ensure_dirs()
        directory = self.root / category
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{stem}.{extension}"
        return StoredArtifact(relative_path=str(path.relative_to(self.root)), absolute_path=path)

    def copy_file(self, source: Path, category: str, stem: str, extension: str) -> StoredArtifact:
        target = self.reserve_path(category, stem, extension)
        shutil.copy2(source, target.absolute_path)
        return target

    def delete_relative_path(self, relative_path: str) -> None:
        if not relative_path:
            return
        path = self.root / relative_path
        # cleanup は複数経路から呼ばれるため、既に無ければそのまま抜ける。
        if path.exists():
            path.unlink()
