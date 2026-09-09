from __future__ import annotations

from datetime import date

import httpx

from dashboard.dashboard_api import load_dashboard_api_snapshot


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_dashboard_api_snapshot_preserves_existing_data_contract(monkeypatch):
    payloads = {
        "overview": {
            "tracked_user_count": 1,
            "registered_user_count": 1,
            "ai_call_count": 1,
            "api_request_count": 1,
            "total_tokens": 120,
            "api_success_rate": 1.0,
            "average_response_time_ms": 80.0,
            "daily_ai_usage": [],
            "recent_activity": [],
            "recent_ai_activity": [],
            "users": [
                {
                    "id": "user-1",
                    "email": "admin@example.test",
                    "created_at": "2026-09-08T00:00:00Z",
                }
            ],
        },
        "usage": {
            "summary": {
                "request_count": 1,
                "input_tokens": 80,
                "output_tokens": 40,
                "total_tokens": 120,
                "average_tokens_per_request": 120.0,
                "error_count": 0,
                "error_rate": 0.0,
                "average_latency_ms": 80.0,
                "p95_latency_ms": 80.0,
            },
            "providers": [],
            "daily_usage": [],
            "details": [
                {
                    "id": "usage-1",
                    "user_id": "user-1",
                    "provider": "gemini",
                    "model_name": "gemini-3.6-flash",
                    "input_tokens": 80,
                    "output_tokens": 40,
                    "total_tokens": 120,
                    "used_at": "2026-09-08T00:01:00Z",
                    "finish_reason": "stop",
                    "provider_latency": 80,
                }
            ],
        },
        "api-calls": {
            "summary": {
                "request_count": 1,
                "success_count": 1,
                "failure_count": 0,
                "success_rate": 1.0,
                "average_response_time_ms": 80.0,
                "p95_response_time_ms": 80,
            },
            "endpoints": [],
            "recent_calls": [],
            "all_calls": [
                {
                    "id": "api-1",
                    "api_name": "POST /api/v1/tutor/ask",
                    "user_id": "user-1",
                    "requested_at": "2026-09-08T00:01:00Z",
                    "response_time_ms": 80,
                    "status_code": 200,
                    "success": True,
                }
            ],
            "status_codes": [],
        },
    }
    calls = []

    class _FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, *, params):
            calls.append((url, dict(params)))
            endpoint = url.rsplit("/", 1)[-1]
            return _FakeResponse(payloads[endpoint])

    monkeypatch.setattr(httpx, "Client", _FakeClient)

    snapshot = load_dashboard_api_snapshot(
        date(2026, 9, 7),
        date(2026, 9, 8),
        api_base_url="http://example.test/",
    )

    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == [
        "overview",
        "usage",
        "api-calls",
    ]
    assert all(
        params["from_date"] == "2026-09-07"
        and params["to_date"] == "2026-09-08"
        for _, params in calls
    )
    assert calls[-1][1]["recent_limit"] == "100"
    assert len(snapshot.data.users) == 1
    assert len(snapshot.data.llm_usage) == 1
    assert len(snapshot.data.api_logs) == 1
    assert snapshot.metrics["total_users"] == 1
    assert snapshot.metrics["api_request_count"] == 1
