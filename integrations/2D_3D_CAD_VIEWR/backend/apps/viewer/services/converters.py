from __future__ import annotations

"""3D conversion backends used by the viewer.

The rest of the app talks only to the abstract backend so STEP conversion can
be swapped later without changing API or page code.
"""

from pathlib import Path
from typing import Protocol

from django.conf import settings

from apps.viewer.domain.types import ConversionResult, StoredArtifact
from apps.viewer.services.errors import ConversionError


class ThreeDConversionBackend(Protocol):
    """Minimal interface for "source file -> display artifact" conversion."""

    def convert(self, source_path: Path, source_extension: str, output_artifact: StoredArtifact) -> ConversionResult: ...


class CadQueryOcctBackend(ThreeDConversionBackend):
    def convert(self, source_path: Path, source_extension: str, output_artifact: StoredArtifact) -> ConversionResult:
        if not settings.VIEWER_STEP_ENABLED:
            raise ConversionError("STEP conversion is disabled")

        try:
            import cadquery as cq
        except Exception as exc:  # pragma: no cover - environment dependent
            raise ConversionError("CadQuery is not installed. Install requirements-step.txt.") from exc

        if source_extension != "step":
            raise ConversionError(f"Unsupported 3D extension: {source_extension}")

        try:
            # STEP は複数 shape を含み得るので、Assembly にまとめてから STL を出力する。
            imported = cq.importers.importStep(str(source_path))
            assembly = cq.Assembly()
            shapes = list(getattr(imported, "objects", []) or [imported.val()])
            for shape in shapes:
                assembly.add(shape)
            assembly.export(
                str(output_artifact.absolute_path),
                exportType="STL",
                tolerance=settings.VIEWER_STEP_STL_TOLERANCE,
                angularTolerance=settings.VIEWER_STEP_STL_ANGULAR_TOLERANCE,
            )
        except Exception as exc:  # pragma: no cover - depends on external library/runtime
            raise ConversionError(f"STEP conversion failed: {exc}") from exc

        return ConversionResult(model_format="stl", artifact=output_artifact)
