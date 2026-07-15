from io import StringIO
import json

import pytest
from django.core.management import call_command

from apps.drawing_metadata.models import DrawingMetadataExtractionJob, DrawingMetadataSnapshot, RegisteredDrawing


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
    assert item["knowledgeSystemPayloadPreview"]["schemaVersion"] == "knowledge_system_payload_preview.v1"
    assert item["knowledgeSystemPayloadPreview"]["targets"][0]["targetKey"] == "drawing"
    assert item["ragPayload"]["preFilters"]["customerName"] == "澁谷工業"
    assert item["ragPayload"]["rankingSignals"]["partNames"] == ["PART-A"]
    assert "exported 1 drawing fixture" in stdout.getvalue()


@pytest.mark.django_db
def test_export_drawing_metadata_fixtures_skips_empty_snapshots_by_default(tmp_path):
    RegisteredDrawing.objects.create(
        host_drawing_id="host-empty",
        filename="empty.icd",
        source_path=r"C:\cad\empty.icd",
        source_format="icad",
    )
    output_path = tmp_path / "souya_fixture.json"

    call_command("export_drawing_metadata_fixtures", output=str(output_path))

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["itemCount"] == 0
    assert payload["sourceDrawingCount"] == 1
    assert payload["skippedEmptySnapshotCount"] == 1
    assert payload["exportPolicy"] == {
        "includeEmptySnapshots": False,
        "emptySnapshotHandling": "skipped",
    }


@pytest.mark.django_db
def test_export_drawing_metadata_fixtures_can_include_empty_snapshots_for_debug(tmp_path):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="host-empty",
        filename="empty.icd",
        source_path=r"C:\cad\empty.icd",
        source_format="icad",
    )
    output_path = tmp_path / "souya_fixture.json"

    call_command(
        "export_drawing_metadata_fixtures",
        drawing_id=[str(drawing.id)],
        include_empty_snapshots=True,
        output=str(output_path),
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["itemCount"] == 1
    assert payload["sourceDrawingCount"] == 1
    assert payload["skippedEmptySnapshotCount"] == 0
    assert payload["exportPolicy"] == {
        "includeEmptySnapshots": True,
        "emptySnapshotHandling": "included",
    }
    assert payload["items"][0]["detailApiPayload"]["snapshotsByMode"] == {}


@pytest.mark.django_db
def test_import_drawing_metadata_extracts_imports_2d_and_3d_snapshots(tmp_path):
    source_path = r"J:\SAMPLE\BRACKET.icd"
    payload_2d = {
        "input_path": source_path,
        "source_format": "icad",
        "source_kind": "2d",
        "extractor_name": "test-extractor",
        "extractor_version": "1.0.0",
        "elapsed_ms": 12,
        "warnings": [{"code": "sample_warning"}],
        "raw_extract": {
            "texts": [
                {
                    "joined_text": "材質 SUS304",
                    "text_lines": ["材質 SUS304"],
                    "source_type": "label",
                    "position_x": 10,
                    "position_y": 20,
                    "inside_print_area": True,
                }
            ],
            "dimensions": [],
            "geometry_primitives": [],
        },
    }
    payload_3d = {
        "input_path": source_path,
        "source_format": "icad",
        "source_kind": "3d",
        "extractor_name": "test-extractor",
        "extractor_version": "1.0.0",
        "raw_extract": {
            "top_part": {"name": "BRACKET"},
            "parts": [{"tree_path": ["BRACKET"], "name": "BRACKET"}],
            "materials": [{"matid": "SUS304", "name": "SUS304", "specific_gravity": 7.93}],
            "material_probe_status": "available",
        },
    }
    path_2d = tmp_path / "BRACKET_2d.json"
    path_3d = tmp_path / "BRACKET_3d.json"
    path_2d.write_text(json.dumps(payload_2d, ensure_ascii=False), encoding="utf-8")
    path_3d.write_text(json.dumps(payload_3d, ensure_ascii=False), encoding="utf-8")
    stdout = StringIO()

    call_command(
        "import_drawing_metadata_extracts",
        str(path_2d),
        str(path_3d),
        stdout=stdout,
    )

    drawing = RegisteredDrawing.objects.get(source_path=source_path)
    snapshots = {snapshot.extraction_mode: snapshot for snapshot in DrawingMetadataSnapshot.objects.filter(drawing=drawing)}
    assert drawing.filename == "BRACKET.icd"
    assert set(snapshots) == {"2d", "3d"}
    assert snapshots["2d"].raw_extract_json["_source_file"]["full_path"] == source_path
    assert snapshots["2d"].latest_job.status == DrawingMetadataExtractionJob.STATUS_SUCCEEDED
    assert snapshots["2d"].latest_job.warnings_json == [{"code": "sample_warning"}]
    assert snapshots["3d"].canonical_attributes_json["top_part_name"] == "BRACKET"
    assert any(tag["tag"] == "材質:SUS304" for tag in snapshots["3d"].derived_tags_json)
    assert "imported=2" in stdout.getvalue()
    assert "created_drawings=1" in stdout.getvalue()


@pytest.mark.django_db
def test_import_drawing_metadata_extracts_accepts_manifest(tmp_path):
    source_path = r"J:\SAMPLE\MANIFEST-PART.icd"
    payload_3d = {
        "input_path": source_path,
        "source_format": "icad",
        "source_kind": "3d",
        "raw_extract": {
            "top_part": {"name": "MANIFEST-PART"},
            "parts": [{"tree_path": ["MANIFEST-PART"], "name": "MANIFEST-PART"}],
        },
    }
    extract_path = tmp_path / "MANIFEST-PART_3d.json"
    extract_path.write_text(json.dumps(payload_3d, ensure_ascii=False), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schemaVersion": "icad_extract_import_manifest.v1",
                "selectedPaths": [str(extract_path)],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    stdout = StringIO()

    call_command(
        "import_drawing_metadata_extracts",
        manifest=[str(manifest_path)],
        stdout=stdout,
    )

    drawing = RegisteredDrawing.objects.get(source_path=source_path)
    snapshot = DrawingMetadataSnapshot.objects.get(drawing=drawing, extraction_mode="3d")
    assert snapshot.canonical_attributes_json["top_part_name"] == "MANIFEST-PART"
    assert "imported=1" in stdout.getvalue()


@pytest.mark.django_db
def test_import_drawing_metadata_extracts_prefers_manifest_source_path(tmp_path):
    corrupted_source_path = r"J:\�A�[�X\PART.icd"
    canonical_source_path = r"J:\アースエンジニアリング\PART.icd"
    payload_3d = {
        "input_path": corrupted_source_path,
        "source_file": {
            "full_path": corrupted_source_path,
            "directory_path": r"J:\�A�[�X",
            "file_name": "�p�[�c.icd",
            "file_name_without_extension": "�p�[�c",
            "extension": ".icd",
        },
        "source_format": "icad",
        "source_kind": "3d",
        "raw_extract": {
            "top_part": {"name": "PART"},
            "parts": [{"tree_path": ["PART"], "name": "PART"}],
        },
    }
    extract_path = tmp_path / "PART.3d.json"
    extract_path.write_text(json.dumps(payload_3d, ensure_ascii=False), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schemaVersion": "icad_extract_import_manifest.v1",
                "selectedPaths": [str(extract_path)],
                "entries": [
                    {
                        "sourcePath": canonical_source_path,
                        "selectedFiles": [{"mode": "3d", "path": str(extract_path)}],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    call_command("import_drawing_metadata_extracts", manifest=[str(manifest_path)])

    drawing = RegisteredDrawing.objects.get(source_path=canonical_source_path)
    assert drawing.filename == "PART.icd"
    assert not RegisteredDrawing.objects.filter(source_path=corrupted_source_path).exists()
    snapshot = DrawingMetadataSnapshot.objects.get(drawing=drawing, extraction_mode="3d")
    assert snapshot.raw_extract_json["_source_file"]["full_path"] == canonical_source_path
    assert snapshot.raw_extract_json["_source_file"]["file_name"] == "PART.icd"


@pytest.mark.django_db
def test_import_drawing_metadata_extracts_rebinds_unique_moved_source_and_filters_filename(tmp_path):
    old_source_path = r"J:\OLD\MOVED.icd"
    moved_source_path = r"J:\NEW\MOVED.icd"
    existing = RegisteredDrawing.objects.create(
        filename="MOVED.icd",
        source_path=old_source_path,
        source_format="icad",
    )
    moved_extract = tmp_path / "MOVED.3d.json"
    moved_extract.write_text(
        json.dumps(
            {
                "input_path": old_source_path,
                "source_kind": "3d",
                "raw_extract": {
                    "top_part": {"name": "MOVED"},
                    "parts": [{"tree_path": ["MOVED"], "name": "MOVED"}],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    moved_2d_extract = tmp_path / "MOVED.2d.json"
    moved_2d_extract.write_text(
        json.dumps(
            {
                "input_path": old_source_path,
                "source_kind": "2d",
                "raw_extract": {"texts": [], "dimensions": [], "geometry_primitives": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    skipped_extract = tmp_path / "SKIPPED.3d.json"
    skipped_extract.write_text(
        json.dumps(
            {
                "input_path": r"J:\NEW\SKIPPED.icd",
                "source_kind": "3d",
                "raw_extract": {"top_part": {"name": "SKIPPED"}, "parts": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "sourcePath": moved_source_path,
                        "selectedFiles": [
                            {"mode": "2d", "path": str(moved_2d_extract)},
                            {"mode": "3d", "path": str(moved_extract)},
                        ],
                    },
                    {
                        "sourcePath": r"J:\NEW\SKIPPED.icd",
                        "selectedFiles": [{"mode": "3d", "path": str(skipped_extract)}],
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    call_command(
        "import_drawing_metadata_extracts",
        manifest=[str(manifest_path)],
        filename=["MOVED.icd"],
        manifest_mode="3d",
        rebind_moved_source=True,
    )

    existing.refresh_from_db()
    assert existing.source_path == moved_source_path
    assert RegisteredDrawing.objects.count() == 1
    snapshot = DrawingMetadataSnapshot.objects.get(drawing=existing, extraction_mode="3d")
    assert snapshot.raw_extract_json["_source_file"]["full_path"] == moved_source_path
    assert not DrawingMetadataSnapshot.objects.filter(drawing=existing, extraction_mode="2d").exists()


@pytest.mark.django_db
def test_export_drawing_metadata_fixtures_filters_by_manifest_source_path(tmp_path):
    included = RegisteredDrawing.objects.create(
        filename="included.icd",
        source_path=r"J:\SAMPLE\included.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(drawing=included, extraction_mode="3d")
    excluded = RegisteredDrawing.objects.create(
        filename="excluded.icd",
        source_path=r"J:\SAMPLE\excluded.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(drawing=excluded, extraction_mode="3d")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"entries": [{"sourcePath": included.source_path}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    output_path = tmp_path / "fixture.json"

    call_command(
        "export_drawing_metadata_fixtures",
        manifest=str(manifest_path),
        output=str(output_path),
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["itemCount"] == 1
    assert payload["items"][0]["filename"] == "included.icd"


@pytest.mark.django_db
def test_queue_missing_drawing_metadata_extracts_enqueues_condition_profiles():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="queue-missing",
        filename="queue-missing.icd",
        source_path=r"C:\temp\queue-missing.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={"drawing_name": "queue-missing"},
    )

    call_command("queue_missing_drawing_metadata_extracts", drawing_id=[str(drawing.id)], executed_by="test")

    job = DrawingMetadataExtractionJob.objects.get(drawing=drawing, extraction_mode="3d")
    assert job.status == DrawingMetadataExtractionJob.STATUS_QUEUED
    assert job.extraction_profile == "3d_parts_materials_ex_info"
    assert job.extraction_options_json["scanPartExtendedInfo"] is True
    assert job.diagnostics_json["reason"] == "missing_snapshot"
    assert job.diagnostics_json["requiredConditionChecks"] == [
        "partTree",
        "partMaterials",
        "partAttributes",
        "massProperties",
    ]
