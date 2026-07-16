from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UI_OUTPUT = ROOT / "output" / "entity_ui_delivery_readiness"
DEFAULT_LLM_PROBE = (
    ROOT
    / "output"
    / "live_extracts"
    / "title_block_llm_probe_2026-07-14"
    / "gemini_probe_current_normalization_2026-07-17.json"
)
DEFAULT_REVIEW_SUMMARY = ROOT / "output" / "souya_handoff" / "drawing_metadata_fixture_all_shared_review_summary_2026-07-17.json"
BACKEND_DIR = ROOT / "backend"
BACKEND_VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
FRONTEND_DIR = ROOT / "integrations" / "2D_3D_CAD_VIEWR" / "frontend"

ACTIVE_HANDOFF_DOCS = [
    ROOT / "docs" / "icad_2d_3d_extraction_capability_matrix_2026-07-14.md",
    ROOT / "docs" / "icad_entity_operations_and_quality_handoff_2026-07-16.md",
    ROOT / "docs" / "souya_icad_tag_attribute_handoff_2026-07-14.md",
    ROOT / "docs" / "icad_tag_selection_and_viewer_ui_spec_2026-07-15.md",
]

ACTIVE_SOURCE_TEXT_PATHS = [
    ROOT / "src",
    ROOT / "backend" / "apps" / "drawing_metadata" / "api",
    ROOT / "backend" / "apps" / "drawing_metadata" / "management",
    ROOT / "backend" / "apps" / "drawing_metadata" / "models.py",
    ROOT / "backend" / "apps" / "drawing_metadata" / "services",
    ROOT / "backend" / "apps" / "drawing_metadata" / "templates",
    ROOT / "integrations" / "2D_3D_CAD_VIEWR" / "frontend" / "src",
    ROOT / "integrations" / "2D_3D_CAD_VIEWR" / "backend" / "apps" / "viewer",
    ROOT / "integrations" / "2D_3D_CAD_VIEWR" / "handover_package" / "frontend" / "src",
    ROOT / "integrations" / "2D_3D_CAD_VIEWR" / "handover_package" / "backend" / "apps" / "viewer",
]

STALE_DOC_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"API_KEY_INVALID",
        r"採用率未確認",
        r"gemini_probe_after_parse_fallback_2026-07-15",
        r"positive recall\s*0\.5000",
        r"classification positive recall\s*\|\s*0\.5000",
        r"2026-07-16に共有抽出から10ファイル",
        r"創屋連携データ確認",
        r"ユーザー画面には表示しません",
        r"通常画面へ出さず",
        r"\|\s*PRFX\s*\|[^\n]*\|\s*未実装\s*\|",
        r"\|\s*ユニット番号\s*\|[^\n]*\|\s*未実装\s*\|",
        r"\|\s*(幾何公差|溶接|バルーン)\s*\|[^\n]*\|\s*summaryのみ\s*\|",
        r"\|\s*(幾何公差|溶接|バルーン)\s*\|[^\n]*構造化未実装",
        r"\|\s*シンボル / 矢視 / 切断線\s*\|[^\n]*未実装",
        r"\|\s*慣性モーメント\s*\|[^\n]*未実装",
        r"\|\s*(スプライン|ハッチング)\s*\|[^\n]*未実装",
        r"SxGeomSpline2D.*未対応 warning",
        r"作成日/改訂日/承認日の分類は未実装",
    )
]

SOURCE_GUARDRAIL_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"not implemented yet",
        r"NotImplementedError",
        r"\bTODO\b",
        r"\bFIXME\b",
        r"未実装",
        r"確認待ち",
        r"材質要確認:",
        r"創屋連携データ確認",
        r"ユーザー画面には表示しません",
        r"通常画面へ出さず",
        r"未対応" r"の操作です。",
    )
]

SOURCE_GUARDRAIL_SUFFIXES = {".cs", ".py", ".ts", ".tsx", ".html"}


def _command_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _python_executable() -> str:
    if BACKEND_VENV_PYTHON.is_file():
        return str(BACKEND_VENV_PYTHON)
    return sys.executable


def _run_gate(name: str, command: list[str], *, cwd: Path = ROOT) -> dict:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=_command_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        return {
            "name": name,
            "command": command,
            "returnCode": None,
            "passed": False,
            "stdoutTail": "",
            "stderrTail": f"command not found: {exc.filename}",
        }
    return {
        "name": name,
        "command": command,
        "returnCode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdoutTail": "\n".join(completed.stdout.splitlines()[-40:]),
        "stderrTail": "\n".join(completed.stderr.splitlines()[-40:]),
    }


def _scan_stale_docs(paths: Iterable[Path]) -> dict:
    findings: list[dict] = []
    for path in paths:
        if not path.is_file():
            findings.append({"file": str(path), "line": None, "pattern": "missing_file", "text": ""})
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for pattern in STALE_DOC_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        {
                            "file": str(path),
                            "line": line_number,
                            "pattern": pattern.pattern,
                            "text": line.strip(),
                        }
                    )
    return {
        "name": "stale_handoff_doc_search",
        "passed": not findings,
        "findingCount": len(findings),
        "findings": findings,
    }


def _iter_source_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file():
            if path.suffix in SOURCE_GUARDRAIL_SUFFIXES:
                yield path
            continue
        if not path.is_dir():
            continue
        for child in path.rglob("*"):
            if not child.is_file() or child.suffix not in SOURCE_GUARDRAIL_SUFFIXES:
                continue
            if ".test." in child.name or ".spec." in child.name:
                continue
            parts = set(child.parts)
            if {"bin", "obj", "node_modules", "dist", "__pycache__"}.intersection(parts):
                continue
            yield child


def _scan_source_text_guardrails(paths: Iterable[Path]) -> dict:
    findings: list[dict] = []
    for path in _iter_source_files(paths):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for pattern in SOURCE_GUARDRAIL_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        {
                            "file": str(path),
                            "line": line_number,
                            "pattern": pattern.pattern,
                            "text": line.strip(),
                        }
                    )
    return {
        "name": "source_text_guardrails",
        "passed": not findings,
        "findingCount": len(findings),
        "findings": findings,
    }


def _git_status_gate(require_clean: bool) -> dict:
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    dirty = bool(completed.stdout.strip())
    return {
        "name": "git_worktree_clean",
        "returnCode": completed.returncode,
        "passed": completed.returncode == 0 and (not require_clean or not dirty),
        "required": require_clean,
        "dirty": dirty,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _npm_run_command(script_name: str) -> list[str]:
    if os.name == "nt":
        return ["pwsh", "-NoLogo", "-NoProfile", "-Command", f"npm run {script_name}"]
    return ["npm", "run", script_name]


def _test_gates(python: str) -> list[dict]:
    return [
        _run_gate("backend_django_check", [python, "manage.py", "check"], cwd=BACKEND_DIR),
        _run_gate(
            "backend_drawing_metadata_pytest",
            [python, "-m", "pytest", "apps/drawing_metadata/tests"],
            cwd=BACKEND_DIR,
        ),
        _run_gate("dotnet_build", ["dotnet", "build", str(ROOT / "IcadExtraction.sln"), "-c", "Debug"], cwd=ROOT),
        _run_gate("dotnet_test", ["dotnet", "test", str(ROOT / "IcadExtraction.sln"), "-c", "Debug", "--no-build"], cwd=ROOT),
        _run_gate("frontend_vitest", _npm_run_command("test"), cwd=FRONTEND_DIR),
        _run_gate("frontend_build", _npm_run_command("build"), cwd=FRONTEND_DIR),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ICAD delivery readiness gates for the current workspace.")
    parser.add_argument("--include-ui", action="store_true", help="Run Playwright UI verification against an already running app.")
    parser.add_argument("--include-tests", action="store_true", help="Run backend, C# and frontend automated test/build gates.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5173/", help="Frontend URL for --include-ui.")
    parser.add_argument("--ui-output-dir", default=str(DEFAULT_UI_OUTPUT), help="Screenshot/output directory for --include-ui.")
    parser.add_argument("--require-clean", action="store_true", help="Fail when git status --short is not clean.")
    parser.add_argument("--output", help="Optional JSON path for the readiness result.")
    args = parser.parse_args()

    python = _python_executable()
    gates = [
        _run_gate("shared_icad_completion", [python, str(ROOT / "scripts" / "audit_shared_icad_completion.py")]),
        _run_gate("drawing_metadata_job_state", [python, str(ROOT / "scripts" / "audit_drawing_metadata_job_state.py")]),
        _run_gate("tag_quality", [python, str(ROOT / "scripts" / "audit_tag_quality.py")]),
        _run_gate(
            "knowledge_payload_attribute_quality",
            [python, str(ROOT / "scripts" / "audit_knowledge_payload_attribute_quality.py")],
        ),
        _run_gate(
            "handoff_review_summary",
            [python, str(ROOT / "scripts" / "validate_drawing_handoff_review_summary.py"), str(DEFAULT_REVIEW_SUMMARY)],
        ),
        _run_gate("mass_weight_format", [python, str(ROOT / "scripts" / "audit_mass_weight_format.py")]),
        _run_gate("llm_title_block_guardrails", [python, str(ROOT / "scripts" / "audit_llm_title_block_guardrails.py")]),
        _run_gate(
            "llm_probe_evaluation",
            [python, str(ROOT / "scripts" / "evaluate_title_block_llm_probe.py"), str(DEFAULT_LLM_PROBE)],
        ),
    ]
    gates.append(_scan_stale_docs(ACTIVE_HANDOFF_DOCS))
    gates.append(_scan_source_text_guardrails(ACTIVE_SOURCE_TEXT_PATHS))
    gates.append(_git_status_gate(args.require_clean))

    if args.include_tests:
        gates.extend(_test_gates(python))

    if args.include_ui:
        gates.append(
            _run_gate(
                "icad_entity_ui",
                [
                    "node",
                    str(ROOT / "scripts" / "verify_icad_entity_ui.mjs"),
                    args.base_url,
                    args.ui_output_dir,
                ],
            )
        )

    failed = [gate for gate in gates if not gate.get("passed")]
    payload = {
        "schemaVersion": "icad_delivery_readiness_audit.v1",
        "gateCount": len(gates),
        "failedGateCount": len(failed),
        "gatePassed": not failed,
        "gates": gates,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if payload["gatePassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
