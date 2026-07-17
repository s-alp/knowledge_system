from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DELIVERY_AUDIT = ROOT / "scripts" / "audit_icad_delivery_readiness.py"
OPERATIONS_HANDOFF = ROOT / "docs" / "icad_entity_operations_and_quality_handoff_2026-07-16.md"
SOUYA_HANDOFF = ROOT / "docs" / "souya_icad_tag_attribute_handoff_2026-07-14.md"
SOUYA_PARTS = ROOT / "docs" / "souya_icad_tag_attribute_handoff_2026-07-14_parts"
TASKLIST = ROOT / "tasklist.md"


REQUIREMENTS: list[dict[str, Any]] = [
    {
        "id": "shared_39_and_one_icd_unit",
        "description": "共有39件を固定manifestで扱い、1 ICDを1登録単位にする。",
        "gates": ["shared_icad_completion", "knowledge_payload_attribute_quality"],
        "docs": [
            (OPERATIONS_HANDOFF, "登録単位は `1 ICD = 1件`"),
            (OPERATIONS_HANDOFF, "固定manifestで共有39件"),
        ],
    },
    {
        "id": "two_d_views_layers_print_frames",
        "description": "2Dの全ビュー、レイヤー、複数図面、印刷枠内外を監査する。",
        "gates": ["two_d_view_layer_print_frame_coverage"],
        "docs": [
            (TASKLIST, "2Dビュー・レイヤー・印刷枠カバレッジゲート"),
            (SOUYA_PARTS / "souya_icad_tag_attribute_handoff_2026-07-14_10_shared_39_status.md", "全ビュー210"),
            (SOUYA_PARTS / "souya_icad_tag_attribute_handoff_2026-07-14_10_shared_39_status.md", "印刷枠内"),
        ],
    },
    {
        "id": "three_d_structure_material_mass_part_info",
        "description": "3D構成、材質、質量、パーツ付加情報を監査する。",
        "gates": ["three_d_structure_material_mass_coverage"],
        "docs": [
            (TASKLIST, "3D構成・材質・質量・パーツ付加情報カバレッジゲート"),
            (OPERATIONS_HANDOFF, "パーツ付加情報あり"),
            (OPERATIONS_HANDOFF, "共有39件中38件は質量取得あり"),
        ],
    },
    {
        "id": "unextracted_reason_and_reextract_condition",
        "description": "未抽出や取得不可状態を理由と再抽出条件つきで残す。",
        "gates": [
            "drawing_metadata_job_state",
            "two_d_view_layer_print_frame_coverage",
            "three_d_structure_material_mass_coverage",
        ],
        "docs": [
            (OPERATIONS_HANDOFF, "値を捏造せず"),
            (SOUYA_PARTS / "souya_icad_tag_attribute_handoff_2026-07-14_10_shared_39_status.md", "2D要素なし"),
        ],
    },
    {
        "id": "knowledge_entity_ui_integration",
        "description": "製品・装置・ユニット、部品、図面管理を統合ビューワーへ合わせる。",
        "gates": ["icad_entity_ui", "frontend_vitest", "viewer_backend_pytest"],
        "docs": [
            (OPERATIONS_HANDOFF, "2D・3Dビューワー統合フロント"),
            (OPERATIONS_HANDOFF, "製品・部品詳細"),
            (OPERATIONS_HANDOFF, "図面紐づけ候補38件"),
        ],
    },
    {
        "id": "business_status_separated_from_extraction_review",
        "description": "抽出内部状態を利用者向け業務状態から分離する。",
        "gates": ["icad_entity_ui"],
        "docs": [
            (OPERATIONS_HANDOFF, "業務状態へ混ぜない"),
            (TASKLIST, "業務ステータスから"),
        ],
    },
    {
        "id": "tag_quality_and_evidence",
        "description": "検索・分類に有効なタグだけを採用し、source/evidence/reason/confidenceを必須化する。",
        "gates": ["tag_quality", "knowledge_payload_attribute_quality"],
        "docs": [
            (OPERATIONS_HANDOFF, "タグ採用規則"),
            (OPERATIONS_HANDOFF, "取得元欠落0件"),
            (TASKLIST, "source/evidence/confidence/reason欠落0件"),
        ],
    },
    {
        "id": "two_d_three_d_reconciliation",
        "description": "2D/3D差異、採用値、要確認理由を追跡する。",
        "gates": ["knowledge_payload_attribute_quality", "icad_entity_ui"],
        "docs": [
            (OPERATIONS_HANDOFF, "reconciledAttributes"),
            (SOUYA_PARTS / "souya_icad_tag_attribute_handoff_2026-07-14_07a_api_contract.md", "2D/3D照合"),
        ],
    },
    {
        "id": "mass_weight_kg_two_decimals",
        "description": "質量・重量をkg、小数点以下2桁へ統一する。",
        "gates": ["mass_weight_format", "three_d_structure_material_mass_coverage"],
        "docs": [
            (OPERATIONS_HANDOFF, "表示単位はkgへ統一"),
            (OPERATIONS_HANDOFF, "`0.49 kg` 形式"),
        ],
    },
    {
        "id": "gemini_low_temperature_guarded",
        "description": "Geminiを低温度の曖昧分類補助に限定し、実API評価と誤採用防止を監査する。",
        "gates": ["llm_title_block_guardrails", "llm_probe_evaluation"],
        "docs": [
            (OPERATIONS_HANDOFF, "温度は `0.0`"),
            (OPERATIONS_HANDOFF, "CADに存在しない値の生成"),
            (TASKLIST, "Geminiの追加採用値0件"),
        ],
    },
    {
        "id": "no_souya_production_db_write",
        "description": "創屋本番DBへの登録・変更・削除を行わない境界を明示する。",
        "gates": ["stale_handoff_doc_search", "source_text_guardrails"],
        "docs": [
            (OPERATIONS_HANDOFF, "創屋本番DBへの登録、変更、削除は一切行わない"),
            (SOUYA_HANDOFF, "本番ナレッジシステムへの登録、変更、削除は創屋側"),
        ],
    },
    {
        "id": "handoff_docs_and_beginner_comments",
        "description": "創屋が移植できるAPI仕様、データ契約、初心者向け説明、分冊資料を保持する。",
        "gates": ["stale_handoff_doc_search", "handoff_doc_size_guardrails"],
        "docs": [
            (SOUYA_HANDOFF, "API/fixture の最小契約案"),
            (SOUYA_PARTS / "souya_icad_tag_attribute_handoff_2026-07-14_07a_api_contract.md", "初心者でも確認できる"),
            (TASKLIST, "ファイル長制限で開けない状態を避ける"),
        ],
    },
    {
        "id": "automated_tests_chrome_and_clean_tree",
        "description": "バックエンド、フロントエンド、C#、Chrome UI、作業ツリーcleanを最終監査に含める。",
        "gates": [
            "backend_django_check",
            "backend_drawing_metadata_pytest",
            "dotnet_build",
            "dotnet_test",
            "viewer_backend_pytest",
            "frontend_vitest",
            "frontend_build",
            "icad_entity_ui",
            "git_worktree_clean",
        ],
        "docs": [
            (TASKLIST, "--include-tests --include-ui --require-clean"),
            (OPERATIONS_HANDOFF, "Chrome実操作"),
        ],
    },
    {
        "id": "no_unimplemented_mock_or_stale_terms",
        "description": "未実装、モック、古い未完表現、放置ファイルを監査で落とす。",
        "gates": ["stale_handoff_doc_search", "source_text_guardrails", "git_worktree_clean"],
        "docs": [
            (TASKLIST, "旧見出し・旧予定表現"),
            (TASKLIST, "未追跡0件"),
        ],
    },
]


def _delivery_audit_text() -> str:
    return DELIVERY_AUDIT.read_text(encoding="utf-8")


def _declared_gate_names(text: str) -> set[str]:
    return set(re.findall(r'_run_gate\(\s*"([^"]+)"', text)) | set(
        re.findall(r'"name":\s*"([^"]+)"', text)
    )


def _read_doc(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _row_for_requirement(requirement: dict[str, Any], gate_names: set[str]) -> dict[str, Any]:
    missing_gates = [gate for gate in requirement["gates"] if gate not in gate_names]
    missing_docs: list[dict[str, str]] = []
    for path, token in requirement["docs"]:
        if not path.is_file():
            missing_docs.append({"file": str(path), "token": token, "reason": "missing_file"})
            continue
        text = _read_doc(path)
        if token not in text:
            missing_docs.append({"file": str(path), "token": token, "reason": "missing_token"})

    return {
        "id": requirement["id"],
        "description": requirement["description"],
        "requiredGates": requirement["gates"],
        "missingGates": missing_gates,
        "requiredDocTokens": [{"file": str(path), "token": token} for path, token in requirement["docs"]],
        "missingDocTokens": missing_docs,
        "passed": not missing_gates and not missing_docs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ゴール要求と納品監査・引継ぎ資料のカバレッジを確認します。")
    parser.add_argument("--output", help="JSON出力先。省略時は標準出力します。")
    args = parser.parse_args()

    audit_text = _delivery_audit_text()
    gate_names = _declared_gate_names(audit_text)
    rows = [_row_for_requirement(requirement, gate_names) for requirement in REQUIREMENTS]
    missing_rows = [row for row in rows if not row["passed"]]
    result = {
        "schemaVersion": "icad_goal_completion_coverage_audit.v1",
        "requirementCount": len(rows),
        "coveredRequirementCount": sum(row["passed"] for row in rows),
        "missingRequirementCount": len(missing_rows),
        "gateCountInReadinessAudit": len(gate_names),
        "gatePassed": not missing_rows,
        "requirements": rows,
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if result["gatePassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
