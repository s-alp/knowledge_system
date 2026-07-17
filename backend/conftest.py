from __future__ import annotations

from pathlib import Path

# pytest.ini の --basetemp=tmp/pytest_run は親ディレクトリが無いと
# 新規クローン環境で全テストが起動時エラーになるため、ここで必ず作成する。
Path(__file__).resolve().parent.joinpath("tmp", "pytest_run").mkdir(parents=True, exist_ok=True)
