"""創屋向け外部共有監査が漏えい候補を拒否し、安全な架空例を許可することを確認する。"""

from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import sys


ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = ROOT / "scripts" / "audit_souya_handoff_content.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "audit_souya_handoff_content",
        AUDIT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"外部共有監査を読み込めません: {AUDIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit_external_handoff = _load_audit_module().audit_external_handoff


def _write_dictionary(root: Path, customer: dict | None = None) -> None:
    path = root / "dictionaries" / "initial-dictionaries.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "customer": customer or {},
                "equipment_category": {},
                "project": {},
                "maker": {},
                "spec": {},
                "heat_treatment": {},
                "part_name": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_external_handoff_audit_accepts_synthetic_package(tmp_path: Path) -> None:
    _write_dictionary(tmp_path)
    (tmp_path / "README.md").write_text(
        "架空例: C:\\sample\\customer-a\\SAMPLE-001.icd / 顧客A",
        encoding="utf-8",
    )

    assert audit_external_handoff(tmp_path) == []


def test_external_handoff_audit_accepts_distributed_dictionary_but_rejects_internal_path(
    tmp_path: Path,
) -> None:
    _write_dictionary(tmp_path, {"配布承認済み顧客": ["customer-a"]})
    (tmp_path / "README.md").write_text(
        "社内パス J:\\project\\drawing.icd",
        encoding="utf-8",
    )

    findings = audit_external_handoff(tmp_path)

    reasons = {finding.reason for finding in findings}
    assert reasons == {"社内ネットワークドライブ"}


def test_external_handoff_audit_rejects_internal_process_wording_in_markdown(
    tmp_path: Path,
) -> None:
    _write_dictionary(tmp_path)
    (tmp_path / "README.md").write_text(
        "本リポジトリ側の受入確認後に生成スクリプトを実行します。",
        encoding="utf-8",
    )

    findings = audit_external_handoff(tmp_path)

    assert {
        finding.evidence
        for finding in findings
        if finding.reason == "受領者向け文書に内部作業表現"
    } == {"リポジトリ", "生成スクリプト", "受入確認"}
