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

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
HANDOFF_DOCS = ROOT / "handoff/claude_cloud"
SOUYA_RECIPIENT_DOCS = ROOT / "handoff/souya_tag_extraction/recipient_docs"
CURRENT_SPEC = DOCS / "tag_extraction_and_assignment_current_spec_2026-07-29.md"
INDEX = DOCS / "tag_extraction_documentation_index_2026-07-29.md"
SOUYA_DOC = DOCS / "cad_tag_extraction_sources_for_souya_2026-07-28.md"
SEED_DICTIONARY_MODULE = ROOT / "backend/icad_tag_extraction/seed_dictionaries.py"

# 創屋様向け文書 4.2「辞書 / 初期エントリ数」表の行ラベルと、初期辞書の定数名の対応。
# 文書へ件数を書く以上、コードの実数とズレたら失敗させる。
SEED_DICTIONARY_TABLE_ROWS = {
    "客先": "CUSTOMER_KEYWORDS",
    "装置カテゴリ": "EQUIPMENT_CATEGORY_KEYWORDS",
    "メーカー": "MAKER_KEYWORDS",
    "材質分類": "MATERIAL_CLASSIFICATION_RULES",
    "熱処理": "HEAT_TREATMENT_KEYWORDS",
    "規格": "SPEC_KEYWORDS",
    "部品名": "PART_NAME_KEYWORDS",
}

REQUIRED_FILES = (
    ROOT / "AGENTS.md",
    CURRENT_SPEC,
    INDEX,
    DOCS / "extraction_result_schema_2026-05-28.md",
    DOCS / "windows_extraction_agent_api_design_2026-07-29.md",
    DOCS / "cad_tag_extraction_sources_for_souya_2026-07-28.md",
    DOCS / "souya_tag_extraction_minimal_handoff_2026-07-30.md",
    SOUYA_RECIPIENT_DOCS / "README.md",
    SOUYA_RECIPIENT_DOCS / "docs/extraction_reference.md",
    SOUYA_RECIPIENT_DOCS / "docs/integration_contract.md",
    SOUYA_RECIPIENT_DOCS / "docs/icad_windows_operations.md",
    HANDOFF_DOCS / "README.md",
    HANDOFF_DOCS / "VALIDATION_CHECKLIST.md",
    HANDOFF_DOCS / "PROMPT_FOR_CLAUDE.md",
    ROOT / "src/IcadExtraction.Contracts/Models.cs",
    ROOT / "src/IcadExtraction.SxNet/Icad2DExtractor.cs",
    ROOT / "src/IcadExtraction.SxNet/Icad3DExtractor.cs",
    ROOT / "src/IcadExtraction.Runner/WindowsExtractionAgent.cs",
    ROOT / "backend/apps/drawing_metadata/models.py",
    ROOT / "backend/icad_tag_extraction/pipeline.py",
    ROOT / "backend/icad_tag_extraction/normalization.py",
    ROOT / "backend/icad_tag_extraction/tag_builder.py",
    ROOT / "backend/icad_tag_extraction/dictionary_provider.py",
    ROOT / "backend/apps/drawing_metadata/services/normalization.py",
    ROOT / "backend/apps/drawing_metadata/services/composition.py",
    ROOT / "backend/apps/drawing_metadata/services/tag_builder.py",
    ROOT / "backend/apps/drawing_metadata/services/overrides.py",
    ROOT / "backend/apps/drawing_metadata/services/retired_ai_metadata.py",
    ROOT / "backend/apps/drawing_metadata/api/urls.py",
    ROOT / "scripts/audit_retired_ai_database_history.py",
    ROOT / "schemas/tag_extraction/icad-csharp-raw-extraction.v1.schema.json",
    ROOT / "schemas/tag_extraction/icad-canonical-attributes.v1.schema.json",
    ROOT / "schemas/tag_extraction/icad-derived-tags.v1.schema.json",
    ROOT / "schemas/tag_extraction/icad-tag-extraction-result.v1.schema.json",
)

CODE_ASSERTIONS = {
    ROOT / "AGENTS.md": (
        "創屋向け最小パッケージの再生成手順",
        "Codexが変更差分、契約影響、テスト結果、同梱内容、既存成果物を順に確認",
        "既存パッケージを自動削除・自動上書きしない",
        "git diff --cached",
        "--output output\\souya_tag_extraction_minimal_YYYY-MM-DD",
        "manifest.json",
    ),
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
    ROOT / "backend/icad_tag_extraction/tag_builder.py": (
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
    # 案件辞書は現行seedに初期値がないため、文書と実装の0件表記を固定する。
    ROOT / "backend/icad_tag_extraction/dictionary_provider.py": (
        "KIND_PROJECT: {}",
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
    "DB上の履歴値そのものは変更せず",
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
    ROOT / "backend/apps/drawing_metadata/services/display.py": (
        '"llmField"',
        '"llmConfidence"',
        '"llmReason"',
    ),
    ROOT / "backend/apps/drawing_metadata/services/knowledge_payload_preview.py": (
        'candidate.get("llm_confidence")',
    ),
    ROOT / "backend/apps/drawing_metadata/services/composition.py": (
        '"title_block_llm_"',
    ),
    ROOT / "backend/apps/drawing_metadata/templates/drawing_metadata/detail.html": (
        "candidate.llmField",
        "candidate.llmConfidence",
        "candidate.llmReason",
        "<th>AI分類</th>",
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


def load_seed_dictionaries() -> dict[str, object] | None:
    """初期辞書モジュールを、Djangoも独立コア本体も読み込まずに単体で評価する。

    seed_dictionaries.py は定数だけを持つDjango非依存モジュールである。
    パッケージとしてimportすると他モジュールを巻き込むため、ファイル単体で読み込む。
    """

    if not SEED_DICTIONARY_MODULE.is_file():
        return None
    spec = importlib.util.spec_from_file_location(
        "audit_seed_dictionaries", SEED_DICTIONARY_MODULE
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return vars(module)


def check_seed_dictionary_counts(errors: list[str]) -> None:
    """文書に記載した初期辞書の件数が、現行コードの実数と一致するか確認する。"""

    if not SOUYA_DOC.is_file():
        return
    namespace = load_seed_dictionaries()
    if namespace is None:
        errors.append(
            "初期辞書モジュールを読み込めません: "
            f"{SEED_DICTIONARY_MODULE.relative_to(ROOT)}"
        )
        return
    content = read_utf8(SOUYA_DOC)
    for label, constant in SEED_DICTIONARY_TABLE_ROWS.items():
        entries = namespace.get(constant)
        if not isinstance(entries, dict):
            errors.append(
                "初期辞書の定数が見つかりません: "
                f"{SEED_DICTIONARY_MODULE.relative_to(ROOT)} :: {constant}"
            )
            continue
        match = re.search(
            rf"^\|\s*{re.escape(label)}\s*\|\s*(\d+)\s*\|", content, re.MULTILINE
        )
        if match is None:
            errors.append(
                f"辞書件数の記載行がありません: {SOUYA_DOC.relative_to(ROOT)} :: {label}"
            )
            continue
        documented = int(match.group(1))
        actual = len(entries)
        if documented != actual:
            errors.append(
                "辞書件数が現行コードと一致しません: "
                f"{label} 文書={documented} コード={actual} ({constant})"
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
    """正本文書と各引継ぎ文書の相対Markdownリンクを確認する。"""

    markdown_paths = (
        list(DOCS.rglob("*.md"))
        + list(HANDOFF_DOCS.rglob("*.md"))
        + list(SOUYA_RECIPIENT_DOCS.rglob("*.md"))
    )
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
    markdown_paths = (
        list(DOCS.rglob("*.md"))
        + list(HANDOFF_DOCS.rglob("*.md"))
        + list(SOUYA_RECIPIENT_DOCS.rglob("*.md"))
    )
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
    check_seed_dictionary_counts(errors)
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
