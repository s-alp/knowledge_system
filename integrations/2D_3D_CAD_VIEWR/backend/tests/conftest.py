"""conftestの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。

テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
"""
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def configure_storage(settings, tmp_path: Path):
    settings.VIEWER_STORAGE_ROOT = tmp_path / "viewer-storage"
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.VIEWER_STEP_ENABLED = True
    settings.VIEWER_LOCAL_FILE_ENABLED = True
    return settings
