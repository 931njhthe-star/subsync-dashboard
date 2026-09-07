"""대시보드 데이터 로딩·정규화 계층.

기본 실행은 안전한 로컬 demo fixture를 사용하며, Supabase 환경변수가 제공되면
동일한 표준 DataFrame 계약으로 PostgREST 데이터를 읽을 수 있도록 구성한다.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": ("id", "email", "created_at", "is_active", "level"),
    "video_history": (
        "id",
        "user_id",
        "video_id",
        "video_title",
        "last_timestamp",
        "watch_duration_sec",
        "created_at",
        "updated_at",
    ),
    "saved_words": (
        "id",
        "user_id",
        "word",
        "meaning",
        "video_id",
        "timestamp",
        "context_sentence",
        "created_at",
    ),
    "click_events": (
        "id",
        "user_id",
        "word",
        "video_id",
        "timestamp",
        "context_sentence",
        "created_at",
    ),
    "tutor_messages": (
        "id",
        "conversation_id",
        "user_id",
        "video_id",
        "sender",
        "message",
        "timestamp",
        "provider",
        "model",
        "latency_ms",
        "created_at",
    ),
    "user_feedback": (
        "id",
        "message_id",
        "user_id",
        "rating",
        "reason",
        "created_at",
    ),
    "system_logs": (
        "id",
        "event_type",
        "user_id",
        "video_id",
        "status_code",
        "latency_ms",
        "severity",
        "message",
        "created_at",
    ),
}

DATE_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": ("created_at",),
    "video_history": ("created_at", "updated_at"),
    "saved_words": ("created_at",),
    "click_events": ("created_at",),
    "tutor_messages": ("created_at",),
    "user_feedback": ("created_at",),
    "system_logs": ("created_at",),
}
NUMERIC_COLUMNS: dict[str, tuple[str, ...]] = {
    "video_history": ("last_timestamp", "watch_duration_sec"),
    "saved_words": ("timestamp",),
    "click_events": ("timestamp",),
    "tutor_messages": ("timestamp", "latency_ms"),
    "system_logs": ("status_code", "latency_ms"),
}
SUPABASE_TABLES = tuple(TABLE_COLUMNS)
DEFAULT_DEMO_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_data.json"


class DashboardDataSourceError(RuntimeError):
    """대시보드 데이터 원천을 읽을 수 없을 때 발생하는 예외."""


@dataclass(frozen=True)
class DashboardData:
    """대시보드가 사용하는 표준 DataFrame 묶음."""

    frames: dict[str, pd.DataFrame]
    source: str
    generated_at: str | None = None

    def frame(self, name: str) -> pd.DataFrame:
        """이름으로 정규화된 데이터 프레임을 반환한다."""

        return self.frames[name]

    @property
    def users(self) -> pd.DataFrame:
        return self.frames["users"]

    @property
    def video_history(self) -> pd.DataFrame:
        return self.frames["video_history"]

    @property
    def saved_words(self) -> pd.DataFrame:
        return self.frames["saved_words"]

    @property
    def click_events(self) -> pd.DataFrame:
        return self.frames["click_events"]

    @property
    def tutor_messages(self) -> pd.DataFrame:
        return self.frames["tutor_messages"]

    @property
    def user_feedback(self) -> pd.DataFrame:
        return self.frames["user_feedback"]

    @property
    def system_logs(self) -> pd.DataFrame:
        return self.frames["system_logs"]


def _records(value: Any) -> Any:
    """테이블 payload의 흔한 응답 래퍼를 평탄화한다."""

    if isinstance(value, Mapping) and "items" in value:
        return value["items"]
    return value if value is not None else []


def _normalize_frame(table: str, records: Any) -> pd.DataFrame:
    """테이블별 컬럼·날짜·수치 타입을 표준화한다."""

    if isinstance(records, pd.DataFrame):
        frame = records.copy()
    else:
        frame = pd.DataFrame(_records(records))

    columns = TABLE_COLUMNS[table]
    frame = frame.reindex(columns=columns)

    for column in DATE_COLUMNS.get(table, ()):
        frame[column] = pd.to_datetime(frame[column], errors="coerce", utc=True)

    for column in NUMERIC_COLUMNS.get(table, ()):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

    if table == "users":
        frame["is_active"] = frame["is_active"].map(
            lambda value: value
            if isinstance(value, bool)
            else str(value).strip().lower() in {"1", "true", "yes", "y"}
        )

    return frame


def dashboard_data_from_payload(
    payload: Mapping[str, Any],
    *,
    source: str = "unknown",
) -> DashboardData:
    """여러 원천의 JSON payload를 표준 ``DashboardData``로 변환한다."""

    root = payload.get("data", payload) if isinstance(payload, Mapping) else {}
    frames = {
        table: _normalize_frame(table, root.get(table, []))
        for table in TABLE_COLUMNS
    }
    generated_at = root.get("generated_at") if isinstance(root, Mapping) else None
    return DashboardData(frames=frames, source=source, generated_at=generated_at)


def load_json(path: str | Path) -> DashboardData:
    """로컬 JSON fixture 또는 export 파일을 읽는다."""

    file_path = Path(path).expanduser()
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DashboardDataSourceError(f"데이터 파일을 찾을 수 없습니다: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise DashboardDataSourceError(f"JSON 형식이 올바르지 않습니다: {file_path}") from exc

    if not isinstance(payload, Mapping):
        raise DashboardDataSourceError("대시보드 JSON 최상위 값은 객체여야 합니다.")
    return dashboard_data_from_payload(payload, source=f"json:{file_path.name}")


def load_demo_data(path: str | Path | None = None) -> DashboardData:
    """검증 가능한 로컬 demo dataset을 읽는다."""

    return _with_source(load_json(path or DEFAULT_DEMO_PATH), "demo")


def _with_source(data: DashboardData, source: str) -> DashboardData:
    """불변 snapshot의 source label을 교체한다."""

    return DashboardData(frames=data.frames, source=source, generated_at=data.generated_at)


def load_supabase_data(
    url: str,
    key: str,
    *,
    limit: int = 5_000,
    timeout_seconds: float = 8.0,
) -> DashboardData:
    """서버 환경변수의 Supabase PostgREST endpoint에서 데이터를 읽는다.

    ``key``는 dashboard 서버 프로세스에서만 사용하며 코드·브라우저·화면에 노출하지
    않는다. 존재하지 않는 선택 테이블은 빈 프레임으로 처리해 부분 구축 단계에서도
    overview 화면을 열 수 있게 한다.
    """

    if not url or not key:
        raise DashboardDataSourceError("SUPABASE_URL과 SUPABASE_KEY가 필요합니다.")

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - pyproject가 보장하는 경로
        raise DashboardDataSourceError("Supabase 연결에 httpx가 필요합니다.") from exc

    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    base_url = url.rstrip("/")
    payload: dict[str, Any] = {}

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            for table in SUPABASE_TABLES:
                response = client.get(
                    f"{base_url}/rest/v1/{table}",
                    params={"select": "*", "limit": str(limit)},
                    headers=headers,
                )
                if response.status_code == 404:
                    payload[table] = []
                    continue
                response.raise_for_status()
                payload[table] = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise DashboardDataSourceError(f"Supabase 데이터를 읽지 못했습니다: {exc}") from exc

    return dashboard_data_from_payload(payload, source="supabase")


def load_dashboard_data(
    source: str | None = None,
    *,
    json_path: str | Path | None = None,
    supabase_url: str | None = None,
    supabase_key: str | None = None,
) -> DashboardData:
    """환경변수 또는 명시한 source에 따라 대시보드 데이터를 로드한다."""

    mode = (source or os.getenv("SUBSYNC_DASHBOARD_SOURCE", "demo")).strip().lower()
    if mode == "demo":
        return load_demo_data(json_path)
    if mode == "json":
        path = json_path or os.getenv("SUBSYNC_DASHBOARD_JSON")
        if not path:
            raise DashboardDataSourceError("JSON source에는 SUBSYNC_DASHBOARD_JSON이 필요합니다.")
        return load_json(path)
    if mode in {"supabase", "auto"}:
        url = supabase_url or os.getenv("SUPABASE_URL", "")
        key = supabase_key or os.getenv("SUPABASE_KEY", "")
        if mode == "auto" and not (url and key):
            return load_demo_data(json_path)
        return load_supabase_data(url, key)
    raise DashboardDataSourceError(f"지원하지 않는 dashboard source입니다: {mode}")


def _date_mask(frame: pd.DataFrame, column: str, start: date | datetime | None, end: date | datetime | None) -> pd.Series:
    """날짜 범위용 boolean mask를 만든다."""

    if frame.empty or column not in frame:
        return pd.Series(True, index=frame.index)
    # pandas 버전별 datetime 해상도 차이로 date 객체와 직접 비교하면
    # ``datetime64[s]``와 ``date`` 사이의 비교 오류가 발생할 수 있다.
    dates = frame[column].dt.strftime("%Y-%m-%d")
    mask = pd.Series(True, index=frame.index)
    if start is not None:
        start_key = (start.date() if isinstance(start, datetime) else start).isoformat()
        mask &= dates >= start_key
    if end is not None:
        end_key = (end.date() if isinstance(end, datetime) else end).isoformat()
        mask &= dates <= end_key
    return mask


def filter_by_date(
    data: DashboardData,
    start: date | datetime | None,
    end: date | datetime | None,
) -> DashboardData:
    """모든 이벤트 프레임을 날짜 범위로 잘라 새로운 snapshot을 반환한다."""

    date_columns = {
        "users": "created_at",
        "video_history": "updated_at",
        "saved_words": "created_at",
        "click_events": "created_at",
        "tutor_messages": "created_at",
        "user_feedback": "created_at",
        "system_logs": "created_at",
    }
    frames: dict[str, pd.DataFrame] = {}
    for table, frame in data.frames.items():
        active_column = date_columns[table]
        if table == "video_history" and frame[active_column].isna().all():
            active_column = "created_at"
        frames[table] = frame.loc[_date_mask(frame, active_column, start, end)].copy()
    return DashboardData(frames=frames, source=data.source, generated_at=data.generated_at)


def summarize_metrics(data: DashboardData) -> dict[str, float | int | None]:
    """대시보드 상단 KPI를 계산한다."""

    users = data.users
    total_users = int(len(users))
    active_users = int(users["is_active"].sum()) if "is_active" in users else 0
    watch_seconds = float(data.video_history["watch_duration_sec"].sum())
    feedback = data.user_feedback
    logs = data.system_logs
    tutor = data.tutor_messages

    if "sender" in tutor and not tutor.empty:
        tutor_questions = int(tutor["sender"].astype(str).str.lower().eq("user").sum())
    else:
        tutor_questions = int(len(tutor))

    helpful_rate: float | None = None
    if not feedback.empty and "rating" in feedback:
        ratings = feedback["rating"].astype(str).str.lower()
        helpful_rate = round(float(ratings.eq("up").mean() * 100), 1)

    error_rate: float | None = None
    if not logs.empty and "status_code" in logs:
        statuses = pd.to_numeric(logs["status_code"], errors="coerce")
        error_rate = round(float(statuses.ge(400).mean() * 100), 1)

    latency: float | None = None
    if not tutor.empty and "latency_ms" in tutor:
        values = pd.to_numeric(tutor["latency_ms"], errors="coerce")
        if values.notna().any():
            latency = round(float(values.mean()), 1)

    return {
        "total_users": total_users,
        "active_users": active_users,
        "watch_hours": round(watch_seconds / 3_600, 1),
        "saved_words": int(len(data.saved_words)),
        "word_clicks": int(len(data.click_events)),
        "tutor_questions": tutor_questions,
        "tutor_helpful_rate": helpful_rate,
        "error_rate": error_rate,
        "avg_tutor_latency_ms": latency,
    }


__all__ = [
    "DashboardData",
    "DashboardDataSourceError",
    "dashboard_data_from_payload",
    "filter_by_date",
    "load_dashboard_data",
    "load_demo_data",
    "load_json",
    "load_supabase_data",
    "summarize_metrics",
]
