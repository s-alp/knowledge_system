"""test_llm_probe_evaluation_scriptの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。

テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
"""
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "evaluate_title_block_llm_probe.py"


def _write_probe(path: Path, *, classifications: list[dict]) -> None:
    payload = {
        "classified": True,
        "files": [
            {
                "file": "sample_2d.json",
                "candidate_preview": [
                    {
                        "field": "material",
                        "value": "SUS304",
                        "evidence_text": "材質 SUS304",
                    }
                ],
                "gemini": {
                    "classifications": classifications,
                    "accepted": [],
                },
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_llm_probe_evaluation_fails_when_positive_candidate_is_missed(tmp_path):
    probe_path = tmp_path / "missed-positive.json"
    _write_probe(
        probe_path,
        classifications=[
            {
                "index": 0,
                "field": None,
                "confidence": "low",
                "reason": "missed",
            }
        ],
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(probe_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 1
    assert "incomplete_classification" in completed.stdout
    assert '"classificationMissedPositiveCount": 1' in completed.stdout


def test_llm_probe_evaluation_passes_when_positive_candidate_is_classified(tmp_path):
    probe_path = tmp_path / "classified-positive.json"
    _write_probe(
        probe_path,
        classifications=[
            {
                "index": 0,
                "field": "material",
                "confidence": "high",
                "reason": "material grade",
            }
        ],
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(probe_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0
    assert '"classificationPrecision": 1.0' in completed.stdout
    assert '"classificationPositiveRecall": 1.0' in completed.stdout
