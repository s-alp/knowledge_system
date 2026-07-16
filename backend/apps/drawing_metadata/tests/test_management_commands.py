from io import StringIO
import json

import pytest
from django.core.management import call_command

from apps.drawing_metadata.management.commands import register_cad_drawings
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
def test_register_cad_drawings_normalizes_display_filename(monkeypatch, tmp_path):
    cad_root = tmp_path / "cad_data"
    cad_root.mkdir()
    drawing = cad_root / "customer-long-name.icd"
    drawing.write_text("", encoding="utf-8")

    monkeypatch.setattr(register_cad_drawings, "normalize_icad_display_filename", lambda _filename: "short.icd")
    stdout = StringIO()

    call_command("register_cad_drawings", cad_root=str(cad_root), stdout=stdout)

    drawing_record = RegisteredDrawing.objects.get()
    assert drawing_record.filename == "short.icd"
    assert "CREATED: short.icd" in stdout.getvalue()
    assert "created=1" in stdout.getvalue()
    assert "skipped=0" in stdout.getvalue()


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
        "profile": "full",
        "includeEmptySnapshots": False,
        "emptySnapshotHandling": "skipped",
        "fileSizePolicy": "machine_handoff_full_payload",
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
        "profile": "full",
        "includeEmptySnapshots": True,
        "emptySnapshotHandling": "included",
        "fileSizePolicy": "machine_handoff_full_payload",
    }
    assert payload["items"][0]["detailApiPayload"]["snapshotsByMode"] == {}


@pytest.mark.django_db
def test_export_drawing_metadata_fixtures_review_summary_omits_heavy_payloads(tmp_path):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="host-summary",
        filename="summary.icd",
        source_path=r"C:\cad\summary.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        raw_extract_json={"texts": [{"joined_text": "材質 SUS304"}]},
        canonical_attributes_json={
            "drawing_name": "サマリ図面",
            "material_keywords": ["SUS304"],
            "unresolved_material_keywords": ["ZZZ"],
        },
        derived_tags_json=[{"tag": "材質:SUS304", "source": "material_keywords", "confidence": "high"}],
    )
    output_path = tmp_path / "souya_fixture_review_summary.json"

    call_command(
        "export_drawing_metadata_fixtures",
        drawing_id=[str(drawing.id)],
        profile="review-summary",
        output=str(output_path),
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "drawing_metadata_handoff_review_summary.v1"
    assert payload["exportPolicy"]["fileSizePolicy"] == "human_review_compact_no_raw_extract"
    item = payload["items"][0]
    assert "detailApiPayload" not in item
    assert "viewerBootstrap" not in item
    assert "ragPayload" not in item
    assert item["snapshotSummary"]["2d"]["rawExtractKeys"] == ["texts"]
    assert item["selectedAttributes"]["material_keywords"]["values"] == ["SUS304"]
    assert item["selectedAttributes"]["unresolved_material_keywords"]["values"] == ["ZZZ"]
    assert item["derivedTags"]["values"] == ["材質:SUS304"]


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
def test_renormalize_snapshots_applies_current_quality_rules_and_keeps_manual_values():
    drawing = RegisteredDrawing.objects.create(
        filename="quality.icd",
        source_path=r"J:\quality.icd",
        source_format="icad",
    )
    snapshot = DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        raw_extract_json={
            "_source_file": {"full_path": drawing.source_path, "file_name": drawing.filename},
            "texts": [
                {"text_lines": ["重量：0.4932kg"], "inside_print_area": True},
                {"text_lines": ["ワーク重量より12.4倍の吸引力がある"], "inside_print_area": True},
                {"text_lines": ["図番：参考：M24A88810"], "inside_print_area": True},
            ],
            "print_frames": [{"frame_no": 1}],
        },
        canonical_attributes_json={"title_block_fields": {"weight": "誤った旧値"}},
        derived_tags_json=[
            {"tag": "図面特徴旧タグ", "source": "geometry_feature_candidates", "manual_flag": False},
            {"tag": "利用者タグ", "source": "manual_override", "manual_flag": True},
        ],
        manual_overrides_json={"canonicalAttributes": {"drawing_name": "手動図面名"}},
    )

    call_command("renormalize_drawing_metadata_snapshots")

    snapshot.refresh_from_db()
    assert snapshot.canonical_attributes_json["title_block_fields"]["weight"] == "0.49 kg"
    assert snapshot.canonical_attributes_json["drawing_name"] == "手動図面名"
    assert [tag["tag"] for tag in snapshot.derived_tags_json] == ["利用者タグ"]


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


@pytest.mark.django_db
def test_backfill_drawing_metadata_failure_diagnostics_updates_failed_jobs(tmp_path):
    source_file = tmp_path / "failed.icd"
    source_file.write_bytes(b"icad-data")
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="failed-diagnostics",
        filename="failed.icd",
        source_path=str(source_file),
        source_format="icad",
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_FAILED,
        error_message="sxnet.SxException: 指定したファイルは図面ファイルではありません。",
    )
    stdout = StringIO()

    call_command("backfill_drawing_metadata_failure_diagnostics", stdout=stdout)

    job.refresh_from_db()
    assert job.diagnostics_json["failure"]["errorClass"] == "sxnet_rejected_as_not_drawing_file"
    assert job.diagnostics_json["failure"]["sourcePreflight"]["sourceExistsFromCurrentMachine"] is True
    assert "updated=1" in stdout.getvalue()


@pytest.mark.django_db
def test_backfill_drawing_metadata_failure_diagnostics_dry_run_does_not_update():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="failed-diagnostics-dry-run",
        filename="failed-dry-run.icd",
        source_path=r"C:\missing\failed-dry-run.icd",
        source_format="icad",
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        status=DrawingMetadataExtractionJob.STATUS_FAILED,
        error_message="missing",
    )
    stdout = StringIO()

    call_command("backfill_drawing_metadata_failure_diagnostics", dry_run=True, stdout=stdout)

    job.refresh_from_db()
    assert job.diagnostics_json == {}
    assert "would_update=1" in stdout.getvalue()
