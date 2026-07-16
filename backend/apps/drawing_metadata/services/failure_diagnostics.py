from __future__ import annotations

from apps.drawing_metadata.models import DrawingMetadataExtractionJob, RegisteredDrawing
from apps.drawing_metadata.services.path_constraints import (
    WINDOWS_FILENAME_LIMIT,
    WINDOWS_LEGACY_PATH_LIMIT,
    icad_source_path_exists,
    requires_sxnet_staged_input,
)


def classify_extraction_failure(status: str, message: str) -> str:
    if status == DrawingMetadataExtractionJob.STATUS_SUCCEEDED:
        return "none"
    if not message:
        return "missing_error_message"
    normalized = message.lower()
    if "パスが長すぎます" in message:
        return "path_length_limit"
    if "ファイル名が長すぎます" in message:
        return "filename_length_limit"
    if "図面ファイルではありません" in message or "not drawing file" in normalized:
        return "sxnet_rejected_as_not_drawing_file"
    if "見つかりません" in message or "not found" in normalized:
        return "source_file_not_found"
    if "timed out" in normalized or "timeout" in normalized:
        return "extractor_timeout"
    if "sxnet" in normalized or "sxexception" in normalized:
        return "sxnet_open_failure"
    return "other"


def build_source_preflight(drawing: RegisteredDrawing) -> dict:
    path_text = drawing.source_path or ""
    filename = drawing.filename or ""
    extension = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    return {
        "filename": filename,
        "sourcePath": path_text,
        "sourcePathLength": len(path_text),
        "sourcePathWithinSxnetLegacyLimit": len(path_text) <= WINDOWS_LEGACY_PATH_LIMIT,
        "requiresSxnetStagedInput": requires_sxnet_staged_input(path_text),
        "filenameLength": len(filename),
        "filenameWithinWindowsLimit": len(filename) <= WINDOWS_FILENAME_LIMIT,
        "extension": extension.lower(),
        "extensionIsIcd": extension.lower() == ".icd",
        "sourceExistsFromCurrentMachine": icad_source_path_exists(path_text),
    }


def build_reextract_condition(*, error_class: str, preflight: dict) -> str:
    if error_class == "none":
        return "再抽出は不要です。"
    if error_class == "missing_error_message":
        return "失敗理由が記録されていません。workerログとICAD起動状態を確認してから再抽出します。"
    if error_class == "filename_length_limit":
        return "ファイル名自体が長すぎます。短いICADファイル名で再登録してから再抽出します。"
    if error_class == "path_length_limit":
        return "現行抽出では短い一時パスへ退避して再抽出します。退避後も失敗する場合はICAD対応版や外部参照を確認します。"
    if error_class == "sxnet_rejected_as_not_drawing_file":
        if preflight.get("requiresSxnetStagedInput"):
            return "長い原本パスは短い一時パスへ退避済み/退避対象です。退避後も同じ場合は、ICAD対応版、ファイル破損、拡張子だけICDのデータ、外部参照不足を確認して再抽出します。"
        return "ICD拡張子ですがSXNETが図面モデルとして開けていません。ICAD対応版、ファイル破損、外部参照不足、2D/3Dデータ有無を確認して再抽出します。"
    if error_class == "extractor_timeout":
        return "ICAD起動待ちまたは抽出時間が不足しています。ICAD起動状態とタイムアウト秒数を確認して再抽出します。"
    if error_class == "source_file_not_found":
        return "元ICADファイルにアクセスできません。保存パスとネットワークドライブ接続を確認して再抽出します。"
    if error_class == "sxnet_open_failure":
        return "SXNETでICADファイルを開けていません。ICAD起動状態、対象ファイル、起動済みダイアログ、対応版を確認して再抽出します。"
    if not preflight.get("sourceExistsFromCurrentMachine"):
        return "現在の実行環境から原本ICADへアクセスできません。ネットワークドライブ/共有パス接続を確認して再抽出します。"
    return "失敗理由を確認し、対象ファイル・ICAD起動状態・抽出条件を修正して再抽出します。"


def build_job_failure_diagnostics(job: DrawingMetadataExtractionJob) -> dict:
    preflight = build_source_preflight(job.drawing)
    error_class = classify_extraction_failure(job.status, job.error_message or "")
    return {
        "errorClass": error_class,
        "sourcePreflight": preflight,
        "reextractCondition": build_reextract_condition(error_class=error_class, preflight=preflight),
    }
