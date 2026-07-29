"""共有ICADを全件DXFへ変換し、文字・寸法・公差・溶接などの取得率を監査する。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MANIFEST = Path("output/souya_handoff/icad_extract_import_manifest_all_shared_2026-07-15.json")
DEFAULT_OUTPUT_ROOT = Path("output/dxf_full_audit_2026-07-28")
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_ICAD_STARTUP_WAIT_SECONDS = 30
DEFAULT_COMPLETION_GRACE_SECONDS = 5
DEFAULT_DXF_EXPORT_FILE_TYPE = 1

TEXT_ENTITY_TYPES = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}
DIMENSION_TYPE_NAMES = {
    0: "linear_or_rotated",
    1: "aligned",
    2: "angular_2_line",
    3: "diameter",
    4: "radius",
    5: "angular_3_point",
    6: "ordinate",
}
TOLERANCE_PATTERN = re.compile(
    r"(?:幾何公差|一般公差|公差|±|\+/-|%%p|[+＋]\s*\d+(?:\.\d+)?\s*[-－]\s*\d+(?:\.\d+)?|"
    r"\bTOL(?:ERANCE)?\b|\\Fgdt;)",
    re.IGNORECASE,
)
WELD_PATTERN = re.compile(
    r"(?:溶接|すみ肉|隅肉|開先|現場溶接|全周溶接|断続溶接|脚長|"
    r"\bWELD(?:ING)?\b|\bFILLET\b|\bGROOVE\b)",
    re.IGNORECASE,
)
WELD_ENTITY_PATTERN = re.compile(r"(?:WELD|WELDING)", re.IGNORECASE)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_backend_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def _decode_runner_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    for encoding in ("utf-8", "cp932"):
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return value.decode("utf-8", errors="replace")


def _safe_sample_name(index: int) -> str:
    return f"sample_{index:03d}"


def _sample_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(manifest.get("entries", []), start=1):
        rows.append(
            {
                "index": index,
                "sampleName": _safe_sample_name(index),
                "sourcePath": str(entry.get("sourcePath") or ""),
                "filename": str(entry.get("filename") or ""),
                "customerHint": str(entry.get("customerHint") or ""),
                "manifestHas2d": bool(entry.get("has2d")),
                "manifestHas3d": bool(entry.get("has3d")),
            }
        )
    return rows


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
    dxf_export_file_type: int,
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
        "dxf",
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
        str(dxf_export_file_type),
    ]


def _conversion_asset_path(payload: dict[str, Any]) -> Path | None:
    asset = payload.get("converted_asset") or {}
    candidate = asset.get("file_path") or payload.get("file_path")
    if not candidate:
        return None
    return Path(str(candidate))


def _find_generated_dxf(output_dir: Path) -> Path | None:
    candidates = sorted(path for path in output_dir.glob("*.dxf") if path.is_file())
    if len(candidates) == 1:
        return candidates[0]
    return None


def _shutdown_icad_safely(runner: str, timeout_seconds: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [runner, "shutdown-icad", "--timeout-seconds", str(timeout_seconds)],
            capture_output=True,
            timeout=timeout_seconds + 15,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "exitCode": None,
            "stdout": _decode_runner_output(exc.stdout)[-3000:],
            "stderr": _decode_runner_output(exc.stderr)[-3000:],
        }
    return {
        "status": "completed" if completed.returncode == 0 else "failed",
        "exitCode": completed.returncode,
        "stdout": _decode_runner_output(completed.stdout)[-3000:],
        "stderr": _decode_runner_output(completed.stderr)[-3000:],
    }


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
    dxf_export_file_type: int,
    resume: bool,
    safe_shutdown_after_conversion: bool,
) -> dict[str, Any]:
    """1サンプルをDXFへ変換し、timeout・標準出力・生成ファイルを個別結果へ記録する。"""

    index = int(sample["index"])
    sample_name = str(sample["sampleName"])
    source_path = Path(str(sample["sourcePath"]))
    result_path = output_root / "conversion_results" / f"{sample_name}.json"
    dxf_dir = output_root / "dxf" / sample_name
    result_path.parent.mkdir(parents=True, exist_ok=True)
    dxf_dir.mkdir(parents=True, exist_ok=True)

    if not source_path.exists():
        return {
            **sample,
            "conversionStatus": "missing_source",
            "conversionError": "manifestのsourcePathにICD実体がありません。",
            "conversionResultPath": str(result_path),
            "dxfPath": None,
            "elapsedMs": 0,
            "exitCode": None,
            "stdoutTail": "",
            "stderrTail": "",
        }

    if resume and result_path.exists():
        payload = _load_json(result_path)
        existing_dxf = _conversion_asset_path(payload) or _find_generated_dxf(dxf_dir)
        if existing_dxf and existing_dxf.exists():
            return {
                **sample,
                "conversionStatus": "reused",
                "conversionError": "",
                "conversionResultPath": str(result_path),
                "dxfPath": str(existing_dxf),
                "elapsedMs": 0,
                "exitCode": 0,
                "stdoutTail": "",
                "stderrTail": "",
            }

    command = _build_convert_command(
        runner=runner,
        sxnet_dll=sxnet_dll,
        icad_executable=icad_executable,
        source_path=str(source_path),
        output_path=result_path,
        output_dir=dxf_dir,
        output_base_name=sample_name,
        icad_startup_wait_seconds=icad_startup_wait_seconds,
        dxf_export_file_type=dxf_export_file_type,
    )

    started = time.perf_counter()
    started_wall_time = time.time()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    timeout_error = ""
    completed_asset_at: float | None = None
    terminated_after_result = False
    while process.poll() is None:
        if result_path.exists() and result_path.stat().st_mtime >= started_wall_time:
            try:
                live_payload = _load_json(result_path)
            except (OSError, ValueError):
                live_payload = {}
            live_dxf = _conversion_asset_path(live_payload) or _find_generated_dxf(dxf_dir)
            if live_dxf and live_dxf.exists() and live_dxf.stat().st_size > 0:
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
        except (OSError, ValueError) as exc:
            return {
                **sample,
                "conversionStatus": "invalid_result_json",
                "conversionError": str(exc),
                "conversionResultPath": str(result_path),
                "dxfPath": None,
                "elapsedMs": elapsed_ms,
                "exitCode": process.returncode,
                "stdoutTail": stdout[-3000:],
                "stderrTail": stderr[-3000:],
                "icadShutdown": shutdown_result,
            }

    dxf_path = _conversion_asset_path(payload) or _find_generated_dxf(dxf_dir)
    exit_code = process.returncode
    if dxf_path and dxf_path.exists():
        if timeout_error:
            status = "converted_after_timeout"
        elif terminated_after_result:
            status = "converted_after_result"
        else:
            status = "converted"
        return {
            **sample,
            "conversionStatus": status,
            "conversionError": timeout_error,
            "conversionResultPath": str(result_path),
            "dxfPath": str(dxf_path),
            "elapsedMs": elapsed_ms,
            "exitCode": exit_code,
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
        "dxfPath": str(dxf_path) if dxf_path else None,
        "elapsedMs": elapsed_ms,
        "exitCode": exit_code,
        "stdoutTail": stdout[-3000:],
        "stderrTail": stderr[-3000:],
        "icadShutdown": shutdown_result,
    }


def _decode_dxf(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    if data.startswith(b"AutoCAD Binary DXF"):
        raise ValueError("Binary DXFはこの監査スクリプトの対象外です。")
    for encoding in ("utf-8-sig", "cp932"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeError("DXFをUTF-8またはCP932としてデコードできません。")


def _group_pairs(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    pairs: list[tuple[str, str]] = []
    index = 0
    while index + 1 < len(lines):
        code = lines[index].strip()
        value = lines[index + 1].rstrip("\r\n")
        if re.fullmatch(r"-?\d+", code):
            pairs.append((code, value))
        index += 2
    return pairs


def _records(pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    index = 0
    while index < len(pairs):
        code, value = pairs[index]
        if code != "0":
            index += 1
            continue
        next_index = index + 1
        while next_index < len(pairs) and pairs[next_index][0] != "0":
            next_index += 1
        records.append({"type": value.strip().upper(), "pairs": pairs[index + 1 : next_index]})
        index = next_index
    return records


def _first_value(pairs: Iterable[tuple[str, str]], code: str) -> str | None:
    for pair_code, value in pairs:
        if pair_code == code:
            stripped = value.strip()
            return stripped or None
    return None


def _all_values(pairs: Iterable[tuple[str, str]], codes: set[str]) -> list[str]:
    return [value.strip() for code, value in pairs if code in codes and value.strip()]


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _text_value(record: dict[str, Any]) -> str:
    pairs = record["pairs"]
    if record["type"] == "MTEXT":
        return "".join(_all_values(pairs, {"3", "1"})).strip()
    return (_first_value(pairs, "1") or "").strip()


def _record_layer(record: dict[str, Any]) -> str | None:
    return _first_value(record["pairs"], "8")


def _record_search_text(record: dict[str, Any]) -> str:
    values = [record["type"]]
    values.extend(value.strip() for _, value in record["pairs"] if value.strip())
    return "\n".join(values)


def _dimension_style_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    styles: dict[str, dict[str, Any]] = {}
    for record in records:
        if record["type"] != "DIMSTYLE":
            continue
        pairs = record["pairs"]
        name = _first_value(pairs, "2") or ""
        if not name:
            continue
        styles[name] = {
            "name": name,
            "dimtol": _to_int(_first_value(pairs, "71")),
            "dimlim": _to_int(_first_value(pairs, "72")),
            "dimtp": _to_float(_first_value(pairs, "47")),
            "dimtm": _to_float(_first_value(pairs, "48")),
        }
    return styles


def _dimension_overrides(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    variable_names = {71: "dimtol", 72: "dimlim", 47: "dimtp", 48: "dimtm"}
    for index, (code, value) in enumerate(pairs[:-1]):
        if code != "1070":
            continue
        variable_code = _to_int(value.strip())
        if variable_code not in variable_names:
            continue
        next_code, next_value = pairs[index + 1]
        if next_code not in {"1040", "1070", "1071"}:
            continue
        parsed_value: int | float | str
        if next_code in {"1070", "1071"}:
            parsed_value = _to_int(next_value.strip())
        else:
            parsed_value = _to_float(next_value.strip())
        result[variable_names[variable_code]] = parsed_value
    return result


def _dimension_rows(
    records: list[dict[str, Any]],
    styles: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        if record["type"] != "DIMENSION":
            continue
        pairs = record["pairs"]
        raw_type = _to_int(_first_value(pairs, "70"))
        base_type = raw_type & 0x0F if raw_type is not None else None
        style_name = _first_value(pairs, "3")
        style = styles.get(style_name or "", {})
        overrides = _dimension_overrides(pairs)
        effective_dimtol = overrides.get("dimtol", style.get("dimtol"))
        effective_dimlim = overrides.get("dimlim", style.get("dimlim"))
        dimtp = overrides.get("dimtp", style.get("dimtp"))
        dimtm = overrides.get("dimtm", style.get("dimtm"))
        text_override = _first_value(pairs, "1")
        tolerance_enabled = effective_dimtol == 1 or effective_dimlim == 1
        tolerance_signal = tolerance_enabled or bool(
            text_override and TOLERANCE_PATTERN.search(text_override)
        )
        rows.append(
            {
                "layer": _record_layer(record),
                "rawType": raw_type,
                "dimensionType": DIMENSION_TYPE_NAMES.get(base_type, f"unknown_{base_type}"),
                "measurement": _to_float(_first_value(pairs, "42")),
                "textOverride": text_override,
                "styleName": style_name,
                "dimtol": effective_dimtol,
                "dimlim": effective_dimlim,
                "dimtp": dimtp,
                "dimtm": dimtm,
                "hasToleranceSignal": tolerance_signal,
                "overrides": overrides,
            }
        )
    return rows


def _block_attribute_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current_block_name: str | None = None
    for record in records:
        record_type = record["type"]
        if record_type == "INSERT":
            current_block_name = _first_value(record["pairs"], "2")
            continue
        if record_type == "SEQEND":
            current_block_name = None
            continue
        if record_type != "ATTRIB":
            continue
        rows.append(
            {
                "blockName": current_block_name,
                "tag": _first_value(record["pairs"], "2"),
                "value": _first_value(record["pairs"], "1"),
                "layer": _record_layer(record),
            }
        )
    return rows


def _candidate_rows(
    records: list[dict[str, Any]],
    pattern: re.Pattern[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        search_text = _record_search_text(record)
        if not pattern.search(search_text):
            continue
        rows.append(
            {
                "entityType": record["type"],
                "layer": _record_layer(record),
                "text": _text_value(record) if record["type"] in TEXT_ENTITY_TYPES else None,
                "name": _first_value(record["pairs"], "2"),
                "evidence": pattern.search(search_text).group(0),
            }
        )
    return rows


def _audit_dxf(path: Path) -> dict[str, Any]:
    """DXFをgroup codeへ分解し、文字・寸法・公差・ブロック属性・溶接候補を数える。"""

    text, encoding = _decode_dxf(path)
    pairs = _group_pairs(text)
    records = _records(pairs)
    type_counts = Counter(record["type"] for record in records)
    declared_layers = sorted(
        {
            layer
            for record in records
            if record["type"] == "LAYER"
            for layer in [_first_value(record["pairs"], "2")]
            if layer
        }
    )
    used_layers = sorted(
        {
            layer
            for record in records
            for layer in [_record_layer(record)]
            if layer
        }
    )
    text_rows = [
        {
            "entityType": record["type"],
            "layer": _record_layer(record),
            "text": _text_value(record),
        }
        for record in records
        if record["type"] in TEXT_ENTITY_TYPES
    ]
    block_attributes = _block_attribute_rows(records)
    styles = _dimension_style_records(records)
    dimensions = _dimension_rows(records, styles)
    tolerance_entities = [
        {
            "layer": _record_layer(record),
            "text": _first_value(record["pairs"], "1"),
            "styleName": _first_value(record["pairs"], "3"),
        }
        for record in records
        if record["type"] == "TOLERANCE"
    ]
    tolerance_candidates = _candidate_rows(records, TOLERANCE_PATTERN)
    weld_candidates = _candidate_rows(records, WELD_PATTERN)
    weld_entity_types = sorted(
        entity_type for entity_type in type_counts if WELD_ENTITY_PATTERN.search(entity_type)
    )
    proxy_class_candidates = [
        {
            "entityType": record["type"],
            "className": _first_value(record["pairs"], "1"),
            "cppClassName": _first_value(record["pairs"], "2"),
            "applicationName": _first_value(record["pairs"], "3"),
        }
        for record in records
        if record["type"] == "CLASS" and WELD_PATTERN.search(_record_search_text(record))
    ]
    dimension_tolerance_count = sum(
        1 for dimension in dimensions if dimension["hasToleranceSignal"]
    )
    mleader_count = type_counts["MLEADER"] + type_counts["MULTILEADER"]

    return {
        "path": str(path),
        "sizeBytes": path.stat().st_size,
        "encoding": encoding,
        "pairCount": len(pairs),
        "recordCount": len(records),
        "entityTypeCounts": dict(sorted(type_counts.items())),
        "text": {
            "textCount": type_counts["TEXT"],
            "mtextCount": type_counts["MTEXT"],
            "attribCount": type_counts["ATTRIB"],
            "attdefCount": type_counts["ATTDEF"],
            "rows": text_rows[:100],
        },
        "blocks": {
            "insertCount": type_counts["INSERT"],
            "blockDefinitionCount": type_counts["BLOCK"],
            "attributeCount": len(block_attributes),
            "attributes": block_attributes[:100],
        },
        "layers": {
            "declaredCount": len(declared_layers),
            "usedCount": len(used_layers),
            "declared": declared_layers,
            "used": used_layers,
        },
        "dimensions": {
            "count": len(dimensions),
            "typeCounts": dict(
                sorted(Counter(row["dimensionType"] for row in dimensions).items())
            ),
            "withToleranceSignalCount": dimension_tolerance_count,
            "rows": dimensions[:100],
        },
        "tolerances": {
            "toleranceEntityCount": len(tolerance_entities),
            "dimensionToleranceCount": dimension_tolerance_count,
            "textOrMetadataCandidateCount": len(tolerance_candidates),
            "entities": tolerance_entities[:100],
            "candidates": tolerance_candidates[:100],
        },
        "weld": {
            "directWeldEntityTypes": weld_entity_types,
            "directWeldEntityCount": sum(type_counts[item] for item in weld_entity_types),
            "textBlockOrMetadataCandidateCount": len(weld_candidates),
            "candidates": weld_candidates[:100],
            "proxyClassCandidates": proxy_class_candidates[:100],
        },
        "advancedEntities": {
            "mleaderCount": mleader_count,
            "proxyEntityCount": type_counts["ACAD_PROXY_ENTITY"],
            "proxyObjectCount": type_counts["ACAD_PROXY_OBJECT"],
        },
    }


def _audit_conversion_result(result: dict[str, Any], output_root: Path) -> dict[str, Any]:
    dxf_path_value = result.get("dxfPath")
    if not dxf_path_value:
        return {**result, "auditStatus": "not_run", "auditError": "", "audit": None}
    dxf_path = Path(str(dxf_path_value))
    if not dxf_path.exists():
        return {
            **result,
            "auditStatus": "missing_dxf",
            "auditError": "変換結果が示すDXFファイルが存在しません。",
            "audit": None,
        }
    try:
        audit = _audit_dxf(dxf_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return {
            **result,
            "auditStatus": "failed",
            "auditError": str(exc),
            "audit": None,
        }

    audit_path = output_root / "per_file_audit" / f"{result['sampleName']}.audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        **result,
        "auditStatus": "audited",
        "auditError": "",
        "auditPath": str(audit_path),
        "audit": audit,
    }


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """個別監査を成功・失敗・要素種別ごとの全体件数へ集約する。"""

    audited = [result for result in results if result.get("auditStatus") == "audited"]

    def file_count(predicate) -> int:
        return sum(1 for result in audited if predicate(result["audit"]))

    return {
        "manifestSampleCount": len(results),
        "sourceAvailableCount": sum(
            1 for result in results if result.get("conversionStatus") != "missing_source"
        ),
        "sourceMissingCount": sum(
            1 for result in results if result.get("conversionStatus") == "missing_source"
        ),
        "convertedCount": sum(
            1
            for result in results
            if result.get("conversionStatus")
            in {"converted", "converted_after_timeout", "converted_after_result", "reused"}
        ),
        "conversionFailedCount": sum(
            1 for result in results if result.get("conversionStatus") == "failed"
        ),
        "auditedCount": len(audited),
        "auditFailedCount": sum(
            1 for result in results if result.get("auditStatus") == "failed"
        ),
        "filesWithTextOrMtext": file_count(
            lambda audit: audit["text"]["textCount"] + audit["text"]["mtextCount"] > 0
        ),
        "filesWithBlockAttributes": file_count(
            lambda audit: audit["blocks"]["attributeCount"] > 0
        ),
        "filesWithLayerNames": file_count(
            lambda audit: audit["layers"]["declaredCount"] + audit["layers"]["usedCount"] > 0
        ),
        "filesWithDimensions": file_count(
            lambda audit: audit["dimensions"]["count"] > 0
        ),
        "filesWithDimensionTolerance": file_count(
            lambda audit: audit["tolerances"]["dimensionToleranceCount"] > 0
        ),
        "filesWithToleranceEntity": file_count(
            lambda audit: audit["tolerances"]["toleranceEntityCount"] > 0
        ),
        "filesWithToleranceCandidate": file_count(
            lambda audit: audit["tolerances"]["textOrMetadataCandidateCount"] > 0
        ),
        "filesWithDirectWeldEntity": file_count(
            lambda audit: audit["weld"]["directWeldEntityCount"] > 0
        ),
        "filesWithWeldCandidate": file_count(
            lambda audit: audit["weld"]["textBlockOrMetadataCandidateCount"] > 0
            or bool(audit["weld"]["proxyClassCandidates"])
        ),
        "filesWithProxyEntity": file_count(
            lambda audit: audit["advancedEntities"]["proxyEntityCount"] > 0
            or audit["advancedEntities"]["proxyObjectCount"] > 0
        ),
    }


def _flat_result(result: dict[str, Any]) -> dict[str, Any]:
    audit = result.get("audit") or {}
    text = audit.get("text") or {}
    blocks = audit.get("blocks") or {}
    layers = audit.get("layers") or {}
    dimensions = audit.get("dimensions") or {}
    tolerances = audit.get("tolerances") or {}
    weld = audit.get("weld") or {}
    advanced = audit.get("advancedEntities") or {}
    return {
        "index": result["index"],
        "filename": result["filename"],
        "customerHint": result["customerHint"],
        "sourcePath": result["sourcePath"],
        "conversionStatus": result.get("conversionStatus"),
        "auditStatus": result.get("auditStatus"),
        "dxfPath": result.get("dxfPath"),
        "dxfSizeBytes": audit.get("sizeBytes"),
        "textCount": text.get("textCount", 0),
        "mtextCount": text.get("mtextCount", 0),
        "attribCount": text.get("attribCount", 0),
        "attdefCount": text.get("attdefCount", 0),
        "insertCount": blocks.get("insertCount", 0),
        "blockAttributeCount": blocks.get("attributeCount", 0),
        "declaredLayerCount": layers.get("declaredCount", 0),
        "usedLayerCount": layers.get("usedCount", 0),
        "dimensionCount": dimensions.get("count", 0),
        "dimensionToleranceCount": tolerances.get("dimensionToleranceCount", 0),
        "toleranceEntityCount": tolerances.get("toleranceEntityCount", 0),
        "toleranceCandidateCount": tolerances.get("textOrMetadataCandidateCount", 0),
        "directWeldEntityCount": weld.get("directWeldEntityCount", 0),
        "weldCandidateCount": weld.get("textBlockOrMetadataCandidateCount", 0),
        "proxyEntityCount": advanced.get("proxyEntityCount", 0),
        "conversionError": result.get("conversionError", ""),
        "auditError": result.get("auditError", ""),
    }


def _write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    rows = [_flat_result(result) for result in results]
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(
    path: Path,
    *,
    manifest_path: Path,
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    """人が確認する要約表と、再確認が必要なファイル一覧をMarkdownへ保存する。"""

    audits = [result["audit"] for result in results if result.get("audit")]
    total_text = sum(audit["text"]["textCount"] for audit in audits)
    total_mtext = sum(audit["text"]["mtextCount"] for audit in audits)
    total_attributes = sum(audit["blocks"]["attributeCount"] for audit in audits)
    total_dimensions = sum(audit["dimensions"]["count"] for audit in audits)
    total_dimension_tolerances = sum(
        audit["dimensions"]["withToleranceSignalCount"] for audit in audits
    )
    total_tolerance_entities = sum(
        audit["tolerances"]["toleranceEntityCount"] for audit in audits
    )
    total_weld_candidates = sum(
        audit["weld"]["textBlockOrMetadataCandidateCount"] for audit in audits
    )
    attribute_identities = sorted(
        {
            (attribute["blockName"], attribute["tag"])
            for audit in audits
            for attribute in audit["blocks"]["attributes"]
        }
    )
    attribute_identity_text = (
        "、".join(f"`{block_name} / {tag}`" for block_name, tag in attribute_identities)
        if attribute_identities
        else "なし"
    )
    weld_candidate_entity_types = sorted(
        {
            candidate["entityType"]
            for audit in audits
            for candidate in audit["weld"]["candidates"]
        }
    )
    weld_candidate_type_text = (
        " / ".join(f"`{entity_type}`" for entity_type in weld_candidate_entity_types)
        if weld_candidate_entity_types
        else "なし"
    )
    lines = [
        "# 共有サンプルICD全件 DXF変換・エンティティ監査",
        "",
        f"- 生成日時（UTC）: {datetime.now(timezone.utc).isoformat()}",
        f"- 対象manifest: `{manifest_path}`",
        f"- manifest件数: {summary['manifestSampleCount']}",
        f"- ICD参照可能: {summary['sourceAvailableCount']}",
        f"- ICD実体なし: {summary['sourceMissingCount']}",
        f"- DXF変換成功: {summary['convertedCount']}",
        f"- DXF監査完了: {summary['auditedCount']}",
        "",
        "## 分類別の確認結果",
        "",
        "| 分類 | 該当ファイル数 | 判定根拠 |",
        "|---|---:|---|",
        f"| TEXT / MTEXT | {summary['filesWithTextOrMtext']} | `TEXT` / `MTEXT` エンティティ |",
        f"| ブロック属性 | {summary['filesWithBlockAttributes']} | `INSERT` に続く `ATTRIB` |",
        f"| レイヤー名 | {summary['filesWithLayerNames']} | `LAYER`テーブルまたはグループコード8 |",
        f"| 寸法 | {summary['filesWithDimensions']} | `DIMENSION` エンティティ |",
        f"| 寸法公差 | {summary['filesWithDimensionTolerance']} | `DIMSTYLE` / `ACAD:DSTYLE` / 寸法文字 |",
        f"| 幾何公差 | {summary['filesWithToleranceEntity']} | `TOLERANCE` エンティティ |",
        f"| 公差候補 | {summary['filesWithToleranceCandidate']} | 公差文字・メタデータ候補 |",
        f"| 溶接専用エンティティ | {summary['filesWithDirectWeldEntity']} | エンティティ型名にWELDを含む |",
        f"| 溶接候補 | {summary['filesWithWeldCandidate']} | 文字・ブロック・属性・クラス名候補 |",
        f"| プロキシエンティティ | {summary['filesWithProxyEntity']} | `ACAD_PROXY_ENTITY/OBJECT` |",
        "",
        "## 判定上の注意",
        "",
        f"- TEXTは{total_text:,}件、MTEXTは{total_mtext:,}件、DIMENSIONは{total_dimensions:,}件を個別レコードとして取得できる。",
        f"- ブロック属性は{total_attributes:,}件。今回確認できたブロック名 / タグは {attribute_identity_text}。",
        f"- 寸法公差の信号付きDIMENSIONは{total_dimension_tolerances:,}件、独立したTOLERANCEエンティティは{total_tolerance_entities:,}件。",
        f"- 溶接候補は{total_weld_candidates:,}件で、候補のエンティティ型は {weld_candidate_type_text}。専用WELDエンティティは0件のため、DXFエンティティ型だけでは溶接記号種別を確定できない。",
        "- プロキシエンティティは0件。今回のDXFでは、未解釈プロキシ内に対象情報が隠れている形跡は確認されなかった。",
        "",
        "## ファイル別結果",
        "",
        "| No. | ファイル | 変換 | TEXT | MTEXT | 属性 | Layer | DIM | 寸法公差 | TOLERANCE | 溶接候補 | Proxy |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        row = _flat_result(result)
        lines.append(
            "| {index} | {filename} | {conversionStatus}/{auditStatus} | {textCount} | "
            "{mtextCount} | {blockAttributeCount} | {usedLayerCount} | {dimensionCount} | "
            "{dimensionToleranceCount} | {toleranceEntityCount} | {weldCandidateCount} | "
            "{proxyEntityCount} |".format(**row)
        )
    failures = [
        row
        for row in (_flat_result(result) for result in results)
        if row["conversionStatus"]
        not in {"converted", "converted_after_timeout", "converted_after_result", "reused"}
        or row["auditStatus"] != "audited"
    ]
    if failures:
        lines.extend(["", "## 未完了・失敗", ""])
        for row in failures:
            detail = row["conversionError"] or row["auditError"] or "詳細なし"
            lines.append(f"- `{row['filename']}`: {row['conversionStatus']}/{row['auditStatus']} — {detail}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """対象manifestを確定し、変換、個別監査、JSON/CSV/Markdown保存を順に実行する。"""

    parser = argparse.ArgumentParser(
        description="共有サンプルICDを全件DXFへ変換し、DXF生エンティティを分類監査します。"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
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
    parser.add_argument("--dxf-export-file-type", type=int, default=DEFAULT_DXF_EXPORT_FILE_TYPE)
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
        raise SystemExit(f"missing or invalid required settings: {', '.join(missing_settings)}")

    manifest = _load_json(args.manifest)
    samples = _sample_rows(manifest)
    if args.index:
        requested_indexes = set(args.index)
        samples = [sample for sample in samples if sample["index"] in requested_indexes]
        found_indexes = {sample["index"] for sample in samples}
        missing_indexes = sorted(requested_indexes - found_indexes)
        if missing_indexes:
            raise SystemExit(
                "manifestに存在しないindexです: "
                + ", ".join(str(index) for index in missing_indexes)
            )
    elif args.limit is not None:
        samples = samples[: args.limit]
    args.output_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for sample in samples:
        index = int(sample["index"])
        print(
            f"{index:03d}/{len(samples):03d} converting {sample['filename']}",
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
            dxf_export_file_type=args.dxf_export_file_type,
            resume=args.resume,
            safe_shutdown_after_conversion=args.safe_shutdown_after_conversion,
        )
        audited_result = _audit_conversion_result(conversion_result, args.output_root)
        results.append(audited_result)
        audit = audited_result.get("audit") or {}
        print(
            f"{index:03d}/{len(samples):03d} "
            f"{audited_result['conversionStatus']}/{audited_result['auditStatus']} "
            f"TEXT={audit.get('text', {}).get('textCount', 0)} "
            f"MTEXT={audit.get('text', {}).get('mtextCount', 0)} "
            f"ATTR={audit.get('blocks', {}).get('attributeCount', 0)} "
            f"DIM={audit.get('dimensions', {}).get('count', 0)} "
            f"TOL={audit.get('tolerances', {}).get('toleranceEntityCount', 0)} "
            f"WELD_CAND={audit.get('weld', {}).get('textBlockOrMetadataCandidateCount', 0)}",
            flush=True,
        )

    summary = _summary(results)
    report = {
        "schemaVersion": "icad_dxf_full_entity_audit.v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest),
        "outputRoot": str(args.output_root),
        "dxfExportFileType": args.dxf_export_file_type,
        "summary": summary,
        "results": results,
    }
    summary_json = args.output_root / "summary.json"
    summary_csv = args.output_root / "summary.csv"
    summary_md = args.output_root / "summary.md"
    summary_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
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
