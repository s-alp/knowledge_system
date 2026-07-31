"""創屋向け配布物に社内情報・実顧客情報が混入していないか検査する。

対象:
- 最小パッケージ内のテキスト系ファイル
- 外部共有するPDF/PPTX内のテキスト
- 配布辞書の客先・案件初期値

画像内の文字は本スクリプトでは判定できないため、生成後にPDFの全ページを
画像化して目視確認する。違反を1件でも検出した場合は配布を中断する。
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import json
import re
import sys


TEXT_SUFFIXES = {
    ".cs",
    ".csproj",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sln",
    ".txt",
    ".yaml",
    ".yml",
}
DICTIONARY_RELATIVE_PATH = "dictionaries/initial-dictionaries.json"
REQUIRED_DICTIONARY_KINDS = {
    "customer",
    "equipment_category",
    "project",
    "maker",
    "spec",
    "heat_treatment",
    "part_name",
}
DICTIONARY_SOURCE_RELATIVE_PATH = "python/icad_tag_extraction/seed_dictionaries.py"

# 受領者向けMarkdownへ開発元の作業手順や判断経緯を戻さないための拒否語。
# 技術的な導入確認は「動作確認」として記載し、生成・監査・Git操作は社内文書へ分離する。
FORBIDDEN_RECIPIENT_DOCUMENT_LITERALS = (
    "リポジトリ",
    "Git履歴",
    "Gitへ",
    "コミット",
    "創屋側から依頼",
    "依頼された次の範囲",
    "外部共有監査",
    "内部監査",
    "配布承認",
    "生成スクリプト",
    "受入確認",
    "コメント監査",
    "文書監査",
)

# 既知の社内検証データを外部向け成果物へ戻さないための拒否語。
# 本監査スクリプト自体は配布パッケージへ同梱しない。
FORBIDDEN_LITERALS = (
    "コマツ小山",
    "広島アルミ",
    "澁谷工業",
    "シブヤパッケージングシステム",
    "アイリスオーヤマ",
    "宮本様",
    "HONSYA-FILE01",
    "210.165.3.139",
    "U8105111315.icd",
    "XH30-A08001-R03-JP_ロードカップ部改造.icd",
    "474300AC219.icd",
    "TR1D9K99027.icd",
    "03_20K03379P00_ｼｭｰﾄﾍﾞｰｽ(No.2FFS_XS).icd",
    "値は加工していません",
    "output/souya_handoff",
)

FORBIDDEN_PATTERNS = (
    ("社内ネットワークドライブ", re.compile(r"(?i)(?<![A-Z0-9])(?:J|T):[\\/]+")),
    ("ユーザープロファイル絶対パス", re.compile(r"(?i)C:[\\/]+Users[\\/]+")),
    ("社内資料保管パス", re.compile(r"(?i)D:[\\/]+創屋用(?:[\\/]+|$)")),
    ("実測件数を含む表現", re.compile(r"(?:実ICAD|共有DXF)\s*\d+\s*件")),
    ("顧客固有規格seed", re.compile(r"(?<![A-Za-z0-9])SES(?![A-Za-z0-9])")),
)


@dataclass(frozen=True)
class Finding:
    """検出した違反の場所と理由を保持する。"""

    path: str
    reason: str
    evidence: str


def _read_text(path: Path) -> str:
    """UTF-8またはUTF-8 BOMのテキストを読み、失敗は明示的に送出する。"""

    return path.read_text(encoding="utf-8-sig")


def _read_pptx_text(path: Path) -> str:
    """PPTX内のXML文字列を連結し、スライド・ノート・埋め込みメタデータを検査可能にする。"""

    try:
        with ZipFile(path) as archive:
            xml_names = sorted(
                name
                for name in archive.namelist()
                if name.endswith(".xml") or name.endswith(".rels")
            )
            return "\n".join(
                archive.read(name).decode("utf-8", errors="strict")
                for name in xml_names
            )
    except (BadZipFile, UnicodeDecodeError) as exc:
        raise ValueError(f"PPTXを検査できません: {path}") from exc


def _read_pdf_text(path: Path) -> str:
    """PDFの全ページから文字を抽出し、対外共有禁止語を検査可能にする。"""

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF監査にはpypdfが必要です。Codexの文書用Python環境、"
            "またはpypdfを導入した生成用環境で実行してください。"
        ) from exc

    try:
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError(f"PDFを検査できません: {path}") from exc


def _collect_distributable_dictionary_literals(payload: object) -> set[str]:
    """配布承認済みの客先・案件・規格辞書から、監査で許可する文字列を集める。"""

    if not isinstance(payload, dict):
        return set()
    allowed: set[str] = set()
    for kind in ("customer", "project", "spec"):
        mapping = payload.get(kind)
        if not isinstance(mapping, dict):
            continue
        for canonical, aliases in mapping.items():
            if isinstance(canonical, str):
                allowed.add(canonical)
            if isinstance(aliases, list):
                allowed.update(alias for alias in aliases if isinstance(alias, str))
    return allowed


def _scan_text(
    label: str,
    text: str,
    *,
    allowed_literals: set[str] | None = None,
    allowed_pattern_reasons: set[str] | None = None,
) -> list[Finding]:
    """本文を検査し、指定された配布辞書値だけを例外として許可する。"""

    allowed_literals = allowed_literals or set()
    allowed_pattern_reasons = allowed_pattern_reasons or set()
    findings: list[Finding] = []
    for literal in FORBIDDEN_LITERALS:
        if literal not in allowed_literals and literal in text:
            findings.append(Finding(label, "外部共有禁止語", literal))
    for reason, pattern in FORBIDDEN_PATTERNS:
        if reason in allowed_pattern_reasons:
            continue
        match = pattern.search(text)
        if match:
            findings.append(Finding(label, reason, match.group(0)))
    return findings


def _scan_recipient_document_wording(label: str, text: str) -> list[Finding]:
    """受領者向け文書へ作成側の生成・監査・Git工程が混入していないか検査する。"""

    findings: list[Finding] = []
    for literal in FORBIDDEN_RECIPIENT_DOCUMENT_LITERALS:
        if literal in text:
            findings.append(
                Finding(
                    label,
                    "受領者向け文書に内部作業表現",
                    literal,
                )
            )
    return findings


def audit_external_handoff(
    package_root: Path,
    *,
    presentations: tuple[Path, ...] = (),
    pdfs: tuple[Path, ...] = (),
) -> list[Finding]:
    """パッケージと指定PDF/PPTXを走査し、外部共有を止めるべき違反を返す。"""

    root = package_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"パッケージフォルダがありません: {root}")

    dictionary_path = root / DICTIONARY_RELATIVE_PATH
    dictionary_payload: object = {}
    if dictionary_path.is_file():
        dictionary_payload = json.loads(_read_text(dictionary_path))
    allowed_dictionary_literals = _collect_distributable_dictionary_literals(
        dictionary_payload
    )
    allowed_dictionary_pattern_reasons = (
        {"顧客固有規格seed"}
        if "SES" in allowed_dictionary_literals
        else set()
    )

    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            relative = path.relative_to(root).as_posix()
            text = _read_text(path)
            dictionary_values_allowed = relative in {
                DICTIONARY_RELATIVE_PATH,
                DICTIONARY_SOURCE_RELATIVE_PATH,
            }
            findings.extend(
                _scan_text(
                    relative,
                    text,
                    allowed_literals=(
                        allowed_dictionary_literals
                        if dictionary_values_allowed
                        else set()
                    ),
                    allowed_pattern_reasons=(
                        allowed_dictionary_pattern_reasons
                        if dictionary_values_allowed
                        else set()
                    ),
                )
            )
            if path.suffix.lower() == ".md":
                findings.extend(_scan_recipient_document_wording(relative, text))

    forbidden_components = {
        "apps",
        "local_test_materials",
        "customer_materials",
        "souya_handoff",
    }
    for path in root.rglob("*"):
        relative_parts = set(path.relative_to(root).parts)
        overlap = sorted(relative_parts & forbidden_components)
        if overlap:
            findings.append(
                Finding(
                    path.relative_to(root).as_posix(),
                    "配布対象外ディレクトリ",
                    ", ".join(overlap),
                )
            )

    if not dictionary_path.is_file():
        findings.append(
            Finding(
                DICTIONARY_RELATIVE_PATH,
                "必須ファイル欠落",
                "初期辞書を監査できません",
            )
        )
    else:
        if not isinstance(dictionary_payload, dict):
            findings.append(
                Finding(
                    DICTIONARY_RELATIVE_PATH,
                    "辞書形式不正",
                    "最上位がJSON objectではありません",
                )
            )
        else:
            for kind in sorted(REQUIRED_DICTIONARY_KINDS):
                if not isinstance(dictionary_payload.get(kind), dict):
                    findings.append(
                        Finding(
                            DICTIONARY_RELATIVE_PATH,
                            "辞書形式不正",
                            f"{kind}がJSON objectではありません",
                        )
                    )

    for presentation in presentations:
        resolved = presentation.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"PPTXがありません: {resolved}")
        presentation_text = _read_pptx_text(resolved)
        findings.extend(
            _scan_text(
                resolved.name,
                presentation_text,
            )
        )
        findings.extend(
            _scan_recipient_document_wording(resolved.name, presentation_text)
        )
    for pdf in pdfs:
        resolved = pdf.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"PDFがありません: {resolved}")
        pdf_text = _read_pdf_text(resolved)
        findings.extend(
            _scan_text(
                resolved.name,
                pdf_text,
            )
        )
        findings.extend(_scan_recipient_document_wording(resolved.name, pdf_text))
    return findings


def assert_external_handoff_safe(
    package_root: Path,
    *,
    presentations: tuple[Path, ...] = (),
    pdfs: tuple[Path, ...] = (),
) -> None:
    """違反があれば一覧を含む例外を送出し、生成・配布を中断させる。"""

    findings = audit_external_handoff(
        package_root,
        presentations=presentations,
        pdfs=pdfs,
    )
    if findings:
        details = "\n".join(
            f"- {finding.path}: {finding.reason}: {finding.evidence}"
            for finding in findings
        )
        raise ValueError(f"外部共有監査で違反を検出しました。\n{details}")


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--pptx", action="append", type=Path, default=[])
    parser.add_argument("--pdf", action="append", type=Path, default=[])
    args = parser.parse_args()
    findings = audit_external_handoff(
        args.package,
        presentations=tuple(args.pptx),
        pdfs=tuple(args.pdf),
    )
    if findings:
        for finding in findings:
            print(f"{finding.path}\t{finding.reason}\t{finding.evidence}")
        return 1
    print("外部共有監査: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
