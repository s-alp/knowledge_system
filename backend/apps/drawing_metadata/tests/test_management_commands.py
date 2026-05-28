from io import StringIO

import pytest
from django.core.management import call_command

from apps.drawing_metadata.models import RegisteredDrawing


@pytest.mark.django_db
def test_register_cad_drawings_registers_icd_files_idempotently(tmp_path):
    cad_root = tmp_path / "cad_data"
    nested = cad_root / "nested"
    nested.mkdir(parents=True)

    drawing_a = cad_root / "A-01.icd"
    drawing_b = nested / "B-02.ICD"
    ignored = cad_root / "memo.txt"

    drawing_a.write_text("", encoding="utf-8")
    drawing_b.write_text("", encoding="utf-8")
    ignored.write_text("ignore", encoding="utf-8")

    existing = RegisteredDrawing.objects.create(
        host_drawing_id="legacy",
        filename="old-name.txt",
        source_path=str(drawing_a.resolve()),
        source_format="pdf",
    )

    stdout_first = StringIO()
    call_command("register_cad_drawings", cad_root=str(cad_root), stdout=stdout_first)

    existing.refresh_from_db()
    assert RegisteredDrawing.objects.count() == 2
    assert existing.filename == "A-01.icd"
    assert existing.source_format == "icad"
    assert {item.source_path for item in RegisteredDrawing.objects.all()} == {
        str(drawing_a.resolve()),
        str(drawing_b.resolve()),
    }
    assert "created=1" in stdout_first.getvalue()
    assert "updated=1" in stdout_first.getvalue()

    stdout_second = StringIO()
    call_command("register_cad_drawings", cad_root=str(cad_root), stdout=stdout_second)

    assert RegisteredDrawing.objects.count() == 2
    assert "created=0" in stdout_second.getvalue()
    assert "updated=0" in stdout_second.getvalue()
    assert "skipped=2" in stdout_second.getvalue()
