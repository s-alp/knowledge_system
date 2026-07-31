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
VERIFIER_PATH = ROOT / "scripts" / "verify_souya_tag_extraction_handoff.py"


def _load_builder_module():
    spec = importlib.util.spec_from_file_location("build_souya_tag_extraction_package", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"パッケージ生成スクリプトを読み込めません: {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_verifier_module():
    """最終成果物の専用検証スクリプトを、CLI実行せず読み込む。"""

    spec = importlib.util.spec_from_file_location(
        "verify_souya_tag_extraction_handoff",
        VERIFIER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"パッケージ検証スクリプトを読み込めません: {VERIFIER_PATH}")
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
    assert "README.md" in manifest_paths
    assert "docs/extraction_reference.md" in manifest_paths
    assert "docs/integration_contract.md" in manifest_paths
    assert "docs/icad_windows_operations.md" in manifest_paths
    assert {
        path
        for path in manifest_paths
        if path.endswith(".md")
    } == set(builder.RECIPIENT_DOCUMENT_PATHS)
    assert not any("delivery_readiness" in path for path in manifest_paths)
    assert not any("minimal_handoff" in path for path in manifest_paths)
    assert not any("api_design" in path for path in manifest_paths)
    assert not any(
        path.startswith("python/icad_tag_extraction/tests/")
        for path in manifest_paths
    )
    dictionaries = json.loads(
        (output_dir / "dictionaries" / "initial-dictionaries.json").read_text(
            encoding="utf-8"
        )
    )
    assert dictionaries["customer"] == {
        "コマツ小山": ["コマツ小山", "komatsu koyama"],
        "広島アルミ": ["広島アルミ", "hiroshima alumi"],
        "澁谷工業": ["澁谷工業", "shibuya"],
    }
    assert dictionaries["project"] == {}
    assert dictionaries["spec"]["SES"] == ["SES", "ses"]
    assert not any(path.startswith("python/apps/") for path in manifest_paths)
    pyproject = (output_dir / "python" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    dockerfile = (output_dir / "docker" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    assert 'version = "1.2.0"' in pyproject
    assert 'requires-python = ">=3.11"' in pyproject
    assert dockerfile.startswith("FROM python:3.11-slim\n")
    recipient_readme = (output_dir / "README.md").read_text(encoding="utf-8")
    for required_navigation in (
        "## 1. 目的別・資料の見方",
        "### 1.1 最初に読む順序",
        "### 1.2 目的別の参照先",
        "### 1.3 各資料に書かれていること・書かれていないこと",
        "### 1.4 担当外の資料は読み飛ばしてよい",
        "### 1.5 文書以外の重要なファイル",
        "### 1.6 問題が起きたときの確認先",
        "`schemas`",
        "`examples`",
        "`dictionaries`",
        "`manifest.json`",
    ):
        assert required_navigation in recipient_readme
    extraction_reference = (
        output_dir / "docs" / "extraction_reference.md"
    ).read_text(encoding="utf-8")
    assert "`paint_instruction_tokens`" in extraction_reference
    assert "`User_WBHNA`" in extraction_reference
    integration_contract = (
        output_dir / "docs" / "integration_contract.md"
    ).read_text(encoding="utf-8")
    assert "結果Schemaは`1.1.0`" in integration_contract
    assert "正規化規則は`1.2.0`" in integration_contract
    recipient_markdown = "\n".join(
        (output_dir / path).read_text(encoding="utf-8")
        for path in sorted(manifest_paths)
        if path.endswith(".md")
    )
    for internal_wording in (
        "リポジトリ",
        "Git履歴",
        "創屋側から依頼",
        "外部共有監査",
        "内部監査",
        "生成スクリプト",
        "受入確認",
        "初心者",
    ):
        assert internal_wording not in recipient_markdown

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


def test_final_verifier_compares_exact_zip_without_modifying_package(
    tmp_path: Path,
) -> None:
    """ZIP検証が配布フォルダーを汚さず、全ファイル一致を確認できる。"""

    builder = _load_builder_module()
    verifier = _load_verifier_module()
    output_dir, archive_path = builder.build_package(tmp_path / "handoff")
    before = {
        path.relative_to(output_dir).as_posix(): verifier._file_sha256(path)
        for path in output_dir.rglob("*")
        if path.is_file()
    }

    verifier.verify_no_generated_artifacts(output_dir)
    assert verifier.verify_archive_matches_directory(output_dir, archive_path) == len(
        before
    )

    after = {
        path.relative_to(output_dir).as_posix(): verifier._file_sha256(path)
        for path in output_dir.rglob("*")
        if path.is_file()
    }
    assert after == before
