"""創屋向け専用Markdownから、配布用の利用ガイドPDFを生成する。

実行目的:
- READMEと技術文書をPDFでも同じ内容へ揃え、二重編集を避ける。
- 社内用の生成・監査資料をPDFへ混入させない。

前提:
- ReportLabを利用できるPythonで実行する。
- 入力は`handoff/souya_tag_extraction/recipient_docs`配下の固定4文書とする。

副作用:
- 指定した新規PDFを1ファイル作成する。
- 既存PDFは上書きせず、出力先が存在する場合は処理を中断する。
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import date
from html import escape
import os
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)


ROOT = Path(__file__).resolve().parents[1]
RECIPIENT_DOCS_ROOT = ROOT / "handoff" / "souya_tag_extraction" / "recipient_docs"
SOURCE_DOCUMENTS = (
    Path("README.md"),
    Path("docs/extraction_reference.md"),
    Path("docs/integration_contract.md"),
    Path("docs/icad_windows_operations.md"),
)
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "CADタグ属性抽出_創屋様向け利用ガイド.pdf"
FONT_NAME = "SouyaGuideJapanese"
PAGE_WIDTH, PAGE_HEIGHT = A4
CONTENT_WIDTH = PAGE_WIDTH - 36 * mm


def _format_inline(text: str) -> str:
    """Markdownのインライン表現をPDFで読める日本語表記へ変換する。"""

    def replace_link(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2)
        if target.startswith(("http://", "https://", "mailto:")):
            return f"{label}（{target}）"
        return label

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, text)
    text = re.sub(r"`([^`]+)`", r"「\1」", text)
    text = text.replace("**", "")
    return escape(text)


def _styles() -> dict[str, ParagraphStyle]:
    """日本語文書用の見出し、本文、表、コードのスタイルを返す。"""

    sample = getSampleStyleSheet()
    return {
        "cover_label": ParagraphStyle(
            "CoverLabel",
            parent=sample["Normal"],
            fontName=FONT_NAME,
            fontSize=11,
            textColor=colors.HexColor("#0F6E8C"),
            leading=16,
            alignment=TA_LEFT,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName=FONT_NAME,
            fontSize=26,
            leading=38,
            textColor=colors.HexColor("#17324D"),
            alignment=TA_LEFT,
            spaceAfter=8 * mm,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=sample["Normal"],
            fontName=FONT_NAME,
            fontSize=12,
            leading=20,
            textColor=colors.HexColor("#44546A"),
            alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "Heading1Japanese",
            parent=sample["Heading1"],
            fontName=FONT_NAME,
            fontSize=20,
            leading=29,
            textColor=colors.HexColor("#17324D"),
            spaceAfter=6 * mm,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Heading2Japanese",
            parent=sample["Heading2"],
            fontName=FONT_NAME,
            fontSize=14,
            leading=21,
            textColor=colors.HexColor("#0F6E8C"),
            spaceBefore=5 * mm,
            spaceAfter=2.5 * mm,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Heading3Japanese",
            parent=sample["Heading3"],
            fontName=FONT_NAME,
            fontSize=11.5,
            leading=18,
            textColor=colors.HexColor("#284B63"),
            spaceBefore=3.5 * mm,
            spaceAfter=1.5 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyJapanese",
            parent=sample["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.2,
            leading=15.2,
            textColor=colors.HexColor("#263238"),
            spaceAfter=2.2 * mm,
            wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "BulletJapanese",
            parent=sample["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.2,
            leading=15.2,
            leftIndent=5 * mm,
            firstLineIndent=-3.5 * mm,
            textColor=colors.HexColor("#263238"),
            spaceAfter=1.2 * mm,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "CodeJapanese",
            parent=sample["Code"],
            fontName=FONT_NAME,
            fontSize=7.8,
            leading=12,
            textColor=colors.HexColor("#17324D"),
            leftIndent=1.5 * mm,
            rightIndent=1.5 * mm,
        ),
        "table": ParagraphStyle(
            "TableJapanese",
            parent=sample["BodyText"],
            fontName=FONT_NAME,
            fontSize=7.4,
            leading=10.5,
            textColor=colors.HexColor("#263238"),
            wordWrap="CJK",
        ),
        "footer": ParagraphStyle(
            "FooterJapanese",
            parent=sample["Normal"],
            fontName=FONT_NAME,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#607D8B"),
            alignment=TA_CENTER,
        ),
    }


def _register_japanese_font() -> None:
    """Windows標準の日本語TrueTypeフォントを埋め込み、閲覧PCの代替フォントへ依存させない。"""

    windows_root = os.environ.get("WINDIR")
    if not windows_root:
        raise RuntimeError("WINDIRが未設定のため、日本語フォントを解決できません。")
    font_path = Path(windows_root) / "Fonts" / "NotoSansJP-VF.ttf"
    if not font_path.is_file():
        raise FileNotFoundError(
            "PDFへ埋め込む日本語フォントがありません: "
            f"{font_path}"
        )
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path)))


def _is_table_separator(cells: list[str]) -> bool:
    """Markdown表の見出し区切り行かを判定する。"""

    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _table_from_markdown(lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    """Markdown表をページ分割可能なReportLab表へ変換する。"""

    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not _is_table_separator(cells):
            rows.append(cells)
    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    data = [
        [Paragraph(_format_inline(cell), styles["table"]) for cell in row]
        for row in normalized
    ]
    table = Table(
        data,
        colWidths=[CONTENT_WIDTH / column_count] * column_count,
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCEEF5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#A9C3CF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
            ]
        )
    )
    return table


def _markdown_story(path: Path, styles: dict[str, ParagraphStyle]) -> list[object]:
    """管理対象Markdownを見出し・表・コード・箇条書きへ分解してPDF要素へ変換する。"""

    if not path.is_file():
        raise FileNotFoundError(f"PDF生成元の文書がありません: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    story: list[object] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index >= len(lines):
                raise ValueError(f"コードブロックが閉じられていません: {path}")
            code = XPreformatted(escape("\n".join(code_lines)), styles["code"])
            code_box = Table([[code]], colWidths=[CONTENT_WIDTH])
            code_box.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F7")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8CDD6")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.extend([code_box, Spacer(1, 3 * mm)])
            index += 1
            continue
        if stripped.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.extend([_table_from_markdown(table_lines, styles), Spacer(1, 3 * mm)])
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            story.append(Paragraph(_format_inline(heading.group(2)), styles[f"h{level}"]))
            index += 1
            continue
        if stripped.startswith("- "):
            story.append(
                Paragraph(
                    f"・{_format_inline(stripped[2:])}",
                    styles["bullet"],
                )
            )
            index += 1
            continue
        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if numbered:
            story.append(
                Paragraph(
                    f"{numbered.group(1)}. {_format_inline(numbered.group(2))}",
                    styles["bullet"],
                )
            )
            index += 1
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if (
                not candidate
                or candidate.startswith(("#", "```", "|", "- "))
                or re.match(r"^\d+\.\s+", candidate)
            ):
                break
            paragraph_lines.append(candidate)
            index += 1
        story.append(
            Paragraph(
                _format_inline(" ".join(paragraph_lines)),
                styles["body"],
            )
        )
    return story


def _draw_later_page(canvas, document) -> None:
    """本文ページへ資料名とページ番号を描画する。"""

    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B8CDD6"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, PAGE_HEIGHT - 13 * mm, PAGE_WIDTH - 18 * mm, PAGE_HEIGHT - 13 * mm)
    canvas.setFillColor(colors.HexColor("#607D8B"))
    canvas.setFont(FONT_NAME, 7.5)
    canvas.drawString(18 * mm, PAGE_HEIGHT - 10 * mm, "CADタグ・属性抽出パッケージ 利用ガイド")
    canvas.drawRightString(PAGE_WIDTH - 18 * mm, 10 * mm, str(document.page))
    canvas.restoreState()


def generate_pdf(
    output_path: Path,
    *,
    document_date: date | None = None,
) -> Path:
    """専用Markdown4文書を読み、既存ファイルを上書きせず配布用PDFを生成する。"""

    output_path = output_path.resolve()
    if output_path.exists():
        raise FileExistsError(f"PDF出力先が既に存在します。上書きしません: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document_date = document_date or date.today()

    _register_japanese_font()
    styles = _styles()
    story: list[object] = [
        Spacer(1, 32 * mm),
        Paragraph("創屋様向け", styles["cover_label"]),
        Spacer(1, 8 * mm),
        Paragraph("CADタグ・属性抽出<br/>利用・組み込みガイド", styles["cover_title"]),
        HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor("#1696C4"),
            spaceBefore=2 * mm,
            spaceAfter=8 * mm,
        ),
        Paragraph(
            "ICAD・STEP・DXFからの属性抽出、共通属性への正規化、"
            "辞書照合、根拠付きタグ生成、Windows実行方法をまとめた資料です。",
            styles["cover_subtitle"],
        ),
        Spacer(1, 16 * mm),
        Paragraph(
            f"更新日: {document_date.isoformat()}<br/>"
            "作成: 株式会社アルパイン設計事務所",
            styles["body"],
        ),
        PageBreak(),
    ]

    for position, relative_path in enumerate(SOURCE_DOCUMENTS):
        story.extend(_markdown_story(RECIPIENT_DOCS_ROOT / relative_path, styles))
        if position != len(SOURCE_DOCUMENTS) - 1:
            story.append(PageBreak())

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=17 * mm,
        title="CADタグ・属性抽出 利用・組み込みガイド",
        author="株式会社アルパイン設計事務所",
        subject="ICAD・STEP・DXFの属性抽出とタグ生成",
    )
    document.build(
        story,
        onFirstPage=lambda canvas, doc: None,
        onLaterPages=_draw_later_page,
    )
    if output_path.stat().st_size <= 0:
        raise ValueError(f"PDFが空です: {output_path}")
    return output_path


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="新規作成するPDF。既存ファイルは上書きしない。",
    )
    args = parser.parse_args()
    output_path = generate_pdf(args.output)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
