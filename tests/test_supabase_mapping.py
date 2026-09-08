from __future__ import annotations

import pytest
import pandas as pd

from dashboard.analytics.ai_quality_eval import provider_summary
from dashboard.analytics.data_loader import (
    DashboardDataSourceError,
    SUPABASE_SELECT_COLUMNS,
    SUPABASE_TABLES,
    dashboard_data_from_payload,
    load_supabase_data,
    summarize_metrics,
)
from dashboard.analytics.user_patterns import daily_activity


ACTUAL_SUPABASE_PAYLOAD = {
    "users": [
        {
            "id": "user-1",
            "google_account_id": "google-1",
            "email": "learner@example.test",
            "created_at": "2026-09-01T00:00:00Z",
            "last_login_at": "2026-09-08T00:00:00Z",
        }
    ],
    "login_history": [
        {
            "id": "login-1",
            "user_id": "user-1",
            "login_at": "2026-09-08T00:00:00Z",
            "logout_at": None,
            "last_access_at": "2026-09-08T00:10:00Z",
        }
    ],
    "saved_words": [
        {
            "id": "word-1",
            "user_id": "user-1",
            "word": "orbit",
            "saved_at": "2026-09-08T00:05:00Z",
        }
    ],
    "ai_conversations": [
        {
            "id": "conversation-1",
            "user_id": "user-1",
            "video_id": "video-1",
            "question": "What does orbit mean?",
            "answer": "It means to move around something.",
            "started_at": "2026-09-08T00:06:00Z",
            "feedback": {"rating": "up", "reason": "Clear explanation"},
        }
    ],
    "llm_usage": [
        {
            "id": "usage-1",
            "provider": "gemini",
            "model_name": "gemini-3.6-flash",
            "input_tokens": 100,
            "output_tokens": 40,
            "total_tokens": 140,
            "used_at": "2026-09-08T00:06:01Z",
        }
    ],
    "api_logs": [
        {
            "id": "api-1",
            "api_name": "POST /api/v1/tutor/ask",
            "user_id": "user-1",
            "requested_at": "2026-09-08T00:06:00Z",
            "response_time_ms": 240,
            "status_code": 200,
            "success": True,
            "error_message": None,
        },
        {
            "id": "api-2",
            "api_name": "GET /api/v1/dict/hover",
            "user_id": "user-1",
            "requested_at": "2026-09-08T00:07:00Z",
            "response_time_ms": 40,
            "status_code": 500,
            "success": False,
            "error_message": "dictionary unavailable",
        },
        {
            "id": "api-3",
            "api_name": "POST /api/v1/tutor/proactive",
            "user_id": "user-1",
            "requested_at": "2026-09-08T00:08:00Z",
            "response_time_ms": 30,
            "status_code": 200,
            "success": False,
            "error_message": "provider unavailable",
        },
    ],
}


def test_actual_supabase_schema_maps_to_dashboard_contract() -> None:
    data = dashboard_data_from_payload(ACTUAL_SUPABASE_PAYLOAD, source="supabase")

    assert bool(data.users.loc[0, "is_active"]) is True
    assert data.saved_words.loc[0, "created_at"] == pd.Timestamp("2026-09-08 00:05:00+0000")
    assert list(data.tutor_messages["sender"]) == ["user", "tutor"]
    assert data.tutor_messages.loc[0, "message"] == "What does orbit mean?"
    assert data.user_feedback.loc[0, "rating"] == "up"
    assert data.system_logs.loc[0, "event_type"] == "POST /api/v1/tutor/ask"
    assert data.system_logs.loc[0, "latency_ms"] == 240
    assert data.llm_usage.loc[0, "provider"] == "gemini"
    assert len(data.api_logs) == 3
    assert len(data.login_history) == 1


def test_actual_operational_tables_drive_metrics_and_quality_views() -> None:
    data = dashboard_data_from_payload(ACTUAL_SUPABASE_PAYLOAD, source="supabase")

    metrics = summarize_metrics(data)
    assert metrics["total_users"] == 1
    assert metrics["active_users"] == 1
    assert metrics["saved_words"] == 1
    assert metrics["tutor_questions"] == 1
    assert metrics["avg_tutor_latency_ms"] == 240.0
    assert metrics["error_rate"] == 66.7

    activity = daily_activity(data)
    assert activity.loc[0, "tutor_questions"] == 1

    providers = provider_summary(data)
    assert providers.loc[0, "provider"] == "gemini"
    assert providers.loc[0, "requests"] == 1
    assert pd.isna(providers.loc[0, "avg_latency_ms"])


def test_supabase_loader_requests_the_real_table_names(monkeypatch) -> None:
    requested_tables: list[str] = []

    class FakeResponse:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

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
            requested_tables.append(table)
            return FakeResponse(ACTUAL_SUPABASE_PAYLOAD.get(table, []))

    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    data = load_supabase_data("https://example.supabase.co", "test-key")

    assert requested_tables == list(SUPABASE_TABLES)
    assert set(requested_tables) == {
        "users",
        "login_history",
        "saved_words",
        "ai_conversations",
        "llm_usage",
        "api_logs",
    }
    assert data.source == "supabase"
    assert bool(data.users.loc[0, "is_active"]) is True


def test_login_history_is_authoritative_for_active_users() -> None:
    payload = dict(ACTUAL_SUPABASE_PAYLOAD)
    payload["users"] = [
        {**ACTUAL_SUPABASE_PAYLOAD["users"][0], "last_login_at": None}
    ]
    data = dashboard_data_from_payload(payload, source="supabase")

    assert bool(data.users.loc[0, "is_active"]) is False
    assert summarize_metrics(data)["active_users"] == 1


def test_empty_operational_tables_still_normalize_without_error() -> None:
    data = dashboard_data_from_payload(
        {
            "users": [],
            "login_history": [],
            "saved_words": [],
            "ai_conversations": [],
            "llm_usage": [],
            "api_logs": [],
        },
        source="supabase",
    )

    assert data.users.empty
    assert data.saved_words.empty
    assert data.system_logs.empty
    assert summarize_metrics(data)["watch_hours"] is None


def test_supabase_loader_uses_explicit_columns_and_paginates(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, str], dict[str, str]]] = []
    rows_by_table = {
        table: [{"id": f"{table}-{index}"} for index in range(3)]
        for table in SUPABASE_TABLES
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
            calls.append((table, params, headers))
            offset = int(params["offset"])
            limit = int(params["limit"])
            rows = rows_by_table[table]
            return FakeResponse(rows[offset : offset + limit])

    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    data = load_supabase_data("https://example.supabase.co", "test-key", limit=2)

    assert len(data.api_logs) == 3
    assert [call[1]["offset"] for call in calls if call[0] == "api_logs"] == ["0", "2"]
    for table, params, headers in calls:
        assert params["select"] == ",".join(SUPABASE_SELECT_COLUMNS[table])
        assert params["order"] == "id.asc"
        assert params["limit"] == "2"
        assert headers["apikey"] == "test-key"
        assert headers["Authorization"] == "Bearer test-key"


def test_supabase_loader_uses_apikey_only_for_new_secret_key(monkeypatch) -> None:
    captured_headers: list[dict[str, str]] = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return []

    class FakeClient:
        def __init__(self, *, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, *, params, headers):
            captured_headers.append(headers)
            return FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    load_supabase_data("https://example.supabase.co", "sb_secret_test-key")

    assert captured_headers
    assert all(headers == {"apikey": "sb_secret_test-key", "Accept": "application/json"}
               for headers in captured_headers)


@pytest.mark.parametrize("status_code", [401, 403, 500])
def test_supabase_loader_reports_http_failures_without_response_body(
    monkeypatch, status_code: int
) -> None:
    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            return []

    class FakeClient:
        def __init__(self, *, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, *, params, headers):
            return FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    with pytest.raises(DashboardDataSourceError) as error:
        load_supabase_data("https://example.supabase.co", "test-key")

    message = str(error.value)
    assert str(status_code) in message
    assert "test-key" not in message


def test_supabase_loader_reports_missing_required_table(monkeypatch) -> None:
    class FakeResponse:
        status_code = 404

        def json(self):
            return []

    class FakeClient:
        def __init__(self, *, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, *, params, headers):
            return FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    with pytest.raises(DashboardDataSourceError, match="users.*404"):
        load_supabase_data("https://example.supabase.co", "test-key")


def test_supabase_loader_reports_timeout_without_secret(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, *, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, *, params, headers):
            raise __import__("httpx").TimeoutException("request timed out")

    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    with pytest.raises(DashboardDataSourceError) as error:
        load_supabase_data("https://example.supabase.co", "test-key")

    assert "test-key" not in str(error.value)
    assert "시간" in str(error.value) or "timeout" in str(error.value).lower()


def test_supabase_loader_rejects_malformed_json(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"unexpected": "object"}

    class FakeClient:
        def __init__(self, *, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, *, params, headers):
            return FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    with pytest.raises(DashboardDataSourceError, match="형식"):
        load_supabase_data("https://example.supabase.co", "test-key")
