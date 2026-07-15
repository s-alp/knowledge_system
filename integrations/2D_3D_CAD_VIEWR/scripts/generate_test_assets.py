from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
    root.mkdir(parents=True, exist_ok=True)

    (root / "sample.stl").write_text(
        "\n".join(
            [
                "solid sample",
                "facet normal 0 0 1",
                "outer loop",
                "vertex 0 0 0",
                "vertex 1 0 0",
                "vertex 0 1 0",
                "endloop",
                "endfacet",
                "endsolid sample",
            ]
        ),
        encoding="utf-8",
    )

    (root / "sample.step").write_text(
        "\n".join(
            [
                "ISO-10303-21;",
                "HEADER;",
                "FILE_DESCRIPTION(('SIMPLE STEP SAMPLE'),'2;1');",
                "FILE_NAME('sample.step','2026-04-13T00:00:00',('Codex'),('Codex'),'','Codex','');",
                "FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));",
                "ENDSEC;",
                "DATA;",
                "ENDSEC;",
                "END-ISO-10303-21;",
            ]
        ),
        encoding="utf-8",
    )

    (root / "README.md").write_text(
        "# Fixtures\n\n"
        "軽量なテスト用 fixture です。PDF/JPEG/TIFF の追加 fixture が必要な場合は、"
        "`scripts/generate_test_assets.py` を拡張してください。\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
