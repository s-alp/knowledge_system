import pytest


@pytest.fixture(autouse=True)
def disable_default_handoff_manifest(settings):
    settings.DRAWING_METADATA_HANDOFF_MANIFEST = ""


@pytest.fixture
def sample_registration_payload():
    return {
        "hostDrawingId": "sample-drawing-id",
        "filename": "sample_3d.icd",
        "sourcePath": r"C:\temp\sample_3d.icd",
        "sourceFormat": "icad",
    }
