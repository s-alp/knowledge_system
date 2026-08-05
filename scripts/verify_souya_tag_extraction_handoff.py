"""創屋向け最小パッケージの最終成果物を、変更を加えず一括検証する。

実行目的:
- 展開済みフォルダー、manifest、ZIPの内容が同一であることを確認する。
- ZIPを一時領域へ展開し、Python 3.11/3.12で配布専用テストを実行する。
- Docker Compose、外部共有監査、PDF本文の機械確認を同じ手順で再現する。

安全性:
- 配布フォルダーへpipのbuild/egg-info等を生成しない。
- ZIPの展開先は自動作成する一時領域に限定し、処理終了時に破棄する。
- Pythonパッケージのバージョンは、未定義の場合がある__version__ではなく、
  pyproject.tomlとimportlib.metadataで照合する。

PDFの画像化と全ページ目視は、人の判断が必要なため本スクリプトの対象外とする。
"""

from __future__ import annotations

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
import os
import shutil
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = ROOT / "scripts"
REQUIRED_PYTHON_MINORS = {"3.11", "3.12"}
FORBIDDEN_FILE_SUFFIXES = {".pyc", ".pyo", ".pptx"}
FORBIDDEN_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    "bin",
    "build",
    "obj",
    "TestResults",
}

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from audit_souya_handoff_content import assert_external_handoff_safe  # noqa: E402
from build_souya_tag_extraction_package import validate_package  # noqa: E402


def _file_sha256(path: Path) -> str:
    """大きいファイルもメモリへ全量展開せずSHA-256を計算する。"""

    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """検証コマンドを実行し、失敗時はコマンドと終了コードを明示する。"""

    process_env = env.copy() if env is not None else os.environ.copy()
    process_env["PYTHONUTF8"] = "1"
    print(f"実行: {subprocess.list2cmdline(command)}")
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=process_env,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"検証コマンドが失敗しました。exit={completed.returncode}: "
            f"{subprocess.list2cmdline(command)}"
        )
    return completed


def _package_file_map(package_dir: Path) -> dict[str, Path]:
    """パッケージ内の全ファイルをPOSIX相対パスで返す。"""

    return {
        path.relative_to(package_dir).as_posix(): path
        for path in package_dir.rglob("*")
        if path.is_file()
    }


def verify_archive_matches_directory(package_dir: Path, archive_path: Path) -> int:
    """ZIPと展開済みパッケージのファイル集合・内容が完全一致することを確認する。"""

    package_files = _package_file_map(package_dir)
    package_prefix = f"{package_dir.name}/"
    with ZipFile(archive_path) as archive:
        archive_files: dict[str, str] = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            member = PurePosixPath(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise ValueError(f"ZIPに不正なパスがあります: {info.filename}")
            if not info.filename.startswith(package_prefix):
                raise ValueError(
                    "ZIPの最上位フォルダーがパッケージ名と一致しません: "
                    f"{info.filename}"
                )
            relative = info.filename[len(package_prefix) :]
            archive_files[relative] = sha256(archive.read(info)).hexdigest()

    if set(archive_files) != set(package_files):
        missing = sorted(set(package_files) - set(archive_files))
        unexpected = sorted(set(archive_files) - set(package_files))
        raise ValueError(
            f"ZIPとフォルダーのファイル集合が一致しません。"
            f"missing={missing}, unexpected={unexpected}"
        )
    for relative, path in package_files.items():
        if archive_files[relative] != _file_sha256(path):
            raise ValueError(f"ZIPとフォルダーの内容が一致しません: {relative}")
    return len(package_files)


def verify_no_generated_artifacts(package_dir: Path) -> None:
    """キャッシュ、ビルド生成物、配布対象外PPTXの混入を拒否する。"""

    violations: list[str] = []
    for path in package_dir.rglob("*"):
        relative = path.relative_to(package_dir)
        if any(part in FORBIDDEN_PATH_PARTS for part in relative.parts):
            violations.append(relative.as_posix())
            continue
        if any(part.endswith(".egg-info") for part in relative.parts):
            violations.append(relative.as_posix())
            continue
        if path.is_file() and path.suffix.lower() in FORBIDDEN_FILE_SUFFIXES:
            violations.append(relative.as_posix())
    if violations:
        raise ValueError(
            "配布対象外の生成物を検出しました:\n- " + "\n- ".join(sorted(violations))
        )


def _safe_extract(archive_path: Path, destination: Path) -> Path:
    """パストラバーサルを拒否してZIPを一時領域へ展開する。"""

    resolved_destination = destination.resolve()
    with ZipFile(archive_path) as archive:
        for info in archive.infolist():
            target = (resolved_destination / PurePosixPath(info.filename)).resolve()
            if not target.is_relative_to(resolved_destination):
                raise ValueError(f"ZIPに展開先外のパスがあります: {info.filename}")
        archive.extractall(resolved_destination)
    return resolved_destination


def _declared_package_version(package_dir: Path) -> str:
    """配布pyproject.tomlから正本のパッケージバージョンを取得する。"""

    pyproject_path = package_dir / "python" / "pyproject.toml"
    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = payload.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"pyproject.tomlにversionがありません: {pyproject_path}")
    return version


def _python_minor(interpreter: Path) -> str:
    """指定Pythonのmajor.minorを取得し、実行できない場合は中断する。"""

    completed = subprocess.run(
        [
            str(interpreter),
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Pythonを実行できません: {interpreter}")
    return completed.stdout.strip()


def verify_python_runtime(
    interpreter: Path,
    package_dir: Path,
    work_dir: Path,
    expected_version: str,
) -> str:
    """一時領域へインストールし、バージョン照合と配布専用テストを実行する。"""

    minor = _python_minor(interpreter)
    install_dir = work_dir / f"python-{minor}" / "installed"
    pytest_temp = work_dir / f"python-{minor}" / "pytest"
    install_dir.mkdir(parents=True)

    _run(
        [
            str(interpreter),
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(install_dir),
            str(package_dir / "python"),
        ],
        cwd=work_dir,
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(install_dir)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    _run(
        [
            str(interpreter),
            "-c",
            (
                "from importlib.metadata import version; "
                f"actual=version('icad-tag-extraction'); "
                f"expected={expected_version!r}; "
                "assert actual == expected, (actual, expected); "
                "print(f'packageVersion={actual}')"
            ),
        ],
        cwd=work_dir,
        env=env,
    )
    _run(
        [
            str(interpreter),
            "-m",
            "pytest",
            str(package_dir / "tests" / "python"),
            "--basetemp",
            str(pytest_temp),
        ],
        cwd=work_dir,
        env=env,
    )
    return minor


def verify_pdf(pdf_path: Path) -> int:
    """PDFの本文、空白、メタデータ、章しおりを機械確認する。"""

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF確認にはpypdfが必要です。文書用Pythonで実行してください。"
        ) from exc

    reader = PdfReader(pdf_path)
    if not reader.pages:
        raise ValueError(f"PDFにページがありません: {pdf_path}")
    metadata = reader.metadata
    if metadata is None or metadata.title != "CADタグ・属性抽出 利用・組み込みガイド":
        raise ValueError(f"PDFのタイトルメタデータが不正です: {getattr(metadata, 'title', None)!r}")
    if metadata.author != "株式会社アルパイン設計事務所":
        raise ValueError(f"PDFの作成者メタデータが不正です: {metadata.author!r}")
    if not reader.outline:
        raise ValueError("PDFに章しおりがありません。見出しから移動できる状態にしてください。")
    blank_pages: list[int] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            blank_pages.append(page_number)
        if "初心者" in text:
            raise ValueError(f"PDFに禁止表現があります: page={page_number}")
    if blank_pages:
        raise ValueError(f"PDFに空白ページがあります: {blank_pages}")
    return len(reader.pages)


def verify_handoff(
    package_dir: Path,
    archive_path: Path,
    pdf_path: Path,
    python_interpreters: tuple[Path, ...],
    *,
    docker_command: str = "docker",
) -> dict[str, object]:
    """最終成果物を一括検証し、後続記録に使える実測値を返す。"""

    package_dir = package_dir.resolve()
    archive_path = archive_path.resolve()
    pdf_path = pdf_path.resolve()
    if not package_dir.is_dir():
        raise FileNotFoundError(f"パッケージがありません: {package_dir}")
    if not archive_path.is_file():
        raise FileNotFoundError(f"ZIPがありません: {archive_path}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDFがありません: {pdf_path}")
    for interpreter in python_interpreters:
        if not interpreter.is_file():
            raise FileNotFoundError(f"Pythonがありません: {interpreter}")

    manifest = validate_package(package_dir)
    verify_no_generated_artifacts(package_dir)
    file_count = verify_archive_matches_directory(package_dir, archive_path)
    packaged_pdf = (
        package_dir / "docs" / "CADタグ属性抽出_創屋様向け利用ガイド.pdf"
    )
    if not packaged_pdf.is_file():
        raise FileNotFoundError(f"パッケージ内PDFがありません: {packaged_pdf}")
    if _file_sha256(packaged_pdf) != _file_sha256(pdf_path):
        raise ValueError("単体PDFとパッケージ内PDFが一致しません")
    assert_external_handoff_safe(package_dir, pdfs=(pdf_path,))
    pdf_pages = verify_pdf(pdf_path)
    expected_version = _declared_package_version(package_dir)

    temp_parent = ROOT / "tmp"
    temp_parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="souya_handoff_verify_", dir=temp_parent) as temp:
        temp_root = Path(temp)
        _safe_extract(archive_path, temp_root)
        extracted_package = temp_root / package_dir.name
        if not extracted_package.is_dir():
            raise FileNotFoundError(
                f"ZIP内にパッケージフォルダーがありません: {extracted_package}"
            )
        verify_no_generated_artifacts(extracted_package)
        runtime_minors = {
            verify_python_runtime(
                interpreter,
                extracted_package,
                temp_root,
                expected_version,
            )
            for interpreter in python_interpreters
        }
        if runtime_minors != REQUIRED_PYTHON_MINORS:
            raise ValueError(
                "Python正式対応範囲の確認が不足しています。"
                f"required={sorted(REQUIRED_PYTHON_MINORS)}, "
                f"actual={sorted(runtime_minors)}"
            )
        docker = shutil.which(docker_command)
        if docker is None:
            raise FileNotFoundError(f"Dockerコマンドがありません: {docker_command}")
        _run(
            [
                docker,
                "compose",
                "-f",
                str(extracted_package / "docker" / "docker-compose.yml"),
                "config",
                "--quiet",
            ],
            cwd=extracted_package,
        )

    return {
        "package": str(package_dir),
        "archive": str(archive_path),
        "pdf": str(pdf_path),
        "packageVersion": expected_version,
        "manifestFileCount": manifest["fileCount"],
        "zipFileCount": file_count,
        "pdfPages": pdf_pages,
        "pythonMinors": sorted(runtime_minors),
        "archiveSizeBytes": archive_path.stat().st_size,
        "archiveSha256": _file_sha256(archive_path),
        "pdfSizeBytes": pdf_path.stat().st_size,
        "pdfSha256": _file_sha256(pdf_path),
    }


def main() -> int:
    # PowerShellの出力設定に依存せず、日本語の診断結果をUTF-8で表示する。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument(
        "--python",
        action="append",
        type=Path,
        required=True,
        help="Python 3.11と3.12の実行ファイルを各1回指定する。",
    )
    parser.add_argument("--docker-command", default="docker")
    args = parser.parse_args()
    summary = verify_handoff(
        args.package,
        args.archive,
        args.pdf,
        tuple(args.python),
        docker_command=args.docker_command,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
