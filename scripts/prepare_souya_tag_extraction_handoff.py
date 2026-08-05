"""創屋向け説明PDFと最小パッケージを、同じ専用原稿から新規生成する。

生成するPDFは、非技術者への説明用の概要ガイドと、導入担当者向けの利用ガイドの2種類で、
どちらも受領者向けMarkdownを原稿とする。

このスクリプトはPDF生成とファイル収集をまとめるだけであり、変更差分、契約影響、
テスト結果、PDF全ページの見た目を判断しない。実行前後の確認はAGENTS.mdに従う。

既存のPDF、パッケージフォルダー、ZIPは上書きしない。
"""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from build_souya_tag_extraction_package import build_package
from generate_souya_recipient_guide_pdf import generate_overview_pdf, generate_pdf


ROOT = Path(__file__).resolve().parents[1]


def prepare_handoff(
    output_dir: Path,
    *,
    guide_pdf_output: Path | None = None,
    overview_pdf_output: Path | None = None,
) -> tuple[Path, Path, Path, Path]:
    """2種類のPDFを生成してから、同じ内容のREADME・技術文書とともにZIP化する。"""

    resolved_output = output_dir.resolve()
    archive_path = resolved_output.with_suffix(".zip")
    if resolved_output.exists():
        raise FileExistsError(f"出力先が既に存在します。上書きしません: {resolved_output}")
    if archive_path.exists():
        raise FileExistsError(f"ZIPが既に存在します。上書きしません: {archive_path}")

    overview_output = (
        overview_pdf_output.resolve()
        if overview_pdf_output is not None
        else ROOT / "output" / "pdf" / f"{resolved_output.name}_概要ガイド.pdf"
    )
    pdf_output = (
        guide_pdf_output.resolve()
        if guide_pdf_output is not None
        else ROOT / "output" / "pdf" / f"{resolved_output.name}_利用ガイド.pdf"
    )
    # 片方だけ生成された状態で中断すると、次回実行が既存PDFで止まるため先に両方確認する。
    for existing_candidate in (overview_output, pdf_output):
        if existing_candidate.exists():
            raise FileExistsError(
                f"PDFが既に存在します。上書きしません: {existing_candidate}"
            )
    if overview_output == pdf_output:
        raise ValueError(f"概要ガイドと利用ガイドに同じ出力先は指定できません: {pdf_output}")

    generated_overview_pdf = generate_overview_pdf(overview_output)
    generated_pdf = generate_pdf(pdf_output)
    package_dir, package_zip = build_package(
        resolved_output,
        guide_pdf=generated_pdf,
        overview_pdf=generated_overview_pdf,
    )
    return generated_overview_pdf, generated_pdf, package_dir, package_zip


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="新規作成するパッケージフォルダー。",
    )
    parser.add_argument(
        "--guide-pdf-output",
        type=Path,
        help="新規作成する利用ガイドPDF。省略時はoutput/pdf配下へ作成する。",
    )
    parser.add_argument(
        "--overview-pdf-output",
        type=Path,
        help="新規作成する概要ガイドPDF。省略時はoutput/pdf配下へ作成する。",
    )
    args = parser.parse_args()
    overview_pdf, guide_pdf, package_dir, package_zip = prepare_handoff(
        args.output,
        guide_pdf_output=args.guide_pdf_output,
        overview_pdf_output=args.overview_pdf_output,
    )
    print(f"overviewPdf={overview_pdf}")
    print(f"guidePdf={guide_pdf}")
    print(f"packageDirectory={package_dir}")
    print(f"archive={package_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
