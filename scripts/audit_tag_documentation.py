"""タグ抽出・付与関連ドキュメントと現行コードの対応を監査する。

目的:
    現行正本文書、関連文書索引、コード上のモデル・API・設定・タグ規則が
    同時に更新されているかを機械的に確認する。

前提:
    リポジトリルートから ``python scripts\\audit_tag_documentation.py`` で実行する。
    外部URLやワークスペース外の絶対パスは存在確認の対象にしない。

失敗時:
    欠落ファイル、壊れたローカルMarkdownリンク、コード識別子との不一致を表示して
    終了コード1を返す。警告だけの場合は終了コード0を返す。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
HANDOFF_DOCS = ROOT / "handoff/claude_cloud"
CURRENT_SPEC = DOCS / "tag_extraction_and_assignment_current_spec_2026-07-29.md"
INDEX = DOCS / "tag_extraction_documentation_index_2026-07-29.md"

REQUIRED_FILES = (
    CURRENT_SPEC,
    INDEX,
    DOCS / "extraction_result_schema_2026-05-28.md",
    DOCS / "windows_extraction_agent_api_design_2026-07-29.md",
    DOCS / "cad_tag_extraction_sources_for_souya_2026-07-28.md",
    HANDOFF_DOCS / "README.md",
    HANDOFF_DOCS / "VALIDATION_CHECKLIST.md",
    HANDOFF_DOCS / "PROMPT_FOR_CLAUDE.md",
    ROOT / "src/IcadExtraction.Contracts/Models.cs",
    ROOT / "src/IcadExtraction.SxNet/Icad2DExtractor.cs",
    ROOT / "src/IcadExtraction.SxNet/Icad3DExtractor.cs",
    ROOT / "src/IcadExtraction.Runner/WindowsExtractionAgent.cs",
    ROOT / "backend/apps/drawing_metadata/models.py",
    ROOT / "backend/apps/drawing_metadata/services/normalization.py",
    ROOT / "backend/apps/drawing_metadata/services/composition.py",
    ROOT / "backend/apps/drawing_metadata/services/tag_builder.py",
    ROOT / "backend/apps/drawing_metadata/services/overrides.py",
    ROOT / "backend/apps/drawing_metadata/api/urls.py",
)

CODE_ASSERTIONS = {
    ROOT / "backend/knowledge_system_backend/settings.py": (
        'DRAWING_METADATA_SCHEMA_VERSION = "1.0.0"',
        'DRAWING_METADATA_NORMALIZER_VERSION = "1.1.0"',
        'DRAWING_METADATA_TAG_RULE_VERSION = "1.1.0"',
    ),
    ROOT / "backend/apps/drawing_metadata/models.py": (
        "class RegisteredDrawing",
        "class DrawingMetadataExtractionJob",
        "class DrawingMetadataAgentHeartbeat",
        "class DrawingMetadataSnapshot",
        "class DrawingMetadataAuditLog",
        "class TagDictionaryEntry",
        'KIND_PART_NAME = "part_name"',
    ),
    ROOT / "backend/apps/drawing_metadata/services/tag_builder.py": (
        'add_tag("寸法あり"',
        'add_tag("寸法公差あり"',
        'add_tag("幾何公差あり"',
        'add_tag("溶接指示あり"',
        'f"硬度:{hardness_scale}"',
        'f"案件:{canonical_attributes[\'project_name\']}"',
    ),
    ROOT / "backend/apps/drawing_metadata/api/urls.py": (
        '"drawing-metadata/agent/jobs/claim"',
        '"drawing-metadata/tag-dictionaries"',
        '"drawing-metadata/registrations/<uuid:drawing_id>/overrides"',
        '"knowledge-entities"',
    ),
    ROOT / "backend/apps/drawing_metadata/services/source_formats.py": (
        '".icd": "icad"',
        '".step": "step"',
        '".stp": "step"',
        '".dxf": "dxf"',
    ),
}

SPEC_ASSERTIONS = (
    "現行コード準拠の正本",
    "スキーマバージョン: `1.0.0`",
    "正規化ルールバージョン: `1.1.0`",
    "タグルールバージョン: `1.1.0`",
    "`客先:{customer_name}`",
    "`案件:{project_name}`",
    "`装置:{equipment_category}`",
    "`寸法あり`",
    "`寸法公差あり`",
    "`幾何公差あり`",
    "`溶接指示あり`",
    "`硬度:HRC`",
    "`硬度:HV`",
    "/api/v1/drawing-metadata/tag-dictionaries",
    "/api/v1/drawing-metadata/agent/jobs/claim",
    "`PATCH/DELETE /api/v1/drawing-metadata/tag-dictionaries/{entryId}`",
    "`GET /api/v1/drawing-metadata/settings/tag-automation`",
    "Geminiを含む外部AIは使用しない",
    "自動タグ - removed + added",
)

FORBIDDEN_CODE_ASSERTIONS = {
    ROOT / "backend/knowledge_system_backend/settings.py": (
        "DRAWING_METADATA_LLM_PROVIDER",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
    ),
    ROOT / "backend/apps/drawing_metadata/tasks/extraction_tasks.py": (
        "llm_title_block_classifier",
        "_classify_2d_title_block_candidates",
    ),
}

LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def read_utf8(path: Path) -> str:
    """UTF-8以外へ暗黙変換せず、監査対象を読み込む。"""

    return path.read_text(encoding="utf-8")


def check_required_files(errors: list[str]) -> None:
    """正本コードと正本文書が削除・移動されていないか確認する。"""

    for path in REQUIRED_FILES:
        if not path.is_file():
            errors.append(f"必須ファイルがありません: {path.relative_to(ROOT)}")


def check_code_assertions(errors: list[str]) -> None:
    """文書の前提にしているコード識別子とバージョンを確認する。"""

    for path, needles in CODE_ASSERTIONS.items():
        if not path.is_file():
            continue
        content = read_utf8(path)
        for needle in needles:
            if needle not in content:
                errors.append(
                    f"コード識別子が見つかりません: {path.relative_to(ROOT)} :: {needle}"
                )


def check_current_spec(errors: list[str]) -> None:
    """現行仕様書に必須のバージョン・タグ・APIが記載されているか確認する。"""

    if not CURRENT_SPEC.is_file():
        return
    content = read_utf8(CURRENT_SPEC)
    for needle in SPEC_ASSERTIONS:
        if needle not in content:
            errors.append(f"現行仕様書の必須記述がありません: {needle}")


def check_forbidden_code_assertions(errors: list[str]) -> None:
    """廃止した外部AI実行経路が現行コードへ戻っていないか確認する。"""

    for path, needles in FORBIDDEN_CODE_ASSERTIONS.items():
        if not path.is_file():
            continue
        content = read_utf8(path)
        for needle in needles:
            if needle in content:
                errors.append(
                    f"廃止済みコード識別子が残っています: {path.relative_to(ROOT)} :: {needle}"
                )


def normalized_link_target(raw_target: str) -> str:
    """Markdownリンクからタイトル属性とアンカーを除いたパスを返す。"""

    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif " " in target:
        target = target.split(" ", 1)[0]
    return target.split("#", 1)[0]


def check_markdown_links(errors: list[str]) -> None:
    """正本文書とCloud引継ぎ文書の相対Markdownリンクを確認する。"""

    markdown_paths = list(DOCS.rglob("*.md")) + list(HANDOFF_DOCS.rglob("*.md"))
    for path in sorted(markdown_paths):
        content = read_utf8(path)
        for match in LINK_PATTERN.finditer(content):
            target = normalized_link_target(match.group(1))
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            if re.match(r"^[A-Za-z]:[\\/]", target):
                continue
            resolved = (path.parent / target.replace("\\", "/")).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                continue
            if not resolved.exists():
                errors.append(
                    f"リンク先がありません: {path.relative_to(ROOT)} -> {target}"
                )


def check_index_coverage(warnings: list[str]) -> None:
    """タグ関連文書が索引から漏れていないか候補を警告する。"""

    if not INDEX.is_file():
        return
    index_text = read_utf8(INDEX)
    keywords = ("タグ", "tag", "属性", "attribute", "metadata", "抽出", "extract")
    markdown_paths = list(DOCS.rglob("*.md")) + list(HANDOFF_DOCS.rglob("*.md"))
    for path in sorted(markdown_paths):
        content = read_utf8(path)
        lowered = content.lower()
        if not any(keyword.lower() in lowered for keyword in keywords):
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative not in index_text and path not in {CURRENT_SPEC, INDEX}:
            warnings.append(f"索引未掲載の関連候補: {relative}")


def main() -> int:
    """全監査を実行し、エラーがあれば1を返す。"""

    errors: list[str] = []
    warnings: list[str] = []

    check_required_files(errors)
    check_code_assertions(errors)
    check_current_spec(errors)
    check_forbidden_code_assertions(errors)
    check_markdown_links(errors)
    check_index_coverage(warnings)

    print(f"tag documentation audit: errors={len(errors)} warnings={len(warnings)}")
    for message in errors:
        print(f"ERROR: {message}")
    for message in warnings:
        print(f"WARNING: {message}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
