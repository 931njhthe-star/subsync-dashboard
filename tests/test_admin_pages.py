from __future__ import annotations

from dashboard.analytics.data_loader import dashboard_data_from_payload
from dashboard.components.admin_pages import (
    _api_health,
    _latency_precise_text,
    _usage_detail_frame,
)


def _dashboard_data():
    return dashboard_data_from_payload(
        {
            "users": [
                {
                    "id": "user-1",
                    "email": "admin@example.test",
                    "created_at": "2026-09-08T00:00:00Z",
                    "last_login_at": "2026-09-08T00:00:00Z",
                }
            ],
            "llm_usage": [
                {
                    "id": "usage-1",
                    "user_id": "user-1",
                    "model_name": "gemini-flash",
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "provider_latency": 40,
                    "finish_reason": "stop",
                    "used_at": "2026-09-08T00:01:00Z",
                }
            ],
            "api_logs": [
                {
                    "id": "api-1",
                    "api_name": "POST /api/tutor",
                    "requested_at": "2026-09-08T00:01:00Z",
                    "response_time_ms": 40,
                    "status_code": 200,
                    "success": True,
                },
                {
                    "id": "api-2",
                    "api_name": "POST /api/tutor",
                    "requested_at": "2026-09-08T00:02:00Z",
                    "response_time_ms": 80,
                    "status_code": 503,
                    "success": False,
                },
            ],
        },
        source="supabase",
    )


def test_api_health_returns_reason_for_warning() -> None:
    health = _api_health(_dashboard_data())

    assert health["status"] == "주의"
    assert health["request_count"] == 2
    assert health["failure_count"] == 1
    assert health["error_rate"] == 50.0
    assert health["latest_failure_api"] == "POST /api/tutor"
    assert health["latest_failure_status"] == "HTTP 503"


def test_usage_detail_keeps_tokens_latency_and_success_columns() -> None:
    data = _dashboard_data()
    detail = _usage_detail_frame(data.llm_usage, data)

    assert list(detail.columns) == [
        "사용자",
        "모델",
        "입력 토큰",
        "출력 토큰",
        "총 토큰",
        "응답 시간",
        "성공 여부",
        "일시",
    ]
    assert detail.loc[0, "사용자"] == "admin@example.test"
    assert detail.loc[0, "응답 시간"] == "0.04s"
    assert detail.loc[0, "성공 여부"] == "성공"


def test_precise_latency_does_not_round_subsecond_values_to_zero() -> None:
    assert _latency_precise_text(40) == "0.04s"
    assert _latency_precise_text(1_250) == "1.25s"
