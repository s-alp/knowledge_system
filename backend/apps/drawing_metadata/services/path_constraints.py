from __future__ import annotations

import hashlib
import os
from pathlib import Path


WINDOWS_FILENAME_LIMIT = 255
WINDOWS_LEGACY_PATH_LIMIT = 259


def path_length_error(path: str | Path) -> str:
    path_text = str(path)
    return (
        f"ICADファイルのパスが長すぎます。SXNETへ渡すパスは"
        f"{WINDOWS_LEGACY_PATH_LIMIT}文字以下にしてください。"
        f"現在の文字数: {len(path_text)}。"
        "現行抽出では短い一時パスへ退避して開きます。"
    )


def validate_icad_path_length(path: str | Path) -> None:
    if len(str(path)) > WINDOWS_LEGACY_PATH_LIMIT:
        raise ValueError(path_length_error(path))


def normalize_icad_display_filename(filename: str) -> str:
    """DBに保存する表示用ファイル名を、拡張子を残して255文字以内へ丸める。"""
    normalized = filename.strip() or "input.icd"
    if len(normalized) <= WINDOWS_FILENAME_LIMIT:
        return normalized

    suffix = Path(normalized).suffix or ".icd"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
    reserved = len(suffix) + len(digest) + 1
    stem_limit = max(1, WINDOWS_FILENAME_LIMIT - reserved)
    return f"{Path(normalized).stem[:stem_limit]}-{digest}{suffix}"


def sxnet_staging_reasons(path: str | Path, *, filename: str = "") -> list[str]:
    """SXNETへ直接渡すには危険な理由を、後から説明できる形で返す。"""
    reasons: list[str] = []
    if len(str(path)) > WINDOWS_LEGACY_PATH_LIMIT:
        reasons.append("path_length")
    if filename and len(filename) > WINDOWS_FILENAME_LIMIT:
        reasons.append("filename_length")
    return reasons


def requires_sxnet_staged_input(path: str | Path, *, filename: str = "") -> bool:
    """SXNETへ直接渡すには危険な長さなら、短い一時パスへの退避を要求する。"""
    return bool(sxnet_staging_reasons(path, filename=filename))


def icad_source_path_exists(path: str | Path) -> bool:
    path_text = str(path)
    candidates = [path_text]
    if os.name == "nt":
        candidates.append(_to_extended_windows_path(path_text))

    for candidate in candidates:
        try:
            if Path(candidate).exists():
                return True
        except OSError:
            continue
    return False


def _to_extended_windows_path(path: str) -> str:
    if path.startswith("\\\\?\\"):
        return path
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path
