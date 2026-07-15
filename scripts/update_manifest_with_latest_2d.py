from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

from build_icad_extract_import_manifest import _candidate, _load_json


def _path_key(value: str) -> str:
    return str(PureWindowsPath(value)).casefold()


def update_manifest(manifest_path: Path, latest_2d_root: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates_by_source: dict[str, dict] = {}
    candidates_by_filename: dict[str, list[dict]] = {}

    for path in sorted(latest_2d_root.glob("*.latest_2d.json")):
        payload = _load_json(path)
        candidate = _candidate(path.resolve(), payload or {})
        if candidate is None or candidate["mode"] != "2d":
            continue
        candidates_by_source[_path_key(candidate["sourcePath"])] = candidate
        filename = PureWindowsPath(candidate["sourcePath"]).name.casefold()
        candidates_by_filename.setdefault(filename, []).append(candidate)

    missing: list[str] = []
    for entry in manifest.get("entries", []):
        source_path = str(entry["sourcePath"])
        candidate = candidates_by_source.get(_path_key(source_path))
        if candidate is None:
            filename_candidates = candidates_by_filename.get(PureWindowsPath(source_path).name.casefold(), [])
            if len(filename_candidates) == 1:
                candidate = filename_candidates[0]
        if candidate is None:
            missing.append(source_path)
            continue

        selected_files = [item for item in entry.get("selectedFiles", []) if item.get("mode") != "2d"]
        entry["selectedFiles"] = [candidate, *selected_files]
        entry["has2d"] = True
        entry["candidateFileCount"] = max(int(entry.get("candidateFileCount") or 0), len(entry["selectedFiles"]))

    if missing:
        raise ValueError(f"最新2D抽出が見つからないmanifest entryがあります: {missing}")

    selected_paths = [
        selected_file["path"]
        for entry in manifest.get("entries", [])
        for selected_file in entry.get("selectedFiles", [])
    ]
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    manifest["selectedFileCount"] = len(selected_paths)
    manifest["selectedPaths"] = selected_paths
    manifest["latest2DRoot"] = str(latest_2d_root)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="既存ICAD manifestの2D参照を最新全件抽出へ更新します。")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--latest-2d-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = update_manifest(args.manifest.resolve(), args.latest_2d_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output} drawings={manifest['selectedDrawingCount']} "
        f"files={manifest['selectedFileCount']} latest2d={len(manifest['entries'])}"
    )


if __name__ == "__main__":
    main()
