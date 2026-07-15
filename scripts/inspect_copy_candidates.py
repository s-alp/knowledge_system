from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


ESTIMATE_PATTERN = re.compile(
    r"見積|金額|原価|費用|工数|単価|価格|quotation|quote|cost",
    re.IGNORECASE,
)


@dataclass
class DirSummary:
    name: str
    file_count: int = 0
    size_bytes: int = 0


def is_estimate_candidate(path: Path) -> bool:
    return bool(ESTIMATE_PATTERN.search(str(path)))


def iter_files(root: Path) -> Iterable[Path]:
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            dirs: list[Path] = []
            for entry in current.iterdir():
                try:
                    if entry.is_dir():
                        dirs.append(entry)
                    elif entry.is_file():
                        yield entry
                except OSError:
                    continue
            stack.extend(reversed(dirs))
        except OSError:
            continue


def inspect_root(root: Path) -> dict:
    extension_breakdown: Counter[str] = Counter()
    top_level: dict[str, DirSummary] = {}
    estimate_candidates: list[str] = []

    total_files = 0
    total_size = 0
    icd_count = 0
    icd_size = 0
    estimate_count = 0
    estimate_size = 0
    copy_count = 0
    copy_size = 0

    for file_path in iter_files(root):
        try:
            stat = file_path.stat()
        except OSError:
            continue

        relative = file_path.relative_to(root)
        top_name = relative.parts[0] if len(relative.parts) > 1 else "[root files]"
        summary = top_level.setdefault(top_name, DirSummary(name=top_name))

        size = stat.st_size
        ext = file_path.suffix.lower() or "[no extension]"
        is_icd = ext == ".icd"
        is_estimate = is_estimate_candidate(file_path)

        total_files += 1
        total_size += size
        extension_breakdown[ext] += 1
        summary.file_count += 1
        summary.size_bytes += size

        if is_icd:
            icd_count += 1
            icd_size += size

        if is_estimate:
            estimate_count += 1
            estimate_size += size
            estimate_candidates.append(str(file_path))

        if not is_icd and not is_estimate:
            copy_count += 1
            copy_size += size

    return {
        "root": str(root),
        "total_files": total_files,
        "total_size_bytes": total_size,
        "icd_file_count": icd_count,
        "icd_size_bytes": icd_size,
        "estimate_candidate_count": estimate_count,
        "estimate_candidate_size_bytes": estimate_size,
        "copy_target_count": copy_count,
        "copy_target_size_bytes": copy_size,
        "extension_breakdown": [
            {"extension": ext, "count": count}
            for ext, count in extension_breakdown.most_common()
        ],
        "top_level_directories": [
            asdict(item)
            for item in sorted(
                top_level.values(),
                key=lambda value: (-value.file_count, value.name),
            )
        ],
        "estimate_candidates": sorted(estimate_candidates),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", help="Inspection target directories")
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for root in args.roots:
        result = inspect_root(Path(root))
        results.append(result)
        output_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"completed: {root}", flush=True)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
