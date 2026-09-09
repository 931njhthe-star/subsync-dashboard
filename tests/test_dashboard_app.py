from __future__ import annotations

from datetime import date
import subprocess
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


DASHBOARD_APP = Path(__file__).parents[1] / "dashboard" / "app.py"


def test_dashboard_demo_mode_renders_without_streamlit_exception(monkeypatch) -> None:
    # 개발자의 실제 .env가 live 모드여도 테스트는 샘플 fixture로 고정한다.
    monkeypatch.setenv("SUBSYNC_DASHBOARD_SOURCE", "demo")
    app = AppTest.from_file(str(DASHBOARD_APP)).run(timeout=30)

    assert not app.exception
    assert app.sidebar.radio[0].value == "Dashboard"
    assert len(app.sidebar.selectbox) == 0
    assert any("학습 흐름을 한눈에" in item.value for item in app.markdown)
    assert app.sidebar.radio[0].options == [
        "대시보드",
        "AI 사용량",
        "API 호출",
    ]
    assert len(app.button) == 0
    assert any("최근 AI 활동" in item.value for item in app.markdown)


def test_dashboard_supabase_shaped_payload_renders_without_exception(monkeypatch) -> None:
    rows_by_table = {
        "users": [
            {
                "id": "user-1",
                "email": "admin@example.test",
                "created_at": "2026-09-08T00:00:00Z",
                "last_login_at": "2026-09-08T00:01:00Z",
            }
        ],
        "login_history": [],
        "saved_words": [],
        "ai_conversations": [],
        "llm_usage": [
            {
                "id": "usage-1",
                "user_id": "user-1",
                "provider": "gemini",
                "model_name": "gemini-3.6-flash",
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "provider_latency": 120,
                "finish_reason": "stop",
                "used_at": "2026-09-08T00:03:00Z",
            }
        ],
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

    api_payloads = {
        "overview": {
            "tracked_user_count": 1,
            "ai_call_count": 1,
        "api_request_count": 1,
        "total_tokens": 150,
        "api_success_rate": 1.0,
        "average_response_time_ms": 120.0,
        "registered_user_count": 1,
        "daily_ai_usage": [],
            "recent_activity": [],
            "recent_ai_activity": [],
            "users": rows_by_table["users"],
        },
        "usage": {
            "summary": {
                "request_count": 1,
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "average_tokens_per_request": 150.0,
                "error_count": 0,
                "error_rate": 0.0,
                "average_latency_ms": 120.0,
                "p95_latency_ms": 120.0,
            },
            "providers": [],
            "daily_usage": [],
            "details": rows_by_table["llm_usage"],
        },
        "api-calls": {
            "summary": {
                "request_count": 1,
                "success_count": 1,
                "failure_count": 0,
                "success_rate": 1.0,
                "average_response_time_ms": 120.0,
                "p95_response_time_ms": 120,
            },
            "endpoints": [],
            "recent_calls": rows_by_table["api_logs"],
            "all_calls": rows_by_table["api_logs"],
            "status_codes": [],
        },
    }

    class FakeResponse:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    api_calls = []

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, *, params):
            api_calls.append((url, dict(params)))
            endpoint = url.rsplit("/", 1)[-1]
            return FakeResponse(api_payloads[endpoint])

    import httpx

    monkeypatch.setenv("SUBSYNC_DASHBOARD_SOURCE", "dashboard_api")
    monkeypatch.setenv("DASHBOARD_API_URL", "http://example.test")
    monkeypatch.setattr(httpx, "Client", FakeClient)

    app = AppTest.from_file(str(DASHBOARD_APP)).run(timeout=30)

    assert not app.exception
    assert len(app.sidebar.selectbox) == 0
    assert len(app.sidebar.date_input) == 1
    assert not any("수파베이스" in item.value for item in app.markdown)

    app.sidebar.radio[0].set_value("AI Usage").run(timeout=30)
    assert not app.exception
    assert app.selectbox[0].options == ["전체 모델", "Gemini 3.6 Flash"]
    assert app.selectbox[1].options == ["전체 사용자", "admin@example.test"]
    assert "항목" in app.dataframe[0].value.columns
    assert any(item.label == "평균 응답시간" for item in app.metric)
    assert not any("LLM 운영 요약" in item.value for item in app.markdown)
    assert not any("현재 연결된 요약 모델" in item.value for item in app.markdown)
    assert not any("요약 생성" in item.value for item in app.markdown)

    app.sidebar.date_input[0].set_value(
        (date(2026, 9, 7), date(2026, 9, 8))
    ).run(timeout=30)
    assert any(
        params.get("from_date") == "2026-09-07"
        and params.get("to_date") == "2026-09-08"
        for _, params in api_calls
    )

    app.sidebar.radio[0].set_value("API Calls").run(timeout=30)
    assert not app.exception
    assert app.selectbox[0].options == [
        "전체 엔드포인트",
        "POST /api/v1/tutor/ask",
    ]
    assert "엔드포인트" in app.dataframe[0].value.columns
    assert app.dataframe[1].value.columns[0] == "상태 코드"
    assert "상태 코드" in app.dataframe[1].value.columns
    assert any(item.label == "성공률" for item in app.metric)

    app.sidebar.radio[0].set_value("Dashboard").run(timeout=30)
    assert not app.exception
    assert len(app.sidebar.date_input) == 1
    app.sidebar.radio[0].set_value("AI Usage").run(timeout=30)
    assert not app.exception
    assert app.sidebar.date_input[0].value == (date(2026, 9, 7), date(2026, 9, 8))


def test_dashboard_script_imports_when_launched_from_project_root() -> None:
    """루트에서 Streamlit이 dashboard 폴더만 sys.path에 넣어도 실행된다."""

    backend_root = DASHBOARD_APP.parents[1]
    script = f"""
from pathlib import Path
import runpy
import sys
import os

backend_root = Path({str(backend_root)!r}).resolve()
sys.path[:] = [
    entry for entry in sys.path
    if not entry or Path(entry).resolve() != backend_root
]
sys.path.insert(0, str(Path({str(DASHBOARD_APP.parent)!r}).resolve()))
os.environ["SUBSYNC_DASHBOARD_SOURCE"] = "demo"
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
