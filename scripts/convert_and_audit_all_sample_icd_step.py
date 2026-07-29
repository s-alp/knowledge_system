"""共有ICADを全件STEPへ変換し、製品名・構成・材質・質量の保持率を監査する。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from convert_and_audit_all_sample_icd_dxf import (
    _conversion_asset_path,
    _decode_runner_output,
    _load_backend_env,
    _shutdown_icad_safely,
)


DEFAULT_MANIFEST = Path("output/souya_handoff/icad_extract_import_manifest_all_shared_2026-07-15.json")
DEFAULT_LOCAL_ICAD_ROOT = Path("cad_data")
DEFAULT_LIVE_EXTRACT_ROOT = Path("output/live_extracts")
DEFAULT_OUTPUT_ROOT = Path("output/step_full_audit_2026-07-28")
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_ICAD_STARTUP_WAIT_SECONDS = 30
DEFAULT_COMPLETION_GRACE_SECONDS = 5
DEFAULT_STEP_EXPORT_FILE_TYPE = 11

STEP_STRING_RE = re.compile(r"'((?:[^']|'')*)'")
STEP_ENTITY_WITH_ID_RE = re.compile(
    r"#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
STEP_REFERENCE_RE = re.compile(r"#(\d+)")
STEP_SCHEMA_RE = re.compile(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", re.IGNORECASE)
MATERIAL_RE = re.compile(
    r"(?<![A-Z0-9])"
    r"(SUS[0-9][0-9A-Z-]*|SS400[A-Z-]*|SPCC|S[0-9]{2}C|A[0-9]{4}P?|"
    r"AL|SKD[0-9]*|SKS[0-9]*|SCM[0-9]*|FC[0-9]*|FCD[0-9]*|"
    r"PETG|PET|POM|PVC|PTFE|PPS|NBR|EPDM|FKM|PP)"
    r"(?![A-Z0-9])",
    re.IGNORECASE,
)
EXTERNAL_REFERENCE_ENTITY_NAMES = {
    "APPLIED_EXTERNAL_IDENTIFICATION_ASSIGNMENT",
    "DOCUMENT_FILE",
    "EXTERNAL_SOURCE",
    "EXTERNALLY_DEFINED_CLASS",
    "EXTERNALLY_DEFINED_GENERAL_PROPERTY",
    "EXTERNALLY_DEFINED_ITEM",
    "EXTERNALLY_DEFINED_REPRESENTATION",
}
SOLID_ENTITY_NAMES = {
    "BREP_WITH_VOIDS",
    "FACETED_BREP",
    "MANIFOLD_SOLID_BREP",
}
EXPLICIT_MASS_ENTITY_NAMES = {
    "MASS_MEASURE_WITH_UNIT",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _path_key(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def _selected_3d_extract_path(entry: dict[str, Any]) -> str:
    for selected in entry.get("selectedFiles", []):
        if str(selected.get("mode") or "").lower() == "3d":
            return str(selected.get("path") or "")
    return ""


def _manifest_samples(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index, entry in enumerate(manifest.get("entries", []), start=1):
        samples.append(
            {
                "index": index,
                "sampleName": f"sample_{index:03d}",
                "sampleGroup": "shared_manifest",
                "sourcePath": str(entry.get("sourcePath") or ""),
                "filename": str(entry.get("filename") or ""),
                "customerHint": str(entry.get("customerHint") or ""),
                "sourceExtractPath": _selected_3d_extract_path(entry),
            }
        )
    return samples


def _extract_quality(payload: dict[str, Any]) -> tuple[int, int, int]:
    raw = payload.get("raw_extract") or {}
    parts = raw.get("parts") or []
    materials = raw.get("materials") or []
    return (
        len(parts),
        len(materials),
        1 if raw.get("mass_properties") else 0,
    )


def _live_extract_index(root: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    by_source_path: dict[str, tuple[tuple[int, int, int], Path]] = {}
    by_filename: dict[str, tuple[tuple[int, int, int], Path]] = {}
    if not root.exists():
        return {}, {}

    for path in root.rglob("*.json"):
        try:
            payload = _load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("source_kind") or "").lower() != "3d":
            continue
        raw = payload.get("raw_extract")
        if not isinstance(raw, dict):
            continue
        quality = _extract_quality(payload)
        source_path = str(payload.get("input_path") or (payload.get("source_file") or {}).get("full_path") or "")
        filename = str((payload.get("source_file") or {}).get("file_name") or Path(source_path).name)
        if source_path:
            key = _path_key(source_path)
            if key not in by_source_path or quality > by_source_path[key][0]:
                by_source_path[key] = (quality, path)
        if filename:
            key = filename.casefold()
            if key not in by_filename or quality > by_filename[key][0]:
                by_filename[key] = (quality, path)
    return (
        {key: value[1] for key, value in by_source_path.items()},
        {key: value[1] for key, value in by_filename.items()},
    )


def _append_local_samples(
    samples: list[dict[str, Any]],
    *,
    local_root: Path,
    extract_by_source: dict[str, Path],
    extract_by_filename: dict[str, Path],
) -> list[dict[str, Any]]:
    known_paths = {_path_key(sample["sourcePath"]) for sample in samples if sample.get("sourcePath")}
    local_paths = sorted(
        path
        for path in local_root.rglob("*")
        if path.is_file() and path.suffix.casefold() == ".icd"
    )
    local_index = 0
    for path in local_paths:
        resolved = path.resolve()
        if _path_key(resolved) in known_paths:
            continue
        local_index += 1
        extract_path = extract_by_source.get(_path_key(resolved))
        if extract_path is None:
            extract_path = extract_by_filename.get(path.name.casefold())
        samples.append(
            {
                "index": len(samples) + 1,
                "sampleName": f"cad_{local_index:03d}",
                "sampleGroup": "workspace_cad_data",
                "sourcePath": str(resolved),
                "filename": path.name,
                "customerHint": "",
                "sourceExtractPath": str(extract_path) if extract_path else "",
            }
        )
        known_paths.add(_path_key(resolved))
    return samples


def _build_convert_command(
    *,
    runner: str,
    sxnet_dll: str,
    icad_executable: str,
    source_path: str,
    output_path: Path,
    output_dir: Path,
    output_base_name: str,
    icad_startup_wait_seconds: int,
    step_export_file_type: int,
) -> list[str]:
    return [
        runner,
        "convert-cad",
        "--input-path",
        source_path,
        "--output-path",
        str(output_path),
        "--output-dir",
        str(output_dir),
        "--output-format",
        "step",
        "--sxnet-dll-path",
        sxnet_dll,
        "--icad-executable-path",
        icad_executable,
        "--icad-startup-wait-seconds",
        str(icad_startup_wait_seconds),
        "--shutdown-icad-if-autostarted",
        "true",
        "--force-sxnet-staged-input",
        "true",
        "--output-base-name",
        output_base_name,
        "--export-file-type",
        str(step_export_file_type),
    ]


def _find_generated_step(output_dir: Path) -> Path | None:
    candidates = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.suffix.casefold() in {".step", ".stp"}
    )
    if len(candidates) == 1:
        return candidates[0]
    return None


def _run_conversion(
    *,
    sample: dict[str, Any],
    runner: str,
    sxnet_dll: str,
    icad_executable: str,
    output_root: Path,
    timeout_seconds: int,
    icad_startup_wait_seconds: int,
    completion_grace_seconds: int,
    step_export_file_type: int,
    resume: bool,
    safe_shutdown_after_conversion: bool,
) -> dict[str, Any]:
    """1サンプルをSTEPへ変換し、timeout・標準出力・生成ファイルを個別結果へ記録する。"""

    sample_name = str(sample["sampleName"])
    source_path = Path(str(sample["sourcePath"]))
    result_path = output_root / "conversion_results" / f"{sample_name}.json"
    step_dir = output_root / "step" / sample_name
    result_path.parent.mkdir(parents=True, exist_ok=True)
    step_dir.mkdir(parents=True, exist_ok=True)

    if not source_path.exists():
        return {
            **sample,
            "conversionStatus": "missing_source",
            "conversionError": "対象ICADの実体がありません。",
            "conversionResultPath": str(result_path),
            "stepPath": None,
            "elapsedMs": 0,
            "exitCode": None,
        }

    if resume and result_path.exists():
        payload = _load_json(result_path)
        existing_step = _conversion_asset_path(payload) or _find_generated_step(step_dir)
        if existing_step and existing_step.exists() and existing_step.stat().st_size > 0:
            return {
                **sample,
                "conversionStatus": "reused",
                "conversionError": "",
                "conversionResultPath": str(result_path),
                "stepPath": str(existing_step),
                "elapsedMs": 0,
                "exitCode": 0,
            }

    command = _build_convert_command(
        runner=runner,
        sxnet_dll=sxnet_dll,
        icad_executable=icad_executable,
        source_path=str(source_path),
        output_path=result_path,
        output_dir=step_dir,
        output_base_name=sample_name,
        icad_startup_wait_seconds=icad_startup_wait_seconds,
        step_export_file_type=step_export_file_type,
    )
    started = time.perf_counter()
    started_wall_time = time.time()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timeout_error = ""
    completed_asset_at: float | None = None
    terminated_after_result = False

    while process.poll() is None:
        if result_path.exists() and result_path.stat().st_mtime >= started_wall_time:
            try:
                live_payload = _load_json(result_path)
            except (OSError, json.JSONDecodeError):
                live_payload = {}
            live_step = _conversion_asset_path(live_payload) or _find_generated_step(step_dir)
            if live_step and live_step.exists() and live_step.stat().st_size > 0:
                completed_asset_at = completed_asset_at or time.perf_counter()
                if time.perf_counter() - completed_asset_at >= completion_grace_seconds:
                    process.terminate()
                    terminated_after_result = True
                    break
        if time.perf_counter() - started >= timeout_seconds:
            timeout_error = f"conversion timed out after {timeout_seconds} seconds"
            process.kill()
            break
        time.sleep(0.5)

    try:
        stdout_bytes, stderr_bytes = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout_bytes, stderr_bytes = process.communicate()
    stdout = _decode_runner_output(stdout_bytes)
    stderr = _decode_runner_output(stderr_bytes)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    shutdown_result = (
        _shutdown_icad_safely(runner)
        if safe_shutdown_after_conversion
        else {"status": "not_requested", "exitCode": None, "stdout": "", "stderr": ""}
    )

    payload: dict[str, Any] = {}
    if result_path.exists():
        try:
            payload = _load_json(result_path)
        except (OSError, json.JSONDecodeError) as exc:
            return {
                **sample,
                "conversionStatus": "invalid_result_json",
                "conversionError": str(exc),
                "conversionResultPath": str(result_path),
                "stepPath": None,
                "elapsedMs": elapsed_ms,
                "exitCode": process.returncode,
                "stdoutTail": stdout[-3000:],
                "stderrTail": stderr[-3000:],
                "icadShutdown": shutdown_result,
            }

    step_path = _conversion_asset_path(payload) or _find_generated_step(step_dir)
    if step_path and step_path.exists() and step_path.stat().st_size > 0:
        status = "converted"
        if timeout_error:
            status = "converted_after_timeout"
        elif terminated_after_result:
            status = "converted_after_result"
        return {
            **sample,
            "conversionStatus": status,
            "conversionError": timeout_error,
            "conversionResultPath": str(result_path),
            "stepPath": str(step_path),
            "elapsedMs": elapsed_ms,
            "exitCode": process.returncode,
            "stdoutTail": stdout[-3000:],
            "stderrTail": stderr[-3000:],
            "icadShutdown": shutdown_result,
        }

    failure_detail = timeout_error or stderr.strip() or stdout.strip()
    if not failure_detail:
        failure_detail = f"runner exited with code {process.returncode}"
    return {
        **sample,
        "conversionStatus": "failed",
        "conversionError": failure_detail[-5000:],
        "conversionResultPath": str(result_path),
        "stepPath": str(step_path) if step_path else None,
        "elapsedMs": elapsed_ms,
        "exitCode": process.returncode,
        "stdoutTail": stdout[-3000:],
        "stderrTail": stderr[-3000:],
        "icadShutdown": shutdown_result,
    }


def _step_strings(value: str) -> list[str]:
    return [
        item.replace("''", "'").strip()
        for item in STEP_STRING_RE.findall(value)
        if item.strip()
    ]


def _unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _entity_records(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for entity_id, entity_name, body in STEP_ENTITY_WITH_ID_RE.findall(text):
        records.append(
            {
                "id": f"#{entity_id}",
                "entityName": entity_name.upper(),
                "strings": _step_strings(body),
                "references": [f"#{value}" for value in STEP_REFERENCE_RE.findall(body)],
            }
        )
    return records


def _product_name_for_ref(
    entity_ref: str,
    entity_by_id: dict[str, dict[str, Any]],
    seen: set[str] | None = None,
) -> str | None:
    visited = seen or set()
    if entity_ref in visited:
        return None
    visited.add(entity_ref)
    entity = entity_by_id.get(entity_ref)
    if not entity:
        return None
    strings = entity.get("strings") or []
    if entity.get("entityName") == "PRODUCT" and strings:
        return str(strings[0])
    for child_ref in entity.get("references") or []:
        product_name = _product_name_for_ref(child_ref, entity_by_id, visited)
        if product_name:
            return product_name
    return None


def _assembly_depth(relationships: list[dict[str, Any]]) -> int:
    children_by_parent: dict[str, list[str]] = {}
    child_names: set[str] = set()
    for relationship in relationships:
        parent = str(relationship.get("parentName") or "")
        child = str(relationship.get("childName") or "")
        if not parent or not child:
            continue
        children_by_parent.setdefault(parent.casefold(), []).append(child)
        child_names.add(child.casefold())
    root_names = [
        parent
        for parent in children_by_parent
        if parent not in child_names
    ]
    if not root_names:
        return 1 if relationships else 0

    def depth(name: str, seen: set[str]) -> int:
        key = name.casefold()
        if key in seen:
            return 0
        next_seen = {*seen, key}
        children = children_by_parent.get(key) or []
        if not children:
            return 1
        return 1 + max(depth(child, next_seen) for child in children)

    return max(depth(root, set()) for root in root_names)


def _audit_step(path: Path) -> dict[str, Any]:
    """STEPエンティティを解析し、製品名・親子関係・構成深さ・材質候補を集計する。"""

    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    records = _entity_records(text)
    entity_by_id = {record["id"]: record for record in records}
    products = [
        {
            "entityId": record["id"],
            "name": record["strings"][0],
            "description": record["strings"][1] if len(record["strings"]) > 1 else None,
        }
        for record in records
        if record["entityName"] == "PRODUCT" and record["strings"]
    ]
    relationships: list[dict[str, Any]] = []
    for record in records:
        if record["entityName"] != "NEXT_ASSEMBLY_USAGE_OCCURRENCE":
            continue
        refs = record["references"]
        relationships.append(
            {
                "entityId": record["id"],
                "parentRef": refs[0] if len(refs) >= 1 else None,
                "childRef": refs[1] if len(refs) >= 2 else None,
                "parentName": _product_name_for_ref(refs[0], entity_by_id) if len(refs) >= 1 else None,
                "childName": _product_name_for_ref(refs[1], entity_by_id) if len(refs) >= 2 else None,
            }
        )
    strings = _unique_strings(_step_strings(text))
    materials = _unique_strings(
        matched.group(1).upper()
        for token in strings
        for matched in MATERIAL_RE.finditer(token)
    )
    entity_names = [str(record["entityName"]) for record in records]
    external_entities = [
        record
        for record in records
        if record["entityName"] in EXTERNAL_REFERENCE_ENTITY_NAMES
        or "EXTERNAL" in record["entityName"]
    ]
    explicit_mass_entities = [
        record
        for record in records
        if record["entityName"] in EXPLICIT_MASS_ENTITY_NAMES
    ]
    schema_match = STEP_SCHEMA_RE.search(text)
    return {
        "path": str(path),
        "sizeBytes": len(data),
        "fileSchema": schema_match.group(1) if schema_match else None,
        "entityCount": len(records),
        "productNames": _unique_strings(product["name"] for product in products),
        "products": products,
        "assemblyRelationshipCount": len(relationships),
        "assemblyDepth": _assembly_depth(relationships),
        "assemblyRelationships": relationships,
        "materialKeywords": materials,
        "externalReferenceEntityCount": len(external_entities),
        "externalReferenceEntityNames": sorted(
            {str(record["entityName"]) for record in external_entities}
        ),
        "explicitMassEntityCount": len(explicit_mass_entities),
        "solidEntityCount": sum(name in SOLID_ENTITY_NAMES for name in entity_names),
        "closedShellCount": entity_names.count("CLOSED_SHELL"),
    }


def _source_material_ids(raw: dict[str, Any]) -> list[str]:
    values: list[str] = []
    material_rows: list[Any] = list(raw.get("materials") or [])
    for part in raw.get("parts") or []:
        material_rows.extend(part.get("materials") or [])
    for material in material_rows:
        if isinstance(material, dict):
            value = material.get("mat_id") or material.get("material_id")
        else:
            value = material
        if value:
            values.append(str(value).upper())
    return _unique_strings(values)


def _audit_source_extract(path_value: str) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    payload = _load_json(path)
    raw = payload.get("raw_extract") or {}
    parts = raw.get("parts") or []
    names = _unique_strings(
        str(part.get("name") or "")
        for part in parts
        if part.get("name")
    )
    external_parts = [part for part in parts if part.get("is_external") is True]
    internal_parts = [part for part in parts if part.get("is_external") is False]
    max_depth = max(
        (len(part.get("tree_path") or []) for part in parts),
        default=0,
    )
    return {
        "path": str(path),
        "partOccurrenceCount": len(parts),
        "uniquePartNames": names,
        "uniquePartNameCount": len(names),
        "externalPartCount": len(external_parts),
        "externalPartNames": _unique_strings(
            str(part.get("name") or "")
            for part in external_parts
            if part.get("name")
        ),
        "internalPartCount": len(internal_parts),
        "maxTreeDepth": max_depth,
        "materialIds": _source_material_ids(raw),
        "massAvailable": bool(raw.get("mass_properties")),
        "massProbeStatus": raw.get("mass_probe_status"),
    }


def _overlap(left: Iterable[str], right: Iterable[str]) -> dict[str, Any]:
    left_values = _unique_strings(str(value) for value in left)
    right_values = _unique_strings(str(value) for value in right)
    right_by_key = {value.casefold(): value for value in right_values}
    overlap_values = [
        value
        for value in left_values
        if value.casefold() in right_by_key
    ]
    return {
        "leftCount": len(left_values),
        "rightCount": len(right_values),
        "overlapCount": len(overlap_values),
        "overlapValues": overlap_values,
        "leftOnly": [
            value
            for value in left_values
            if value.casefold() not in right_by_key
        ],
        "rightOnly": [
            value
            for value in right_values
            if value.casefold() not in {item.casefold() for item in left_values}
        ],
    }


def _audit_conversion_result(
    conversion_result: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    """元ICAD抽出と変換後STEPを同じ観点へそろえ、保持できた値と欠落値を比較する。"""

    step_path_value = conversion_result.get("stepPath")
    if not step_path_value:
        return {
            **conversion_result,
            "auditStatus": "not_audited",
            "auditError": conversion_result.get("conversionError") or "STEP成果物がありません。",
            "auditPath": None,
            "sourceAudit": _audit_source_extract(str(conversion_result.get("sourceExtractPath") or "")),
            "stepAudit": None,
            "comparison": None,
        }
    step_path = Path(str(step_path_value))
    try:
        step_audit = _audit_step(step_path)
        source_audit = _audit_source_extract(str(conversion_result.get("sourceExtractPath") or ""))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            **conversion_result,
            "auditStatus": "audit_failed",
            "auditError": str(exc),
            "auditPath": None,
            "sourceAudit": None,
            "stepAudit": None,
            "comparison": None,
        }

    comparison: dict[str, Any] | None = None
    if source_audit:
        comparison = {
            "partNameOverlap": _overlap(
                source_audit["uniquePartNames"],
                step_audit["productNames"],
            ),
            "externalPartNameOverlap": _overlap(
                source_audit["externalPartNames"],
                step_audit["productNames"],
            ),
            "materialOverlap": _overlap(
                source_audit["materialIds"],
                step_audit["materialKeywords"],
            ),
            "sourceHasExternalParts": source_audit["externalPartCount"] > 0,
            "stepHasExternalReferenceSignals": step_audit["externalReferenceEntityCount"] > 0,
            "sourceMassAvailable": source_audit["massAvailable"],
            "stepHasExplicitMassSignals": step_audit["explicitMassEntityCount"] > 0,
        }
    audit_payload = {
        "schemaVersion": "icad_step_file_audit.v1",
        "sampleName": conversion_result["sampleName"],
        "sourcePath": conversion_result["sourcePath"],
        "sourceExtract": source_audit,
        "step": step_audit,
        "comparison": comparison,
    }
    audit_path = output_root / "per_file_audit" / f"{conversion_result['sampleName']}.audit.json"
    _write_json(audit_path, audit_payload)
    return {
        **conversion_result,
        "auditStatus": "audited",
        "auditError": "",
        "auditPath": str(audit_path),
        "sourceAudit": source_audit,
        "stepAudit": step_audit,
        "comparison": comparison,
    }


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """全サンプルの変換成否と、製品・構成・材質・質量の一致度を集約する。"""

    source_audited = [result for result in results if result.get("sourceAudit")]
    step_audited = [result for result in results if result.get("stepAudit")]
    comparable = [result for result in results if result.get("comparison")]
    source_external = [
        result
        for result in comparable
        if result["comparison"]["sourceHasExternalParts"]
    ]
    source_material = [
        result
        for result in comparable
        if result["sourceAudit"]["materialIds"]
    ]
    source_mass = [
        result
        for result in comparable
        if result["sourceAudit"]["massAvailable"]
    ]
    return {
        "targetCount": len(results),
        "sharedManifestCount": sum(result["sampleGroup"] == "shared_manifest" for result in results),
        "workspaceCadDataCount": sum(result["sampleGroup"] == "workspace_cad_data" for result in results),
        "sourceAvailableCount": sum(Path(str(result["sourcePath"])).exists() for result in results),
        "sourceMissingCount": sum(not Path(str(result["sourcePath"])).exists() for result in results),
        "convertedCount": sum(
            str(result.get("conversionStatus") or "").startswith(("converted", "reused"))
            for result in results
        ),
        "conversionFailedCount": sum(
            result.get("conversionStatus") not in {
                "converted",
                "converted_after_result",
                "converted_after_timeout",
                "reused",
                "missing_source",
            }
            for result in results
        ),
        "auditedStepCount": len(step_audited),
        "sourceExtractAvailableCount": len(source_audited),
        "comparableCount": len(comparable),
        "filesWithStepProducts": sum(bool(result["stepAudit"]["productNames"]) for result in step_audited),
        "filesWithStepAssemblyRelationships": sum(
            result["stepAudit"]["assemblyRelationshipCount"] > 0
            for result in step_audited
        ),
        "filesWithStepExternalReferenceSignals": sum(
            result["stepAudit"]["externalReferenceEntityCount"] > 0
            for result in step_audited
        ),
        "sourceFilesWithExternalParts": len(source_external),
        "sourceExternalButNoStepExternalSignal": sum(
            not result["comparison"]["stepHasExternalReferenceSignals"]
            for result in source_external
        ),
        "sourceFilesWithMaterials": len(source_material),
        "sourceMaterialWithAnyStepOverlap": sum(
            result["comparison"]["materialOverlap"]["overlapCount"] > 0
            for result in source_material
        ),
        "sourceFilesWithMass": len(source_mass),
        "sourceMassWithStepExplicitSignal": sum(
            result["comparison"]["stepHasExplicitMassSignals"]
            for result in source_mass
        ),
        "filesWithAnyPartNameOverlap": sum(
            result["comparison"]["partNameOverlap"]["overlapCount"] > 0
            for result in comparable
        ),
        "filesWithAnyExternalPartNameOverlap": sum(
            result["comparison"]["externalPartNameOverlap"]["overlapCount"] > 0
            for result in source_external
        ),
    }


def _flat_result(result: dict[str, Any]) -> dict[str, Any]:
    source = result.get("sourceAudit") or {}
    step = result.get("stepAudit") or {}
    comparison = result.get("comparison") or {}
    return {
        "sampleName": result["sampleName"],
        "sampleGroup": result["sampleGroup"],
        "filename": result["filename"],
        "sourcePath": result["sourcePath"],
        "sourceExists": Path(str(result["sourcePath"])).exists(),
        "conversionStatus": result.get("conversionStatus"),
        "auditStatus": result.get("auditStatus"),
        "stepPath": result.get("stepPath"),
        "sourcePartOccurrenceCount": source.get("partOccurrenceCount"),
        "sourceExternalPartCount": source.get("externalPartCount"),
        "sourceInternalPartCount": source.get("internalPartCount"),
        "sourceMaxTreeDepth": source.get("maxTreeDepth"),
        "stepProductCount": len(step.get("productNames") or []),
        "stepAssemblyRelationshipCount": step.get("assemblyRelationshipCount"),
        "stepAssemblyDepth": step.get("assemblyDepth"),
        "stepExternalReferenceEntityCount": step.get("externalReferenceEntityCount"),
        "partNameOverlapCount": (comparison.get("partNameOverlap") or {}).get("overlapCount"),
        "externalPartNameOverlapCount": (comparison.get("externalPartNameOverlap") or {}).get("overlapCount"),
        "sourceMaterialCount": len(source.get("materialIds") or []),
        "stepMaterialCount": len(step.get("materialKeywords") or []),
        "materialOverlapCount": (comparison.get("materialOverlap") or {}).get("overlapCount"),
        "sourceMassAvailable": source.get("massAvailable"),
        "stepExplicitMassEntityCount": step.get("explicitMassEntityCount"),
        "conversionError": result.get("conversionError"),
        "auditError": result.get("auditError"),
    }


def _write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    rows = [_flat_result(result) for result in results]
    if not rows:
        raise ValueError("CSVへ出力する監査結果がありません。")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(
    path: Path,
    *,
    manifest_path: Path,
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    lines = [
        "# 既存テスト用ICAD全件 STEP変換・構造監査",
        "",
        f"- 生成日時: {datetime.now(timezone.utc).isoformat()}",
        f"- manifest: `{manifest_path}`",
        f"- 対象: {summary['targetCount']}件",
        f"- 参照可能: {summary['sourceAvailableCount']}件",
        f"- STEP変換成功: {summary['convertedCount']}件",
        f"- STEP監査成功: {summary['auditedStepCount']}件",
        f"- 元3D抽出結果と比較可能: {summary['comparableCount']}件",
        "",
        "## 横断結果",
        "",
        f"- 元ICADで外部パーツあり: {summary['sourceFilesWithExternalParts']}件",
        f"- 上記のうちSTEPに外部参照シグナルなし: {summary['sourceExternalButNoStepExternalSignal']}件",
        f"- 元ICADで材質あり: {summary['sourceFilesWithMaterials']}件",
        f"- 上記のうちSTEPと材質が1件以上一致: {summary['sourceMaterialWithAnyStepOverlap']}件",
        f"- 元ICADで質量あり: {summary['sourceFilesWithMass']}件",
        f"- 上記のうちSTEPに明示的な質量シグナルあり: {summary['sourceMassWithStepExplicitSignal']}件",
        f"- 部品名が1件以上一致: {summary['filesWithAnyPartNameOverlap']}件",
        f"- 外部パーツ名が1件以上一致: {summary['filesWithAnyExternalPartNameOverlap']}件",
        "",
        "## ファイル別",
        "",
        "| No. | ファイル | 変換 | 元外部 | 元内部 | STEP製品 | STEP関係 | STEP外部参照 | 部品名一致 | 材質一致 | 元質量 |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        row = _flat_result(result)
        lines.append(
            f"| {result['index']} | {result['filename']} | {row['conversionStatus']} | "
            f"{row['sourceExternalPartCount'] if row['sourceExternalPartCount'] is not None else '-'} | "
            f"{row['sourceInternalPartCount'] if row['sourceInternalPartCount'] is not None else '-'} | "
            f"{row['stepProductCount']} | "
            f"{row['stepAssemblyRelationshipCount'] if row['stepAssemblyRelationshipCount'] is not None else '-'} | "
            f"{row['stepExternalReferenceEntityCount'] if row['stepExternalReferenceEntityCount'] is not None else '-'} | "
            f"{row['partNameOverlapCount'] if row['partNameOverlapCount'] is not None else '-'} | "
            f"{row['materialOverlapCount'] if row['materialOverlapCount'] is not None else '-'} | "
            f"{'あり' if row['sourceMassAvailable'] else 'なし／未比較'} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """manifestと追加サンプルを確定し、変換、比較監査、成果物保存を順に実行する。"""

    parser = argparse.ArgumentParser(
        description="既存テスト用ICADを全件STEPへ変換し、元ICAD抽出結果と構造・属性を比較監査します。"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--local-icad-root", type=Path, default=DEFAULT_LOCAL_ICAD_ROOT)
    parser.add_argument("--live-extract-root", type=Path, default=DEFAULT_LIVE_EXTRACT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--icad-startup-wait-seconds",
        type=int,
        default=DEFAULT_ICAD_STARTUP_WAIT_SECONDS,
    )
    parser.add_argument(
        "--completion-grace-seconds",
        type=int,
        default=DEFAULT_COMPLETION_GRACE_SECONDS,
    )
    parser.add_argument(
        "--step-export-file-type",
        type=int,
        default=DEFAULT_STEP_EXPORT_FILE_TYPE,
    )
    parser.add_argument("--runner")
    parser.add_argument("--sxnet-dll")
    parser.add_argument("--icad-executable")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--safe-shutdown-after-conversion", action="store_true")
    parser.add_argument("--index", type=int, action="append", default=[])
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    backend_env = _load_backend_env(Path("backend/.env"))
    runner = args.runner or backend_env.get("DRAWING_METADATA_EXTRACTOR_EXECUTABLE")
    sxnet_dll = args.sxnet_dll or backend_env.get("DRAWING_METADATA_SXNET_DLL_PATH")
    icad_executable = args.icad_executable or backend_env.get("DRAWING_METADATA_ICAD_EXECUTABLE")
    missing_settings = [
        name
        for name, value in (
            ("runner", runner),
            ("sxnet_dll", sxnet_dll),
            ("icad_executable", icad_executable),
        )
        if not value or not Path(str(value)).exists()
    ]
    if missing_settings:
        raise SystemExit(
            "必要な実行設定が不足または無効です: "
            + ", ".join(missing_settings)
        )

    manifest = _load_json(args.manifest)
    extract_by_source, extract_by_filename = _live_extract_index(args.live_extract_root)
    samples = _append_local_samples(
        _manifest_samples(manifest),
        local_root=args.local_icad_root,
        extract_by_source=extract_by_source,
        extract_by_filename=extract_by_filename,
    )
    if args.index:
        requested_indexes = set(args.index)
        samples = [
            sample
            for sample in samples
            if int(sample["index"]) in requested_indexes
        ]
        found_indexes = {int(sample["index"]) for sample in samples}
        missing_indexes = sorted(requested_indexes - found_indexes)
        if missing_indexes:
            raise SystemExit(
                "対象一覧に存在しないindexです: "
                + ", ".join(str(index) for index in missing_indexes)
            )
    elif args.limit is not None:
        samples = samples[: args.limit]
    args.output_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    total = len(samples)
    for position, sample in enumerate(samples, start=1):
        print(
            f"{position:03d}/{total:03d} converting {sample['filename']}",
            flush=True,
        )
        conversion_result = _run_conversion(
            sample=sample,
            runner=str(runner),
            sxnet_dll=str(sxnet_dll),
            icad_executable=str(icad_executable),
            output_root=args.output_root,
            timeout_seconds=args.timeout_seconds,
            icad_startup_wait_seconds=args.icad_startup_wait_seconds,
            completion_grace_seconds=args.completion_grace_seconds,
            step_export_file_type=args.step_export_file_type,
            resume=args.resume,
            safe_shutdown_after_conversion=args.safe_shutdown_after_conversion,
        )
        audited_result = _audit_conversion_result(conversion_result, args.output_root)
        results.append(audited_result)
        step_audit = audited_result.get("stepAudit") or {}
        source_audit = audited_result.get("sourceAudit") or {}
        print(
            f"{position:03d}/{total:03d} "
            f"{audited_result['conversionStatus']}/{audited_result['auditStatus']} "
            f"SRC_EXT={source_audit.get('externalPartCount', '-')} "
            f"PRODUCT={len(step_audit.get('productNames') or [])} "
            f"REL={step_audit.get('assemblyRelationshipCount', '-')} "
            f"STEP_EXT={step_audit.get('externalReferenceEntityCount', '-')}",
            flush=True,
        )

    summary = _summary(results)
    report = {
        "schemaVersion": "icad_step_full_audit.v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest),
        "localIcadRoot": str(args.local_icad_root),
        "liveExtractRoot": str(args.live_extract_root),
        "outputRoot": str(args.output_root),
        "stepExportFileType": args.step_export_file_type,
        "summary": summary,
        "results": results,
    }
    summary_json = args.output_root / "summary.json"
    summary_csv = args.output_root / "summary.csv"
    summary_md = args.output_root / "summary.md"
    _write_json(summary_json, report)
    _write_csv(summary_csv, results)
    _write_markdown(
        summary_md,
        manifest_path=args.manifest,
        summary=summary,
        results=results,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(f"summary_json={summary_json}", flush=True)
    print(f"summary_csv={summary_csv}", flush=True)
    print(f"summary_md={summary_md}", flush=True)


if __name__ == "__main__":
    main()
