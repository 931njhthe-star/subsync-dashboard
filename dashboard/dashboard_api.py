"""FastAPI Dashboard API client used by the three administrator screens.

The existing Streamlit components still consume ``DashboardData``.  This module
adapts the richer FastAPI responses to that shape so the current cards, charts,
filters, and detail tables can use the documented Dashboard API responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping

import httpx

from dashboard.analytics.data_loader import (
    DashboardData,
    dashboard_data_from_payload,
)


DEFAULT_DASHBOARD_API_URL = " https://subsync-backend-4bmh.onrender.com/"
DEFAULT_DASHBOARD_API_TIMEOUT_SECONDS = 8.0
MAX_API_CALL_ROWS = 50_000


class DashboardApiError(RuntimeError):
    """FastAPI Dashboard API를 읽지 못했을 때 사용하는 안전한 오류."""


@dataclass(frozen=True)
class DashboardApiSnapshot:
    """세 화면의 응답과 기존 Streamlit 데이터 모델을 함께 보관한다."""

    data: DashboardData
    overview: Mapping[str, Any]
    usage: Mapping[str, Any]
    api_calls: Mapping[str, Any]

    @property
    def metrics(self) -> dict[str, float | int | None]:
        """홈 KPI가 기존 컴포넌트에서 사용할 수 있는 값으로 변환한다."""

        usage_summary = _mapping(self.usage.get("summary"))
        api_summary = _mapping(self.api_calls.get("summary"))
        overview_users = _rows(self.overview.get("users"))
        registered_user_count = self.overview.get("registered_user_count")
        if registered_user_count is None:
            registered_user_count = (
                len(overview_users)
                or _int_or_zero(self.overview.get("tracked_user_count"))
            )
        return {
            "total_users": _int_or_zero(registered_user_count),
            "tutor_questions": _int_or_zero(self.overview.get("ai_call_count")),
            "error_rate": _percent_or_none(usage_summary.get("error_rate")),
            "avg_tutor_latency_ms": _number_or_none(
                usage_summary.get("average_latency_ms")
            ),
            "api_request_count": _int_or_zero(api_summary.get("request_count")),
            "api_success_rate": _percent_or_none(api_summary.get("success_rate")),
            "api_p95_latency_ms": _number_or_none(
                api_summary.get("p95_response_time_ms")
            ),
        }


def _mapping(value: Any) -> Mapping[str, Any]:
    """JSON 객체가 아닌 값은 빈 mapping으로 안전하게 바꾼다."""

    return value if isinstance(value, Mapping) else {}


def _rows(value: Any) -> list[Mapping[str, Any]]:
    """응답의 리스트 필드를 화면 adapter가 사용할 행 목록으로 변환한다."""

    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _int_or_zero(value: Any) -> int:
    """KPI에 사용할 정수 값을 안전하게 변환한다."""

    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _number_or_none(value: Any) -> float | None:
    """응답시간처럼 결측을 보존해야 하는 수치를 변환한다."""

    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _percent_or_none(value: Any) -> float | None:
    """FastAPI가 0~1로 반환하는 비율을 기존 화면의 퍼센트로 바꾼다."""

    number = _number_or_none(value)
    return None if number is None else number * 100


def _user_rows(overview: Mapping[str, Any], usage_rows: list[Mapping[str, Any]], api_rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """overview의 사용자 목록을 기존 users frame 형태로 변환한다."""

    rows = _rows(overview.get("users"))
    if rows:
        return [dict(row) for row in rows]

    # 구버전 API와 사용자 테이블 조회 실패에서도 기존 표가 비어 보이지 않도록
    # 상세 응답에 포함된 user_id/user_label을 최소 directory로 만든다.
    fallback: dict[str, dict[str, Any]] = {}
    for row in [*usage_rows, *api_rows]:
        user_id = row.get("user_id")
        if user_id is None or not str(user_id).strip():
            continue
        user_id_text = str(user_id)
        label = row.get("user_label")
        fallback.setdefault(
            user_id_text,
            {
                "id": user_id_text,
                "email": str(label) if label and "@" in str(label) else None,
                "created_at": None,
                "last_login_at": None,
            },
        )
    return list(fallback.values())


def _usage_rows(overview: Mapping[str, Any], usage: Mapping[str, Any]) -> list[dict[str, Any]]:
    """사용량 상세 행을 기존 llm_usage frame 형태로 변환한다."""

    rows = _rows(usage.get("details"))
    if not rows:
        # API가 아직 확장 응답을 배포하지 않은 경우의 호환 경로다.
        rows = _rows(overview.get("recent_ai_activity"))
    return [dict(row) for row in rows]


def _api_rows(api_calls: Mapping[str, Any]) -> list[dict[str, Any]]:
    """전체 API 호출 상세 행을 기존 api_logs frame 형태로 변환한다."""

    rows = _rows(api_calls.get("all_calls"))
    if not rows:
        rows = _rows(api_calls.get("recent_calls"))
    return [
        {
            "id": row.get("id"),
            "api_name": row.get("api_name"),
            "user_id": row.get("user_id"),
            "requested_at": row.get("requested_at"),
            "response_time_ms": row.get("response_time_ms"),
            "status_code": row.get("status_code"),
            "success": row.get("success"),
        }
        for row in rows
    ]


def _payload_to_data(
    overview: Mapping[str, Any],
    usage: Mapping[str, Any],
    api_calls: Mapping[str, Any],
) -> DashboardData:
    """세 API 응답을 기존 화면이 사용하는 DashboardData로 합친다."""

    usage_rows = _usage_rows(overview, usage)
    api_rows = _api_rows(api_calls)
    payload = {
        "users": _user_rows(overview, usage_rows, api_rows),
        "llm_usage": usage_rows,
        "api_logs": api_rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return dashboard_data_from_payload(payload, source="dashboard_api")


def _date_params(start_date: date, end_date: date) -> dict[str, str]:
    """FastAPI의 inclusive 날짜 필터를 구성한다."""

    if end_date < start_date:
        raise DashboardApiError("조회 종료일은 시작일보다 빠를 수 없습니다.")
    return {
        "from_date": start_date.isoformat(),
        "to_date": end_date.isoformat(),
    }


def _get_json(client: httpx.Client, url: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
    """Dashboard API JSON 응답을 읽고 사용자에게 안전한 오류만 반환한다."""

    try:
        response = client.get(url, params=params)
    except httpx.TimeoutException as exc:
        raise DashboardApiError("Dashboard API 응답 시간이 초과되었습니다.") from exc
    except httpx.HTTPError as exc:
        raise DashboardApiError("Dashboard API에 연결할 수 없습니다.") from exc

    if not 200 <= response.status_code < 300:
        raise DashboardApiError(
            f"Dashboard API 조회에 실패했습니다 (HTTP {response.status_code})."
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise DashboardApiError("Dashboard API 응답 형식이 올바르지 않습니다.") from exc
    if not isinstance(payload, Mapping):
        raise DashboardApiError("Dashboard API 응답 형식이 올바르지 않습니다.")
    return payload


def load_dashboard_api_snapshot(
    start_date: date,
    end_date: date,
    *,
    api_base_url: str | None = None,
    timeout_seconds: float = DEFAULT_DASHBOARD_API_TIMEOUT_SECONDS,
) -> DashboardApiSnapshot:
    """홈·AI 사용량·API 호출 API를 조회해 기존 화면용 snapshot을 만든다."""

    base_url = (api_base_url or DEFAULT_DASHBOARD_API_URL).strip().rstrip("/")
    if not base_url:
        raise DashboardApiError("DASHBOARD_API_URL이 비어 있습니다.")
    try:
        timeout = max(float(timeout_seconds), 0.1)
    except (TypeError, ValueError):
        timeout = DEFAULT_DASHBOARD_API_TIMEOUT_SECONDS

    date_params = _date_params(start_date, end_date)
    with httpx.Client(timeout=timeout) as client:
        overview = _get_json(
            client,
            f"{base_url}/api/v1/dashboard/overview",
            {**date_params, "recent_limit": "10"},
        )
        usage = _get_json(
            client,
            f"{base_url}/api/v1/dashboard/usage",
            date_params,
        )
        api_calls = _get_json(
            client,
            f"{base_url}/api/v1/dashboard/api-calls",
            {**date_params, "recent_limit": str(MAX_API_CALL_ROWS)},
        )

    data = _payload_to_data(overview, usage, api_calls)
    return DashboardApiSnapshot(
        data=data,
        overview=overview,
        usage=usage,
        api_calls=api_calls,
    )


__all__ = [
    "DashboardApiError",
    "DashboardApiSnapshot",
    "DEFAULT_DASHBOARD_API_TIMEOUT_SECONDS",
    "DEFAULT_DASHBOARD_API_URL",
    "MAX_API_CALL_ROWS",
    "load_dashboard_api_snapshot",
]
