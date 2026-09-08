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

# 분석 함수가 소비하는 표준 frame과 Supabase 원본 frame을 한 계약 안에 둔다.
# 원본 테이블은 실제 public schema의 이름을 사용하고, legacy fixture용 frame은
# 기존 화면과의 호환성을 위해 유지한다.
TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": (
        "id",
        "google_account_id",
        "email",
        "created_at",
        "last_login_at",
        "is_active",
        "level",
    ),
    "login_history": (
        "id",
        "user_id",
        "login_at",
        "logout_at",
        "last_access_at",
        "login_success",
    ),
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
        "saved_at",
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
    "ai_conversations": (
        "id",
        "user_id",
        "video_id",
        "question",
        "answer",
        "started_at",
        "feedback",
    ),
    "llm_usage": (
        "id",
        "user_id",
        "provider",
        "model_name",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "used_at",
    ),
    "api_logs": (
        "id",
        "api_name",
        "user_id",
        "requested_at",
        "response_time_ms",
        "status_code",
        "success",
        "error_message",
    ),
}

DATE_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": ("created_at", "last_login_at"),
    "login_history": ("login_at", "logout_at", "last_access_at"),
    "video_history": ("created_at", "updated_at"),
    "saved_words": ("created_at", "saved_at"),
    "click_events": ("created_at",),
    "tutor_messages": ("created_at",),
    "user_feedback": ("created_at",),
    "system_logs": ("created_at",),
    "ai_conversations": ("started_at",),
    "llm_usage": ("used_at",),
    "api_logs": ("requested_at",),
}
NUMERIC_COLUMNS: dict[str, tuple[str, ...]] = {
    "video_history": ("last_timestamp", "watch_duration_sec"),
    "saved_words": ("timestamp",),
    "click_events": ("timestamp",),
    "tutor_messages": ("timestamp", "latency_ms"),
    "system_logs": ("status_code", "latency_ms"),
    "llm_usage": ("input_tokens", "output_tokens", "total_tokens"),
    "api_logs": ("response_time_ms", "status_code"),
}

# Supabase에 실제로 존재하는 운영 테이블만 조회한다. video_history와
# click_events는 현재 프로젝트 schema에 없으므로 live 요청에서 조회하지 않는다.
SUPABASE_TABLES = (
    "users",
    "login_history",
    "saved_words",
    "ai_conversations",
    "llm_usage",
    "api_logs",
)

# Supabase REST 조회에는 실제 public schema 컬럼만 명시한다. 파생/legacy 컬럼은
# dashboard frame에서만 생성하고 PostgREST에 요청하지 않는다.
SUPABASE_SELECT_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": ("id", "google_account_id", "email", "created_at", "last_login_at"),
    "login_history": ("id", "user_id", "login_at", "logout_at", "last_access_at"),
    "saved_words": ("id", "user_id", "word", "saved_at"),
    "ai_conversations": ("id", "user_id", "video_id", "question", "answer", "started_at", "feedback"),
    "llm_usage": (
        "id",
        "user_id",
        "provider",
        "model_name",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "used_at",
    ),
    "api_logs": (
        "id",
        "api_name",
        "user_id",
        "requested_at",
        "response_time_ms",
        "status_code",
        "success",
        "error_message",
    ),
}
DEFAULT_SUPABASE_PAGE_SIZE = 1_000
DEFAULT_SUPABASE_MAX_ROWS = 50_000
DEFAULT_DEMO_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_data.json"
NEW_SUPABASE_KEY_PREFIXES = ("sb_publishable_", "sb_secret_")


class DashboardDataSourceError(RuntimeError):
    """대시보드 데이터 원천을 읽을 수 없을 때 발생하는 예외."""


@dataclass(frozen=True)
class DashboardData:
    """대시보드가 사용하는 표준 DataFrame 묶음."""

    frames: dict[str, pd.DataFrame]
    source: str
    generated_at: str | None = None
    source_tables: frozenset[str] = frozenset()

    def frame(self, name: str) -> pd.DataFrame:
        """이름으로 정규화된 데이터 프레임을 반환한다."""

        return self.frames[name]

    @property
    def users(self) -> pd.DataFrame:
        return self.frames["users"]

    @property
    def login_history(self) -> pd.DataFrame:
        return self.frames["login_history"]

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

    @property
    def ai_conversations(self) -> pd.DataFrame:
        return self.frames["ai_conversations"]

    @property
    def llm_usage(self) -> pd.DataFrame:
        return self.frames["llm_usage"]

    @property
    def api_logs(self) -> pd.DataFrame:
        return self.frames["api_logs"]


def _records(value: Any) -> Any:
    """테이블 payload의 흔한 응답 래퍼를 평탄화한다."""

    if isinstance(value, Mapping) and "items" in value:
        return value["items"]
    return value if value is not None else []


def _record_list(value: Any) -> list[Mapping[str, Any]]:
    """파생 frame 생성에 사용할 row mapping 목록을 반환한다."""

    records = _records(value)
    if isinstance(records, Mapping):
        return [records]
    if isinstance(records, (list, tuple)):
        return [record for record in records if isinstance(record, Mapping)]
    return []


def _conversation_messages(records: Any) -> list[dict[str, Any]]:
    """ai_conversations 한 행을 기존 Tutor message 두 행으로 변환한다."""

    messages: list[dict[str, Any]] = []
    for record in _record_list(records):
        conversation_id = record.get("id")
        common = {
            "conversation_id": conversation_id,
            "user_id": record.get("user_id"),
            "video_id": record.get("video_id"),
            "timestamp": None,
            "provider": None,
            "model": None,
            "latency_ms": None,
            "created_at": record.get("started_at"),
        }
        for sender, field, suffix in (
            ("user", "question", "question"),
            ("tutor", "answer", "answer"),
        ):
            message = record.get(field)
            if message is None or not str(message).strip():
                continue
            messages.append(
                {
                    "id": f"{conversation_id}:{suffix}",
                    "sender": sender,
                    "message": message,
                    **common,
                }
            )
    return messages


def _feedback_value(value: Any) -> Mapping[str, Any] | None:
    """JSONB 또는 문자열 형태의 feedback 객체를 안전하게 해석한다."""

    if isinstance(value, Mapping):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, Mapping) else None
    return None


def _conversation_feedback(records: Any) -> list[dict[str, Any]]:
    """ai_conversations의 JSONB feedback을 기존 피드백 frame으로 변환한다."""

    feedback_rows: list[dict[str, Any]] = []
    for record in _record_list(records):
        feedback = _feedback_value(record.get("feedback"))
        if feedback is None:
            continue
        rating = feedback.get("rating") or feedback.get("value") or feedback.get("type")
        if rating is None and "helpful" in feedback:
            rating = "up" if bool(feedback.get("helpful")) else "down"
        if rating is None:
            continue
        conversation_id = record.get("id")
        feedback_rows.append(
            {
                "id": f"{conversation_id}:feedback",
                "message_id": f"{conversation_id}:answer",
                "user_id": record.get("user_id"),
                "rating": rating,
                "reason": feedback.get("reason"),
                "created_at": record.get("started_at"),
            }
        )
    return feedback_rows


def _api_log_events(records: Any) -> list[dict[str, Any]]:
    """api_logs를 시스템 로그 표준 frame으로 변환한다."""

    events: list[dict[str, Any]] = []
    for record in _record_list(records):
        raw_status = record.get("status_code")
        try:
            status_code = int(raw_status) if raw_status is not None else None
        except (TypeError, ValueError):
            status_code = None
        success = record.get("success")
        if not isinstance(success, bool):
            success = status_code is not None and status_code < 400
        events.append(
            {
                "id": record.get("id"),
                "event_type": record.get("api_name"),
                "user_id": record.get("user_id"),
                "video_id": None,
                "status_code": status_code,
                "latency_ms": record.get("response_time_ms"),
                "severity": "info" if success else "error",
                # 원본 error_message는 raw api_logs frame에 보존하되, 운영 화면에는
                # 사용자 입력이나 provider 응답을 노출하지 않는 일반 상태만 표시한다.
                "message": "API request completed" if success else "API request failed",
                "created_at": record.get("requested_at"),
            }
        )
    return events


def _derived_payload(root: Mapping[str, Any]) -> dict[str, Any]:
    """실제 운영 테이블을 기존 분석용 파생 테이블과 합친다."""

    normalized = dict(root)
    if "ai_conversations" in root:
        normalized["tutor_messages"] = [
            *_record_list(root.get("tutor_messages", [])),
            *_conversation_messages(root.get("ai_conversations", [])),
        ]
        normalized["user_feedback"] = [
            *_record_list(root.get("user_feedback", [])),
            *_conversation_feedback(root.get("ai_conversations", [])),
        ]
    if "api_logs" in root:
        normalized["system_logs"] = [
            *_record_list(root.get("system_logs", [])),
            *_api_log_events(root.get("api_logs", [])),
        ]
    return normalized


def _normalize_frame(table: str, records: Any) -> pd.DataFrame:
    """테이블별 컬럼·날짜·수치 타입을 표준화한다."""

    if isinstance(records, pd.DataFrame):
        frame = records.copy()
    else:
        frame = pd.DataFrame(_records(records))

    # 실제 users/saved_words의 컬럼명을 기존 분석 계약에 맞춰 보완한다.
    # 값이 없는 optional column은 이후 reindex에서 안전하게 NaN으로 유지한다.
    if table == "users" and "is_active" not in frame:
        last_login_values = frame["last_login_at"] if "last_login_at" in frame else pd.Series(index=frame.index)
        last_login = pd.to_datetime(last_login_values, errors="coerce", utc=True)
        frame["is_active"] = last_login.notna()
    if table == "saved_words" and "created_at" not in frame:
        saved_values = frame["saved_at"] if "saved_at" in frame else pd.Series(index=frame.index)
        frame["created_at"] = saved_values

    columns = TABLE_COLUMNS[table]
    frame = frame.reindex(columns=columns)

    for column in DATE_COLUMNS.get(table, ()):
        frame[column] = pd.to_datetime(frame[column], errors="coerce", utc=True)

    for column in NUMERIC_COLUMNS.get(table, ()):
        numeric = pd.to_numeric(frame[column], errors="coerce")
        # 사용량·latency가 기록되지 않은 상태와 실제 0을 구분해야 한다.
        preserve_missing = table == "llm_usage" or (
            table == "tutor_messages" and column == "latency_ms"
        ) or (table == "system_logs" and column == "latency_ms")
        if not preserve_missing:
            numeric = numeric.fillna(0)
        frame[column] = numeric

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
    if not isinstance(root, Mapping):
        root = {}
    normalized_root = _derived_payload(root)
    frames = {
        table: _normalize_frame(table, normalized_root.get(table, []))
        for table in TABLE_COLUMNS
    }
    generated_at = root.get("generated_at")
    source_tables = frozenset(key for key in root if key != "generated_at")
    return DashboardData(
        frames=frames,
        source=source,
        generated_at=generated_at,
        source_tables=source_tables,
    )


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

    return DashboardData(
        frames=data.frames,
        source=source,
        generated_at=data.generated_at,
        source_tables=data.source_tables,
    )


def load_supabase_data(
    url: str,
    key: str,
    *,
    limit: int = DEFAULT_SUPABASE_PAGE_SIZE,
    max_rows: int | None = DEFAULT_SUPABASE_MAX_ROWS,
    timeout_seconds: float = 8.0,
) -> DashboardData:
    """서버 환경변수의 Supabase PostgREST endpoint에서 데이터를 읽는다.

    ``key``는 dashboard 서버 프로세스에서만 사용하며 코드·브라우저·화면에 노출하지
    않는다. 실제 schema 컬럼만 요청하고, 각 테이블은 안정적인 ``id`` 정렬과 offset
    페이지네이션으로 읽는다. 필수 운영 테이블이 없거나 응답이 비정상이면 부분 자료를
    정상 데이터처럼 표시하지 않고 예외를 발생시킨다.
    """

    if not url or not key:
        raise DashboardDataSourceError(
            "SUPABASE_URL과 SUPABASE_SECRET_KEY 또는 SUPABASE_KEY가 필요합니다."
        )
    if limit < 1:
        raise DashboardDataSourceError("Supabase 페이지 크기는 1 이상이어야 합니다.")
    if max_rows is not None and max_rows < 1:
        raise DashboardDataSourceError("Supabase 최대 조회 행 수는 1 이상이어야 합니다.")

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - pyproject가 보장하는 경로
        raise DashboardDataSourceError("Supabase 연결에 httpx가 필요합니다.") from exc

    # 새 publishable/secret key는 JWT가 아니므로 apikey 헤더만 사용한다.
    # 기존 anon/service_role JWT와의 호환성을 위해 레거시 형식에는
    # Authorization 헤더를 계속 붙인다.
    headers = {
        "apikey": key,
        "Accept": "application/json",
    }
    if not key.startswith(NEW_SUPABASE_KEY_PREFIXES):
        headers["Authorization"] = f"Bearer {key}"
    base_url = url.rstrip("/")
    payload: dict[str, Any] = {}

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            for table in SUPABASE_TABLES:
                selected_columns = ",".join(SUPABASE_SELECT_COLUMNS[table])

                def request_page(offset: int, page_limit: int) -> list[Mapping[str, Any]]:
                    response = client.get(
                        f"{base_url}/rest/v1/{table}",
                        params={
                            "select": selected_columns,
                            "order": "id.asc",
                            "limit": str(page_limit),
                            "offset": str(offset),
                        },
                        headers=headers,
                    )
                    status_code = response.status_code
                    if status_code == 404:
                        raise DashboardDataSourceError(
                            f"Supabase 필수 테이블을 찾을 수 없습니다: {table} (HTTP 404)"
                        )
                    if status_code in {401, 403}:
                        raise DashboardDataSourceError(
                            f"Supabase {table} 조회 권한이 없습니다 (HTTP {status_code})."
                        )
                    if not 200 <= status_code < 300:
                        raise DashboardDataSourceError(
                            f"Supabase {table} 조회에 실패했습니다 (HTTP {status_code})."
                        )
                    try:
                        page = response.json()
                    except ValueError as exc:
                        raise DashboardDataSourceError(
                            f"Supabase {table} 응답 형식이 올바르지 않습니다."
                        ) from exc
                    if not isinstance(page, list) or any(
                        not isinstance(row, Mapping) for row in page
                    ):
                        raise DashboardDataSourceError(
                            f"Supabase {table} 응답 형식이 올바르지 않습니다."
                        )
                    return page

                rows: list[Mapping[str, Any]] = []
                offset = 0
                while True:
                    page_limit = limit
                    if max_rows is not None:
                        remaining = max_rows - len(rows)
                        if remaining <= 0:
                            probe = request_page(len(rows), 1)
                            if probe:
                                raise DashboardDataSourceError(
                                    f"Supabase {table} 조회 결과가 최대 {max_rows:,}행을 초과합니다."
                                )
                            break
                        page_limit = min(page_limit, remaining)

                    page = request_page(offset, page_limit)
                    rows.extend(page)
                    offset += len(page)
                    if len(page) < page_limit:
                        break

                payload[table] = rows
    except DashboardDataSourceError:
        raise
    except httpx.TimeoutException as exc:
        raise DashboardDataSourceError("Supabase 응답 시간이 초과되었습니다.") from exc
    except httpx.HTTPError as exc:
        raise DashboardDataSourceError("Supabase 네트워크 요청에 실패했습니다.") from exc

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
        key = (
            supabase_key
            or os.getenv("SUPABASE_SECRET_KEY", "")
            or os.getenv("SUPABASE_KEY", "")
        )
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
        "login_history": "login_at",
        "video_history": "updated_at",
        "saved_words": "created_at",
        "click_events": "created_at",
        "tutor_messages": "created_at",
        "user_feedback": "created_at",
        "system_logs": "created_at",
        "ai_conversations": "started_at",
        "llm_usage": "used_at",
        "api_logs": "requested_at",
    }
    frames: dict[str, pd.DataFrame] = {}
    for table, frame in data.frames.items():
        active_column = date_columns[table]
        if table == "video_history" and frame[active_column].isna().all():
            active_column = "created_at"
        frames[table] = frame.loc[_date_mask(frame, active_column, start, end)].copy()
    return DashboardData(
        frames=frames,
        source=data.source,
        generated_at=data.generated_at,
        source_tables=data.source_tables,
    )


def _table_unavailable(data: DashboardData, table: str) -> bool:
    """현재 source에 해당 테이블 자체가 없는지 판정한다."""

    return data.source != "demo" and table not in data.source_tables


def _tutor_api_logs(data: DashboardData) -> pd.DataFrame:
    """Tutor 질문 API의 성공 요청만 골라 반환한다."""

    logs = data.api_logs.copy()
    if logs.empty or "api_name" not in logs:
        return logs.iloc[0:0]
    names = logs["api_name"].astype(str).str.lower()
    mask = names.str.contains("tutor/ask|tutor\\.ask", regex=True, na=False)
    logs = logs.loc[mask].copy()
    if logs.empty:
        return logs
    statuses = pd.to_numeric(logs.get("status_code"), errors="coerce")
    success = logs.get("success")
    if success is None:
        success = statuses.lt(400)
    else:
        success = success.fillna(statuses.lt(400)).astype(bool)
    return logs.loc[success].copy()


def summarize_metrics(data: DashboardData) -> dict[str, float | int | None]:
    """대시보드 상단 KPI를 계산한다."""

    users = data.users
    total_users = int(len(users))
    login_history = data.login_history
    if not login_history.empty and "user_id" in login_history:
        active_users = int(login_history["user_id"].dropna().astype(str).nunique())
    elif data.source == "supabase" and "login_history" in data.source_tables:
        # 실제 login_history가 비어 있으면 last_login_at을 현재 활동으로
        # 추정하지 않고, 선택 기간에 관측된 활성 사용자가 없다고 표시한다.
        active_users = 0
    elif "is_active" in users:
        active_users = int(users["is_active"].sum())
    elif "last_login_at" in users:
        active_users = int(users["last_login_at"].notna().sum())
    else:
        active_users = 0

    watch_hours: float | None
    if data.video_history.empty and _table_unavailable(data, "video_history"):
        watch_hours = None
    else:
        watch_seconds = float(data.video_history["watch_duration_sec"].sum())
        watch_hours = round(watch_seconds / 3_600, 1)

    feedback = data.user_feedback
    logs = data.system_logs
    tutor = data.tutor_messages
    tutor_api_logs = _tutor_api_logs(data)

    if "sender" in tutor and not tutor.empty:
        tutor_questions = int(tutor["sender"].astype(str).str.lower().eq("user").sum())
    elif not tutor_api_logs.empty:
        tutor_questions = int(len(tutor_api_logs))
    else:
        tutor_questions = 0

    helpful_rate: float | None = None
    if not feedback.empty and "rating" in feedback:
        ratings = feedback["rating"].astype(str).str.lower()
        helpful_rate = round(float(ratings.eq("up").mean() * 100), 1)

    error_rate: float | None = None
    if logs.empty and not data.api_logs.empty:
        logs = _api_log_events(data.api_logs.to_dict("records"))
        logs = _normalize_frame("system_logs", logs)
    if not logs.empty:
        status_values = logs["status_code"] if "status_code" in logs else pd.Series(index=logs.index)
        statuses = pd.to_numeric(status_values, errors="coerce")
        observed = statuses.notna()
        errors = statuses.ge(400).fillna(False)
        if "success" in logs:
            success_values = logs["success"].astype("boolean")
            observed |= success_values.notna()
            errors |= success_values.eq(False).fillna(False)
        if "severity" in logs:
            severity_values = logs["severity"].astype(str).str.lower()
            observed |= logs["severity"].notna()
            errors |= severity_values.isin({"error", "critical"})
        if observed.any():
            error_rate = round(float(errors[observed].mean() * 100), 1)

    latency: float | None = None
    if not tutor.empty and "latency_ms" in tutor:
        response_rows = tutor
        if "sender" in response_rows:
            response_rows = response_rows[
                response_rows["sender"].astype(str).str.lower().eq("tutor")
            ]
        values = pd.to_numeric(response_rows["latency_ms"], errors="coerce")
        if values.notna().any():
            latency = round(float(values.mean()), 1)
    if latency is None and not tutor_api_logs.empty:
        values = pd.to_numeric(tutor_api_logs["response_time_ms"], errors="coerce")
        if values.notna().any():
            latency = round(float(values.mean()), 1)

    word_clicks: int | None
    if data.click_events.empty and _table_unavailable(data, "click_events"):
        word_clicks = None
    else:
        word_clicks = int(len(data.click_events))

    return {
        "total_users": total_users,
        "active_users": active_users,
        "watch_hours": watch_hours,
        "saved_words": int(len(data.saved_words)),
        "word_clicks": word_clicks,
        "tutor_questions": tutor_questions,
        "tutor_helpful_rate": helpful_rate,
        "error_rate": error_rate,
        "avg_tutor_latency_ms": latency,
    }


__all__ = [
    "DashboardData",
    "DashboardDataSourceError",
    "SUPABASE_SELECT_COLUMNS",
    "SUPABASE_TABLES",
    "dashboard_data_from_payload",
    "filter_by_date",
    "load_dashboard_data",
    "load_demo_data",
    "load_json",
    "load_supabase_data",
    "summarize_metrics",
]
