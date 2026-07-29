"""初心者向けコメントが自作ソース全体へ行き渡っているかを監査する。

この監査は、単にコメント記号が存在するかではなく、次の二点を確認する。

1. ファイル冒頭に、そのファイルの責務を説明する日本語コメントがあること。
2. 行数が多いファイルには、処理途中にも判断理由や処理段階を説明する
   日本語コメントが一定数あること。

自動生成物、外部依存、空の ``__init__.py``、Django migration は対象外とする。
これらへ手作業のコメントを加えると、再生成時の差分や保守対象を増やすためである。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


SOURCE_EXTENSIONS = {".cs", ".js", ".ps1", ".py", ".ts", ".tsx"}
INCLUDED_PREFIXES = (
    "backend/",
    "handoff/claude_cloud/tools/",
    "integrations/2D_3D_CAD_VIEWR/backend/",
    "integrations/2D_3D_CAD_VIEWR/frontend/src/",
    "integrations/2D_3D_CAD_VIEWR/scripts/",
    "scripts/",
    "skills_to_install/",
    "src/",
    "tests/",
)
EXCLUDED_PATH_PARTS = {
    ".venv",
    "dist",
    "handover_package",
    "migrations",
    "node_modules",
    "obj",
}
EXCLUDED_FILENAMES = {
    "AssemblyInfo.cs",
    "assets.d.ts",
    "vite-env.d.ts",
}
JAPANESE_PATTERN = re.compile(r"[ぁ-んァ-ヶ一-龠]")


@dataclass(frozen=True)
class CommentAuditResult:
    """1ファイル分の監査結果を、後続の一覧表示とJSON保存で共用する。"""

    path: str
    line_count: int
    japanese_comment_lines: int
    required_comment_lines: int
    has_japanese_header: bool
    issues: tuple[str, ...]


def _tracked_files(repo_root: Path) -> list[Path]:
    """Git管理下のファイルだけを対象にし、成果物や一時ファイルの混入を防ぐ。"""

    completed = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    paths: list[Path] = []
    for raw_path in completed.stdout.splitlines():
        normalized = raw_path.replace("\\", "/")
        if not normalized.startswith(INCLUDED_PREFIXES):
            continue
        path = Path(normalized)
        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        if any(part in EXCLUDED_PATH_PARTS for part in path.parts):
            continue
        if path.name in EXCLUDED_FILENAMES or path.name.endswith(".d.ts"):
            continue
        # TypeScriptと同時管理されているJavaScriptはビルド生成物なので、正本のTSだけを監査する。
        if path.suffix == ".js" and (repo_root / path.with_suffix(".ts")).exists():
            continue
        absolute_path = repo_root / path
        if path.name == "__init__.py" and (
            not absolute_path.exists() or not absolute_path.read_text(encoding="utf-8").strip()
        ):
            continue
        paths.append(path)
    return sorted(paths)


def _comment_lines(lines: list[str], extension: str) -> list[tuple[int, str]]:
    """言語ごとのコメント構文を認識し、日本語を含むコメント行だけを返す。"""

    results: list[tuple[int, str]] = []
    in_block_comment = False
    in_python_docstring = False
    python_delimiter = ""

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        is_comment = False

        if extension == ".py":
            if in_python_docstring:
                is_comment = True
                if python_delimiter in stripped and stripped.count(python_delimiter) % 2 == 1:
                    in_python_docstring = False
            elif stripped.startswith("#"):
                is_comment = True
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                is_comment = True
                python_delimiter = stripped[:3]
                if stripped.count(python_delimiter) % 2 == 1:
                    in_python_docstring = True
        elif extension == ".ps1":
            if in_block_comment:
                is_comment = True
                if "#>" in stripped:
                    in_block_comment = False
            elif stripped.startswith("<#"):
                is_comment = True
                in_block_comment = "#>" not in stripped
            elif stripped.startswith("#"):
                is_comment = True
        else:
            if in_block_comment:
                is_comment = True
                if "*/" in stripped:
                    in_block_comment = False
            elif stripped.startswith("/*"):
                is_comment = True
                in_block_comment = "*/" not in stripped
            elif stripped.startswith("//"):
                is_comment = True

        if is_comment and JAPANESE_PATTERN.search(stripped):
            results.append((line_number, stripped))

    return results


def _required_comment_lines(line_count: int) -> int:
    """大きいファイルほど、冒頭説明だけで済ませないための最低行数を決める。"""

    if line_count >= 1_000:
        return 8
    if line_count >= 500:
        return 5
    if line_count >= 200:
        return 3
    return 1


def audit_file(repo_root: Path, relative_path: Path) -> CommentAuditResult:
    """ファイル冒頭と全体のコメント量を検査し、不足理由を明示する。"""

    absolute_path = repo_root / relative_path
    lines = absolute_path.read_text(encoding="utf-8").splitlines()
    comments = _comment_lines(lines, relative_path.suffix.lower())
    first_code_area_end = min(len(lines), 20)
    has_header = any(line_number <= first_code_area_end for line_number, _ in comments)
    required_count = _required_comment_lines(len(lines))
    issues: list[str] = []

    if not has_header:
        issues.append("冒頭20行以内に日本語の責務説明がない")
    if len(comments) < required_count:
        issues.append(
            f"日本語コメントが{len(comments)}行のみ"
            f"（{len(lines)}行のファイルには最低{required_count}行必要）"
        )

    return CommentAuditResult(
        path=relative_path.as_posix(),
        line_count=len(lines),
        japanese_comment_lines=len(comments),
        required_comment_lines=required_count,
        has_japanese_header=has_header,
        issues=tuple(issues),
    )


def main() -> int:
    """全対象を監査し、人が直すべきファイルを行数の大きい順に表示する。"""

    parser = argparse.ArgumentParser(description="初心者向け日本語ソースコメントの網羅性を監査します。")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="knowledge_systemリポジトリのルート",
    )
    parser.add_argument("--json-output", type=Path, help="監査結果をJSONでも保存する")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    results = [audit_file(repo_root, path) for path in _tracked_files(repo_root)]
    failures = sorted(
        (result for result in results if result.issues),
        key=lambda result: (-result.line_count, result.path),
    )

    if args.json_output:
        output_path = args.json_output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"対象ファイル数: {len(results)}")
    print(f"合格: {len(results) - len(failures)}")
    print(f"要補強: {len(failures)}")
    for result in failures:
        print(
            f"- {result.path} ({result.line_count}行): "
            + " / ".join(result.issues)
        )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
