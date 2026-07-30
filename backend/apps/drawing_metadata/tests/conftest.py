"""conftestの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。

テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
"""
import pytest


@pytest.fixture(autouse=True)
def configure_drawing_metadata_test_dependencies(settings, request):
    """DB許可の有無を辞書providerへ明示し、例外フォールバックへ依存しないテストにする。"""

    settings.DRAWING_METADATA_HANDOFF_MANIFEST = ""
    settings.DRAWING_METADATA_DICTIONARY_SOURCE = (
        "database" if request.node.get_closest_marker("django_db") else "seed"
    )


@pytest.fixture
def sample_registration_payload():
    return {
        "hostDrawingId": "sample-drawing-id",
        "filename": "sample_3d.icd",
        "sourcePath": r"C:\temp\sample_3d.icd",
        "sourceFormat": "icad",
    }
