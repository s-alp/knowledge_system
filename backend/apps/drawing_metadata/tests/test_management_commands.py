from io import StringIO
import json

import pytest
from django.core.management import call_command

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing


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


@pytest.mark.django_db
def test_export_drawing_metadata_fixtures_writes_handoff_payload(tmp_path):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="host-001",
        filename="sample.icd",
        source_path=r"C:\cad\sample.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={
            "customer_name": "澁谷工業",
            "equipment_category": "ロボット",
            "part_names": ["PART-A"],
            "material_keywords": ["SUS304"],
        },
        derived_tags_json=[],
    )
    output_path = tmp_path / "souya_fixture.json"
    stdout = StringIO()

    call_command(
        "export_drawing_metadata_fixtures",
        drawing_id=[str(drawing.id)],
        output=str(output_path),
        stdout=stdout,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "drawing_metadata_handoff_fixture.v1"
    assert payload["itemCount"] == 1
    item = payload["items"][0]
    assert item["drawingId"] == str(drawing.id)
    assert item["detailApiPayload"]["viewerBootstrap"]["metadata"]["tags"] == ["客先:澁谷工業", "装置:ロボット", "材質:SUS304"]
    assert item["viewerBootstrap"]["availability"] == {"has2d": False, "has3d": True}
    assert item["ragPayload"]["preFilters"]["customerName"] == "澁谷工業"
    assert item["ragPayload"]["rankingSignals"]["partNames"] == ["PART-A"]
    assert "exported 1 drawing fixture" in stdout.getvalue()
