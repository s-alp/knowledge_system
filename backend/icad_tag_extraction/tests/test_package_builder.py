"""最小引き渡しパッケージがDjangoなしで生成・実行できることを検証する。

失敗時は、配布対象一覧、pyproject、相対パス、不要なDjango依存の混入を確認する。
"""
from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = ROOT / "scripts" / "build_souya_tag_extraction_package.py"


def _load_builder_module():
    spec = importlib.util.spec_from_file_location("build_souya_tag_extraction_package", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"パッケージ生成スクリプトを読み込めません: {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_minimal_package_contains_contracts_and_runs_without_django(tmp_path: Path) -> None:
    builder = _load_builder_module()
    output_dir, archive_path = builder.build_package(tmp_path / "handoff")

    assert archive_path.is_file()
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert builder.validate_package(output_dir) == manifest
    manifest_paths = {item["path"] for item in manifest["files"]}
    assert "python/icad_tag_extraction/pipeline.py" in manifest_paths
    assert "schemas/icad-csharp-raw-extraction.v1.schema.json" in manifest_paths
    assert "dictionaries/initial-dictionaries.json" in manifest_paths
    assert "tests/python/test_distribution.py" in manifest_paths
    assert "scripts/start_windows_extraction_agent.ps1" in manifest_paths
    assert "docker/data/input.json" in manifest_paths
    assert (
        "docs/icad_remote_windows_agent_setup_for_souya_2026-07-30.md"
        in manifest_paths
    )
    assert (
        "docs/souya_tag_extraction_delivery_readiness_2026-07-30.md"
        in manifest_paths
    )
    assert (
        "docs/souya_tag_extraction_minimal_handoff_2026-07-30.md"
        in manifest_paths
    )
    assert not any(
        path.startswith("python/icad_tag_extraction/tests/")
        for path in manifest_paths
    )
    dictionaries = json.loads(
        (output_dir / "dictionaries" / "initial-dictionaries.json").read_text(
            encoding="utf-8"
        )
    )
    assert dictionaries["customer"] == {}
    assert dictionaries["project"] == {}
    assert not any(path.startswith("python/apps/") for path in manifest_paths)

    result_path = output_dir / "examples" / "cli_result.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(output_dir / "python")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "icad_tag_extraction",
            "--input",
            str(output_dir / "examples" / "raw" / "csharp_raw_2d.v1.json"),
            "--dictionary",
            str(output_dir / "dictionaries" / "initial-dictionaries.json"),
            "--output",
            str(result_path),
        ],
        cwd=output_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert result_path.is_file()
