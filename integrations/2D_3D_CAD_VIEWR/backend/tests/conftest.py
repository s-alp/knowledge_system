from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def configure_storage(settings, tmp_path: Path):
    settings.VIEWER_STORAGE_ROOT = tmp_path / "viewer-storage"
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.VIEWER_STEP_ENABLED = True
    settings.VIEWER_LOCAL_FILE_ENABLED = True
    return settings
