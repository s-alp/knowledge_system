"""創屋へ渡すCADタグ・属性抽出の最小ソースパッケージを再現可能に生成する。

実行目的:
- C#抽出、Django非依存Pythonコア、JSON Schema、初期辞書、例、文書だけを収集する。
- 全ファイルのSHA-256 manifestとZIPを作り、受け渡し時の欠落・差替えを検出可能にする。

安全性:
- 出力先はワークスペース配下に限定する。
- 同名フォルダまたはZIPが存在する場合は上書き・削除せず停止する。
- 元ファイルは読み取りのみで変更しない。
"""
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
SCRIPTS_ROOT = ROOT / "scripts"
RECIPIENT_DOCS_ROOT = ROOT / "handoff" / "souya_tag_extraction" / "recipient_docs"
RECIPIENT_DOCUMENT_PATHS = (
    "README.md",
    "docs/extraction_reference.md",
    "docs/integration_contract.md",
    "docs/icad_windows_operations.md",
)
DEFAULT_OUTPUT = ROOT / "output" / "souya_tag_extraction_minimal_2026-07-30"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from icad_tag_extraction.dictionary_provider import DICTIONARY_KINDS, SeedDictionaryProvider  # noqa: E402
from icad_tag_extraction.pipeline import process_extraction  # noqa: E402
from audit_souya_handoff_content import assert_external_handoff_safe  # noqa: E402


def _copy_tree(
    source: Path,
    destination: Path,
    *,
    extra_ignore_patterns: tuple[str, ...] = (),
) -> None:
    """生成物・キャッシュを除外してソースツリーをコピーする。"""

    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "bin",
            "obj",
            ".pytest_cache",
            "TestResults",
            *extra_ignore_patterns,
        ),
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    _write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_recipient_documents(output_dir: Path) -> None:
    """受領者向けとして管理する専用原稿だけを、固定の許可リストから同梱する。

    社内の設計資料や生成手順を自動収集すると、内部工程の説明がREADMEへ混入する。
    配布原稿を専用フォルダーへ分離し、追加文書もこの一覧への明示登録を必須にする。
    """

    for relative_path in RECIPIENT_DOCUMENT_PATHS:
        source = RECIPIENT_DOCS_ROOT / relative_path
        if not source.is_file():
            raise FileNotFoundError(f"受領者向け文書がありません: {source}")
        _copy_file(source, output_dir / relative_path)


def _python_pyproject() -> str:
    return """[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "icad-tag-extraction"
version = "1.1.0"
description = "ICAD/STEP/DXF raw metadata normalization and evidence-backed tag generation"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
icad-tag-extraction = "icad_tag_extraction.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["icad_tag_extraction*"]
"""


def _dockerfile() -> str:
    return """FROM python:3.11-slim

WORKDIR /app
COPY python /app/python
COPY dictionaries /app/dictionaries
RUN python -m pip install --no-cache-dir /app/python

ENTRYPOINT ["icad-tag-extraction"]
"""


def _docker_compose() -> str:
    return """services:
  tag-extraction:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    volumes:
      - ./data:/data
    command:
      - --input
      - /data/input.json
      - --dictionary
      - /app/dictionaries/initial-dictionaries.json
      - --output
      - /data/output.json
"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(output_dir: Path) -> dict:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        files.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "sizeBytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {
        "schemaVersion": "souya_tag_extraction_handoff_manifest.v1",
        "packageName": output_dir.name,
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "fileCount": len(files),
        "files": files,
    }


def validate_package(output_dir: Path) -> dict:
    """manifestと実ファイルの集合・サイズ・SHA-256が一致することを確認する。"""

    manifest_path = output_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifestがありません: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {item["path"]: item for item in manifest.get("files", [])}
    actual_paths = {
        path.relative_to(output_dir).as_posix()
        for path in output_dir.rglob("*")
        if (
            path.is_file()
            and path.name != "manifest.json"
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        )
    }
    if actual_paths != set(expected):
        missing = sorted(set(expected) - actual_paths)
        unexpected = sorted(actual_paths - set(expected))
        raise ValueError(
            f"manifestとファイル集合が一致しません。missing={missing}, unexpected={unexpected}"
        )

    for relative_path, entry in expected.items():
        path = output_dir / Path(relative_path)
        if path.stat().st_size != entry["sizeBytes"]:
            raise ValueError(f"manifestのサイズと一致しません: {relative_path}")
        if _sha256(path) != entry["sha256"]:
            raise ValueError(f"manifestのSHA-256と一致しません: {relative_path}")
    return manifest


def _validate_output_target(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f"出力先はワークスペース配下に限定します: {resolved}")
    archive_path = resolved.with_suffix(".zip")
    if resolved.exists():
        raise FileExistsError(f"出力先が既に存在します。上書きしません: {resolved}")
    if archive_path.exists():
        raise FileExistsError(f"ZIPが既に存在します。上書きしません: {archive_path}")


def build_package(
    output_dir: Path,
    *,
    guide_pdf: Path | None = None,
) -> tuple[Path, Path]:
    """正本ソースと確認済みPDFから最小フォルダとZIPを新規生成する。"""

    output_dir = output_dir.resolve()
    _validate_output_target(output_dir)
    output_dir.mkdir(parents=True)

    _copy_file(ROOT / "IcadExtraction.sln", output_dir / "csharp" / "IcadExtraction.sln")
    for project_name in (
        "IcadExtraction.Contracts",
        "IcadExtraction.SxNet",
        "IcadExtraction.Runner",
    ):
        _copy_tree(
            ROOT / "src" / project_name,
            output_dir / "csharp" / "src" / project_name,
        )
    for test_name in (
        "IcadExtraction.Contracts.Tests",
        "IcadExtraction.SxNet.Tests",
        "IcadExtraction.Runner.Tests",
    ):
        _copy_tree(
            ROOT / "tests" / test_name,
            output_dir / "csharp" / "tests" / test_name,
        )

    _copy_tree(
        BACKEND_ROOT / "icad_tag_extraction",
        output_dir / "python" / "icad_tag_extraction",
        # リポジトリ構成を前提とする生成テストは配布せず、下で配布専用テストを入れる。
        extra_ignore_patterns=("tests",),
    )
    _write_text(output_dir / "python" / "pyproject.toml", _python_pyproject())
    _write_text(
        output_dir / "python" / "requirements-dev.txt",
        "jsonschema==4.25.1\npytest==8.3.4\n",
    )
    _copy_file(
        ROOT / "handoff" / "souya_tag_extraction" / "test_distribution.py",
        output_dir / "tests" / "python" / "test_distribution.py",
    )

    _copy_tree(ROOT / "schemas" / "tag_extraction", output_dir / "schemas")
    seed_provider = SeedDictionaryProvider()
    _write_json(
        output_dir / "dictionaries" / "initial-dictionaries.json",
        {kind: seed_provider.get_mapping(kind) for kind in DICTIONARY_KINDS},
    )

    for fixture_name in ("csharp_raw_2d.v1.json", "csharp_raw_3d.v1.json"):
        source = ROOT / "examples" / "tag_extraction_contract" / fixture_name
        destination = output_dir / "examples" / "raw" / fixture_name
        _copy_file(source, destination)
        payload = json.loads(source.read_text(encoding="utf-8"))
        _write_json(
            output_dir / "examples" / "results" / fixture_name.replace("csharp_raw", "tagged_result"),
            process_extraction(payload),
        )

    _copy_file(
        ROOT / "scripts" / "convert_icad_standalone.ps1",
        output_dir / "scripts" / "convert_icad_standalone.ps1",
    )
    _copy_file(
        ROOT / "scripts" / "start_windows_extraction_agent.ps1",
        output_dir / "scripts" / "start_windows_extraction_agent.ps1",
    )
    _copy_recipient_documents(output_dir)

    copied_guide_pdf: tuple[Path, ...] = ()
    if guide_pdf is not None:
        resolved_guide_pdf = guide_pdf.resolve()
        if not resolved_guide_pdf.is_file():
            raise FileNotFoundError(f"説明PDFがありません: {resolved_guide_pdf}")
        if resolved_guide_pdf.suffix.lower() != ".pdf":
            raise ValueError(f"説明資料はPDFを指定してください: {resolved_guide_pdf}")
        package_guide_pdf = (
            output_dir
            / "docs"
            / "CADタグ属性抽出_創屋様向け利用ガイド.pdf"
        )
        _copy_file(resolved_guide_pdf, package_guide_pdf)
        copied_guide_pdf = (package_guide_pdf,)

    _write_text(output_dir / "docker" / "Dockerfile", _dockerfile())
    _write_text(output_dir / "docker" / "docker-compose.yml", _docker_compose())
    _copy_file(
        ROOT / "examples" / "tag_extraction_contract" / "csharp_raw_2d.v1.json",
        output_dir / "docker" / "data" / "input.json",
    )
    # 承認済み初期辞書は許可する一方、文書・PDF・サンプルへの社内情報混入は生成前に拒否する。
    assert_external_handoff_safe(output_dir, pdfs=copied_guide_pdf)
    _write_json(output_dir / "manifest.json", _manifest(output_dir))
    validate_package(output_dir)

    archive_base = output_dir.with_suffix("")
    archive_path = Path(
        shutil.make_archive(
            str(archive_base),
            "zip",
            root_dir=output_dir.parent,
            base_dir=output_dir.name,
        )
    )
    return output_dir, archive_path


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="新規作成するパッケージフォルダ。既存パスは拒否する。",
    )
    parser.add_argument(
        "--guide-pdf",
        type=Path,
        required=True,
        help="外部共有監査済みの説明PDF。docs配下へ同梱する。",
    )
    args = parser.parse_args()
    output_dir, archive_path = build_package(
        args.output,
        guide_pdf=args.guide_pdf,
    )
    print(json.dumps(
        {
            "outputDirectory": str(output_dir),
            "archive": str(archive_path),
            "manifest": str(output_dir / "manifest.json"),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
