from __future__ import annotations

from pathlib import Path


CAD_SOURCE_FORMAT_BY_SUFFIX = {
    ".icd": "icad",
    ".step": "step",
    ".stp": "step",
    ".dxf": "dxf",
}
SXNET_SOURCE_FORMATS = {"icad"}
GENERIC_CAD_SOURCE_FORMATS = {"step", "dxf"}
SOURCE_FORMAT_DEFAULT_MODE = {
    "step": "3d",
    "dxf": "2d",
}


def source_format_from_path(path: str | Path) -> str | None:
    return CAD_SOURCE_FORMAT_BY_SUFFIX.get(Path(path).suffix.lower())


def is_supported_cad_source(path: str | Path) -> bool:
    return source_format_from_path(path) is not None


def uses_sxnet_extractor(source_format: str | None) -> bool:
    return (source_format or "").lower() in SXNET_SOURCE_FORMATS


def uses_generic_cad_extractor(source_format: str | None) -> bool:
    return (source_format or "").lower() in GENERIC_CAD_SOURCE_FORMATS


def default_extraction_modes_for_source_format(source_format: str | None) -> tuple[str, ...]:
    normalized = (source_format or "").lower()
    if normalized == "icad":
        return ("2d", "3d")
    mode = SOURCE_FORMAT_DEFAULT_MODE.get(normalized)
    return (mode,) if mode else ()
