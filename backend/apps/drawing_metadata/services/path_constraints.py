from __future__ import annotations

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
        "短い作業フォルダへコピーして再登録してください。"
    )


def validate_icad_path_length(path: str | Path) -> None:
    if len(str(path)) > WINDOWS_LEGACY_PATH_LIMIT:
        raise ValueError(path_length_error(path))


def validate_icad_filename_length(filename: str) -> None:
    if len(filename) > WINDOWS_FILENAME_LIMIT:
        raise ValueError(filename_length_error(filename))
