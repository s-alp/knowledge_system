import pytest


@pytest.fixture
def sample_registration_payload():
    return {
        "hostDrawingId": "sample-drawing-id",
        "filename": "sample_3d.icd",
        "sourcePath": r"C:\temp\sample_3d.icd",
        "sourceFormat": "icad",
    }
