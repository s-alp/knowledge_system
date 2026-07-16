from __future__ import annotations

import os
from pathlib import Path


WINDOWS_FILENAME_LIMIT = 255
WINDOWS_LEGACY_PATH_LIMIT = 259


def filename_length_error(filename: str) -> str:
    return (
        f"ICADファイル名が長すぎます。SXNETへ渡すファイル名は"
        f"{WINDOWS_FILENAME_LIMIT}文字以下にしてください。"
        f"現在の文字数: {len(filename)}。"
        "短いファイル名へ変更してから再登録してください。"
    )


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


def validate_icad_filename_length(filename: str) -> None:
    if len(filename) > WINDOWS_FILENAME_LIMIT:
        raise ValueError(filename_length_error(filename))


def requires_sxnet_staged_input(path: str | Path) -> bool:
    """SXNETへ直接渡すには危険な長さなら、短い一時パスへの退避を要求する。"""
    return len(str(path)) > WINDOWS_LEGACY_PATH_LIMIT


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
