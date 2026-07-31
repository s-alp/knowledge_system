"""創屋向け利用ガイドPDFと最小パッケージを、同じ専用原稿から新規生成する。

このスクリプトはPDF生成とファイル収集をまとめるだけであり、変更差分、契約影響、
テスト結果、PDF全ページの見た目を判断しない。実行前後の確認はAGENTS.mdに従う。

既存のPDF、パッケージフォルダー、ZIPは上書きしない。
"""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from build_souya_tag_extraction_package import build_package
from generate_souya_recipient_guide_pdf import generate_pdf


ROOT = Path(__file__).resolve().parents[1]


def prepare_handoff(
    output_dir: Path,
    *,
    guide_pdf_output: Path | None = None,
) -> tuple[Path, Path, Path]:
    """PDFを生成してから同じ内容のREADME・技術文書とともにZIP化する。"""

    resolved_output = output_dir.resolve()
    archive_path = resolved_output.with_suffix(".zip")
    if resolved_output.exists():
        raise FileExistsError(f"出力先が既に存在します。上書きしません: {resolved_output}")
    if archive_path.exists():
        raise FileExistsError(f"ZIPが既に存在します。上書きしません: {archive_path}")

    pdf_output = (
        guide_pdf_output.resolve()
        if guide_pdf_output is not None
        else ROOT / "output" / "pdf" / f"{resolved_output.name}_利用ガイド.pdf"
    )
    if pdf_output.exists():
        raise FileExistsError(f"PDFが既に存在します。上書きしません: {pdf_output}")

    generated_pdf = generate_pdf(pdf_output)
    package_dir, package_zip = build_package(
        resolved_output,
        guide_pdf=generated_pdf,
    )
    return generated_pdf, package_dir, package_zip


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
    args = parser.parse_args()
    guide_pdf, package_dir, package_zip = prepare_handoff(
        args.output,
        guide_pdf_output=args.guide_pdf_output,
    )
    print(f"guidePdf={guide_pdf}")
    print(f"packageDirectory={package_dir}")
    print(f"archive={package_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
