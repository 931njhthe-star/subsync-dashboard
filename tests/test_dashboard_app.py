from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


DASHBOARD_APP = Path(__file__).parents[1] / "dashboard" / "app.py"


def test_dashboard_demo_mode_renders_without_streamlit_exception() -> None:
    app = AppTest.from_file(str(DASHBOARD_APP)).run(timeout=30)

    assert not app.exception
    assert app.sidebar.radio[0].value == "Overview"
    assert app.sidebar.selectbox[0].value == "demo"
    assert any("학습 흐름을 한눈에" in item.value for item in app.markdown)
    assert app.sidebar.radio[0].options == ["개요", "학습 활동", "튜터 품질", "시스템 로그"]
    assert app.sidebar.selectbox[0].options == ["샘플 데이터", "자동 선택", "자료 파일", "수파베이스"]


def test_dashboard_script_imports_when_launched_from_project_root() -> None:
    """루트에서 Streamlit이 dashboard 폴더만 sys.path에 넣어도 실행된다."""

    backend_root = DASHBOARD_APP.parents[1]
    script = f"""
from pathlib import Path
import runpy
import sys

backend_root = Path({str(backend_root)!r}).resolve()
sys.path[:] = [
    entry for entry in sys.path
    if not entry or Path(entry).resolve() != backend_root
]
sys.path.insert(0, str(Path({str(DASHBOARD_APP.parent)!r}).resolve()))
runpy.run_path({str(DASHBOARD_APP)!r}, run_name="__main__")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_root.parent,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
