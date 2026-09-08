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


def test_dashboard_supabase_shaped_payload_renders_without_exception(monkeypatch) -> None:
    rows_by_table = {
        "users": [
            {
                "id": "user-1",
                "created_at": "2026-09-08T00:00:00Z",
                "last_login_at": "2026-09-08T00:01:00Z",
            }
        ],
        "login_history": [],
        "saved_words": [],
        "ai_conversations": [],
        "llm_usage": [],
        "api_logs": [
            {
                "id": "api-1",
                "api_name": "POST /api/v1/tutor/ask",
                "user_id": "user-1",
                "requested_at": "2026-09-08T00:02:00Z",
                "response_time_ms": 120,
                "status_code": 200,
                "success": True,
                "error_message": None,
            }
        ],
    }

    class FakeResponse:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, *, params, headers):
            table = url.rsplit("/", 1)[-1]
            offset = int(params["offset"])
            limit = int(params["limit"])
            return FakeResponse(rows_by_table[table][offset : offset + limit])

    import httpx

    monkeypatch.setenv("SUBSYNC_DASHBOARD_SOURCE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "mock-key")
    monkeypatch.setattr(httpx, "Client", FakeClient)

    app = AppTest.from_file(str(DASHBOARD_APP)).run(timeout=30)

    assert not app.exception
    assert app.sidebar.selectbox[0].value == "supabase"
    assert any("수파베이스" in item.value for item in app.markdown)


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
