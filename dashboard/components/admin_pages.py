"""와이어프레임의 관리자용 목록·사용량 화면."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape

import pandas as pd
import streamlit as st

from dashboard.analytics.data_loader import DashboardData
from dashboard.components.display_labels import provider_label, rating_label


PAGE_COLUMNS = ["사용자", "질문 내용", "모델", "응답 시간", "일시", "평가"]
MODEL_LABELS = {
    "gemini-3.6-flash": "Gemini 3.6 Flash",
    "gemini:3.6-flash": "Gemini 3.6 Flash",
    "openai/gpt-oss-20b": "GPT-OSS 20B",
    "gpt-oss-20b": "GPT-OSS 20B",
}


def _missing(value: object) -> bool:
    """스칼라 값의 결측 여부를 안전하게 판정한다."""

    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _text(value: object, fallback: str = "-") -> str:
    """표시용 문자열을 반환한다."""

    return fallback if _missing(value) else str(value)


def _date_text(value: object) -> str:
    """UTC 시각을 와이어프레임 표기 형식으로 바꾼다."""

    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return "-" if pd.isna(parsed) else parsed.strftime("%Y.%m.%d")


def _datetime_text(value: object) -> str:
    """UTC 시각을 날짜와 시간이 함께 보이는 형식으로 바꾼다."""

    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return "-" if pd.isna(parsed) else parsed.strftime("%Y.%m.%d %H:%M")


def _model_label(value: object) -> str:
    """긴 provider/model 식별자를 관리자 화면용 이름으로 정리한다."""

    raw = _text(value, "알 수 없는 모델").strip()
    known_label = MODEL_LABELS.get(raw.lower())
    if known_label:
        return known_label
    pretty = raw.replace("/", " ").replace(":", " ").replace("_", " ").replace("-", " ")
    words = pretty.split()
    return " ".join(
        word.upper() if word.lower() in {"ai", "api", "gpt", "oss", "llm"} else word.capitalize()
        for word in words
    )


def _latency_text(value: object) -> str:
    """밀리초 응답시간을 초 단위로 표시한다."""

    if _missing(value):
        return "-"
    try:
        return f"{float(value) / 1_000:.1f}s"
    except (TypeError, ValueError):
        return "-"


def _latency_precise_text(value: object) -> str:
    """관리자 KPI와 상세 표에 응답시간의 실제 단위를 함께 표시한다."""

    if _missing(value):
        return "-"
    try:
        milliseconds = float(value)
    except (TypeError, ValueError):
        return "-"
    if milliseconds >= 1_000:
        return f"{milliseconds / 1_000:.2f}s ({milliseconds:,.0f}ms)"
    return f"{milliseconds:,.0f}ms"


def _column(frame: pd.DataFrame, name: str) -> pd.Series:
    """없는 컬럼도 같은 index의 빈 Series로 반환한다."""

    if name in frame:
        return frame[name]
    return pd.Series(index=frame.index, dtype="object")


def _user_directory(data: DashboardData) -> dict[str, str]:
    """user_id를 이메일로 바꿀 수 있는 사전을 만든다."""

    if data.users.empty or "id" not in data.users or "email" not in data.users:
        return {}
    return {
        str(row["id"]): _text(row["email"], "알 수 없는 사용자")
        for _, row in data.users[["id", "email"]].iterrows()
    }


def _login_record_ids(data: DashboardData) -> set[str]:
    """로그인 이력이 한 번이라도 있는 user_id 집합을 만든다."""

    history = data.login_history
    if history.empty or "user_id" not in history:
        return set()
    return {
        str(value)
        for value in history["user_id"].dropna().tolist()
    }


def _user_name(email: object, account_id: object = None) -> str:
    """이름 컬럼이 없는 schema에서도 읽기 쉬운 사용자명을 만든다."""

    account = _text(account_id, "")
    if account:
        return account
    address = _text(email, "알 수 없는 사용자")
    return address.split("@", 1)[0] if "@" in address else address


def _heading(number: int, title: str, subtitle: str) -> None:
    """공통 페이지 제목을 렌더링한다."""

    st.markdown(
        f"""
        <div class="subsync-page-heading">
            <div class="subsync-heading-number">{number}</div>
            <div>
                <h1>{escape(title)}</h1>
                <p>{escape(subtitle)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _download_button(frame: pd.DataFrame, label: str, filename: str) -> None:
    """현재 필터 결과를 CSV로 내려받는 버튼을 표시한다."""

    st.download_button(
        label,
        data=frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


def _search_mask(frame: pd.DataFrame, columns: list[str], query: str) -> pd.Series:
    """여러 컬럼을 합쳐 검색어 마스크를 만든다."""

    if not query.strip():
        return pd.Series(True, index=frame.index)
    searchable = frame.reindex(columns=columns).fillna("").astype(str).agg(" ".join, axis=1)
    return searchable.str.contains(query.strip(), case=False, na=False, regex=False)


def render_user_management(data: DashboardData) -> None:
    """사용자 검색·로그인 기록 필터·CSV 내보내기 화면을 표시한다."""

    _heading(2, "사용자 관리", "사용자 목록, 검색, 로그인 기록 관리")
    frame = data.users.copy()
    if frame.empty:
        st.info("사용자 데이터가 없습니다.")
        return

    frame["_name"] = [
        _user_name(email, account)
        for email, account in zip(_column(frame, "email"), _column(frame, "google_account_id"))
    ]
    frame["_email"] = _column(frame, "email").map(lambda value: _text(value))
    login_ids = _login_record_ids(data)
    frame["_login_status"] = [
        "로그인 기록 있음"
        if str(user_id) in login_ids or not _missing(last_login)
        else "로그인 기록 없음"
        for user_id, last_login in zip(_column(frame, "id"), _column(frame, "last_login_at"))
    ]

    search_col, status_col, export_col = st.columns([1.6, 0.8, 0.8], gap="small")
    with search_col:
        query = st.text_input("이름, 이메일로 검색", placeholder="검색어 입력", key="users-search")
    with status_col:
        status = st.selectbox(
            "로그인 기록",
            ["전체", "로그인 기록 있음", "로그인 기록 없음"],
            key="users-status",
        )

    filtered = frame.loc[_search_mask(frame, ["_name", "_email", "id"], query)].copy()
    if status != "전체":
        filtered = filtered.loc[filtered["_login_status"].eq(status)].copy()

    display = pd.DataFrame(
        {
            "이름": filtered["_name"],
            "이메일": filtered["_email"],
            "가입일": _column(filtered, "created_at").map(_date_text),
            "최근 접속": _column(filtered, "last_login_at").map(_date_text),
            "로그인 기록": filtered["_login_status"],
            "레벨": _column(filtered, "level").map(lambda value: _text(value)),
        },
        index=filtered.index,
    )
    with export_col:
        _download_button(display, "사용자 내보내기", "subsync-사용자-목록.csv")

    st.caption(f"검색 결과 {len(display):,}명")
    st.dataframe(display.reset_index(drop=True), width="stretch", hide_index=True)


def _related_messages(messages: pd.DataFrame, conversation_id: object) -> pd.DataFrame:
    """대화 ID에 연결된 메시지만 반환한다."""

    if messages.empty or "conversation_id" not in messages:
        return messages.iloc[0:0]
    return messages.loc[messages["conversation_id"].astype(str).eq(str(conversation_id))]


def _first_value(frame: pd.DataFrame, column: str) -> object:
    """컬럼의 첫 번째 non-null 값을 반환한다."""

    if frame.empty or column not in frame:
        return None
    values = frame[column].dropna()
    return None if values.empty else values.iloc[0]


def _feedback_text(value: object) -> str:
    """JSONB feedback과 legacy rating을 화면 라벨로 변환한다."""

    if isinstance(value, Mapping):
        rating = value.get("rating") or value.get("value") or value.get("type")
        if rating is None and "helpful" in value:
            rating = "up" if bool(value["helpful"]) else "down"
        return rating_label(rating) if rating is not None else "-"
    if _missing(value):
        return "-"
    return rating_label(value)


def _conversation_frame(data: DashboardData) -> pd.DataFrame:
    """실제 대화 테이블 또는 파생 Tutor message를 목록 계약으로 변환한다."""

    directory = _user_directory(data)
    messages = data.tutor_messages.copy()
    if messages.empty or "sender" not in messages:
        questions = messages.iloc[0:0]
    else:
        questions = messages[messages["sender"].astype(str).str.lower().eq("user")].copy()

    rows: list[dict[str, object]] = []
    if not data.ai_conversations.empty:
        for _, row in data.ai_conversations.iterrows():
            conversation_id = row.get("id")
            related = _related_messages(messages, conversation_id)
            tutor_rows = related[
                related["sender"].astype(str).str.lower().eq("tutor")
            ] if "sender" in related else related
            user_id = row.get("user_id")
            rows.append(
                {
                    "사용자": directory.get(str(user_id), _text(user_id, "사용자")),
                    "질문 내용": _text(row.get("question"), "질문 내용 없음"),
                    "모델": _model_label(_first_value(tutor_rows, "model")),
                    "응답 시간": _latency_text(_first_value(tutor_rows, "latency_ms")),
                    "일시": _date_text(row.get("started_at")),
                    "평가": _feedback_text(row.get("feedback")),
                }
            )
        return pd.DataFrame(rows, columns=PAGE_COLUMNS)

    for _, row in questions.iterrows():
        conversation_id = row.get("conversation_id")
        related = _related_messages(messages, conversation_id)
        tutor_rows = related[
            related["sender"].astype(str).str.lower().eq("tutor")
        ] if "sender" in related else related
        model = row.get("model")
        if _missing(model):
            model = _first_value(tutor_rows, "model")
        user_id = row.get("user_id")
        rows.append(
            {
                "사용자": directory.get(str(user_id), _text(user_id, "사용자")),
                "질문 내용": _text(row.get("message"), "질문 내용 없음"),
                "모델": _model_label(model),
                "응답 시간": _latency_text(_first_value(tutor_rows, "latency_ms")),
                "일시": _date_text(row.get("created_at")),
                "평가": "-",
            }
        )
    return pd.DataFrame(rows, columns=PAGE_COLUMNS)


def render_conversation_history(data: DashboardData) -> None:
    """AI 질문·응답 기록을 검색하고 조회하는 화면을 표시한다."""

    _heading(3, "AI 대화 내역", "사용자의 AI 질문/응답 기록 확인")
    frame = _conversation_frame(data)
    if frame.empty:
        st.info("AI 대화 내역이 없습니다.")
        return

    search_col, user_col = st.columns([1.6, 0.9], gap="small")
    with search_col:
        query = st.text_input("질문 내용으로 검색", placeholder="질문 검색", key="conversation-search")
    users = ["전체 사용자", *sorted(frame["사용자"].dropna().astype(str).unique())]
    with user_col:
        selected_user = st.selectbox("사용자", users, key="conversation-user")

    filtered = frame.loc[_search_mask(frame, ["사용자", "질문 내용", "모델"], query)].copy()
    if selected_user != "전체 사용자":
        filtered = filtered.loc[filtered["사용자"].eq(selected_user)].copy()
    st.caption(f"검색 결과 {len(filtered):,}건")
    st.dataframe(filtered.reset_index(drop=True), width="stretch", hide_index=True)


def render_word_management(data: DashboardData) -> None:
    """저장 단어 목록을 검색·필터링하는 화면을 표시한다."""

    _heading(4, "단어 관리", "사용자 저장 단어 목록 관리")
    frame = data.saved_words.copy()
    if frame.empty:
        st.info("저장된 단어가 없습니다.")
        return

    directory = _user_directory(data)
    frame["_user"] = _column(frame, "user_id").map(
        lambda value: directory.get(str(value), _text(value, "알 수 없는 사용자"))
    )
    frame["_word"] = _column(frame, "word").map(lambda value: _text(value))
    frame["_meaning"] = _column(frame, "meaning").map(lambda value: _text(value))

    search_col, user_col, export_col = st.columns([1.45, 0.8, 0.8], gap="small")
    with search_col:
        query = st.text_input("단어로 검색", placeholder="단어 검색", key="words-search")
    users = ["전체 사용자", *sorted(frame["_user"].dropna().astype(str).unique())]
    with user_col:
        selected_user = st.selectbox("사용자", users, key="words-user")

    filtered = frame.loc[_search_mask(frame, ["_word", "_meaning", "_user"], query)].copy()
    if selected_user != "전체 사용자":
        filtered = filtered.loc[filtered["_user"].eq(selected_user)].copy()
    display = pd.DataFrame(
        {
            "단어": filtered["_word"],
            "의미": filtered["_meaning"],
            "사용자": filtered["_user"],
            "저장일": _column(filtered, "created_at").map(_date_text),
        },
        index=filtered.index,
    )
    with export_col:
        _download_button(display, "단어 내보내기", "subsync-저장-단어.csv")

    st.caption(f"검색 결과 {len(display):,}건")
    st.dataframe(display.reset_index(drop=True), width="stretch", hide_index=True)


def _api_health(data: DashboardData) -> dict[str, object]:
    """api_logs에서 오류율·P95 응답시간·최근 상태를 계산한다."""

    logs = data.api_logs.copy()
    if logs.empty:
        return {
            "status": "데이터 없음",
            "error_rate": None,
            "p95_ms": None,
            "request_count": 0,
            "failure_count": 0,
            "latest_failure_at": None,
            "latest_failure_api": None,
            "latest_failure_status": None,
        }

    statuses = pd.to_numeric(_column(logs, "status_code"), errors="coerce")
    observed = statuses.notna().astype(bool)
    failures = statuses.ge(400).fillna(False).astype(bool)
    if "success" in logs:
        success_values = _column(logs, "success").astype("boolean")
        observed |= success_values.notna().astype(bool)
        failures |= success_values.eq(False).fillna(False).astype(bool)

    request_count = int(observed.sum())
    failure_mask = failures & observed
    failure_count = int(failure_mask.sum())
    error_rate = (
        None
        if request_count == 0
        else round(float(failure_count / request_count * 100), 1)
    )

    response_times = pd.to_numeric(
        _column(logs, "response_time_ms"), errors="coerce"
    ).dropna()
    p95_ms = None if response_times.empty else round(float(response_times.quantile(0.95)), 1)

    ordered = logs.assign(
        _requested_at=pd.to_datetime(
            _column(logs, "requested_at"), errors="coerce", utc=True
        )
    ).sort_values("_requested_at", na_position="last")
    latest_failure = ordered.loc[
        failure_mask.reindex(ordered.index, fill_value=False)
    ]
    latest_failure_at = None
    latest_failure_api = None
    latest_failure_status = None
    if not latest_failure.empty:
        failure_row = latest_failure.iloc[-1]
        latest_failure_at = failure_row.get("_requested_at")
        latest_failure_api = _text(failure_row.get("api_name"), "API 요청")
        raw_status = failure_row.get("status_code")
        if not _missing(raw_status):
            try:
                latest_failure_status = f"HTTP {int(float(raw_status))}"
            except (TypeError, ValueError):
                latest_failure_status = _text(raw_status)
        elif not _missing(failure_row.get("success")):
            latest_failure_status = "success=false"

    status = "데이터 없음" if request_count == 0 else "주의" if failure_count else "정상"
    return {
        "status": status,
        "error_rate": error_rate,
        "p95_ms": p95_ms,
        "request_count": request_count,
        "failure_count": failure_count,
        "latest_failure_at": latest_failure_at,
        "latest_failure_api": latest_failure_api,
        "latest_failure_status": latest_failure_status,
    }


def _refresh_text(value: object) -> str:
    """데이터 snapshot 생성 시각을 관리자용 문자열로 표시한다."""

    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return "-" if pd.isna(parsed) else parsed.strftime("%Y.%m.%d %H:%M UTC")


def _render_health_panel(data: DashboardData) -> dict[str, object]:
    """Supabase·AI API 상태와 마지막 갱신 시각을 표시한다."""

    api_health = _api_health(data)
    supabase_status = "정상" if data.source == "supabase" else "확인 필요"
    request_count = int(api_health["request_count"])
    failure_count = int(api_health["failure_count"])
    api_detail = (
        f"오류 {failure_count:,}건 / {request_count:,}건"
        if request_count
        else "api_logs 데이터 없음"
    )
    cards = [
        ("데이터 연결", supabase_status, "Data API"),
        ("AI API 상태", str(api_health["status"]), api_detail),
        ("마지막 갱신", _refresh_text(data.generated_at), "현재 snapshot"),
    ]
    markup = []
    for label, value, detail in cards:
        tone = "ok" if value == "정상" else "warn" if value in {"주의", "확인 필요"} else "neutral"
        markup.append(
            f'<div class="subsync-health-card {tone}"><div class="subsync-health-label">{escape(label)}</div><div class="subsync-health-value">{escape(value)}</div><div class="subsync-health-detail">{escape(detail)}</div></div>'
        )
    st.markdown(
        f'<div class="subsync-health-grid">{"".join(markup)}</div>',
        unsafe_allow_html=True,
    )
    if api_health["status"] == "주의":
        error_rate = api_health["error_rate"]
        latest_api = escape(_text(api_health["latest_failure_api"], "API 요청"))
        latest_status = escape(_text(api_health["latest_failure_status"], "실패 응답"))
        latest_at = _refresh_text(api_health["latest_failure_at"])
        st.markdown(
            "<div class=\"subsync-health-note warning\">"
            "<span class=\"subsync-callout-mark\">!</span>"
            f"<div><strong>AI API 주의:</strong> 선택한 조회 기간에 "
            f"{failure_count:,}건/{request_count:,}건의 실패가 확인되었습니다 "
            f"(오류율 {float(error_rate):.1f}%). "
            f"최근 실패는 {latest_api} · {latest_status} · {latest_at}입니다.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    elif api_health["status"] == "정상":
        st.markdown(
            f'<div class="subsync-health-note ok"><span class="subsync-callout-mark">✓</span>'
            f'<div><strong>AI API 정상:</strong> 선택한 조회 기간의 {request_count:,}건 요청에서 실패가 확인되지 않았습니다.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="subsync-health-note neutral"><span class="subsync-callout-mark">i</span>'
            '<div><strong>AI API 확인 불가:</strong> 선택한 조회 기간에 판단할 api_logs가 없습니다.</div></div>',
            unsafe_allow_html=True,
        )
    return api_health


def _api_success_series(frame: pd.DataFrame) -> pd.Series:
    """api_logs의 success 또는 상태 코드로 성공 여부를 계산한다."""

    statuses = pd.to_numeric(_column(frame, "status_code"), errors="coerce")
    inferred = statuses.lt(400)
    raw_success = _column(frame, "success")
    parsed_success = raw_success.astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    return parsed_success.where(parsed_success.notna(), inferred).fillna(False).astype(bool)


def _api_endpoint_text(value: object) -> str:
    """API 이름을 빈 값 없이 읽기 쉬운 문자열로 표시한다."""

    endpoint = _text(value, "API 요청").strip()
    return endpoint or "API 요청"


def _api_status_text(value: object, success: bool) -> str:
    """HTTP 상태 코드를 관리자용 상태 라벨로 변환한다."""

    if not _missing(value):
        try:
            code = int(float(value))
        except (TypeError, ValueError):
            code = None
        if code is not None:
            if code < 300:
                return f"{code} OK"
            if code < 400:
                return f"{code} Redirect"
            return f"{code} 오류"
    return "성공" if success else "실패"


def _api_status_code_text(value: object) -> str:
    """상태 코드 숫자를 표에 명확하게 표시한다."""

    if _missing(value):
        return "-"
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return _text(value)


def _api_request_frame(frame: pd.DataFrame, data: DashboardData) -> pd.DataFrame:
    """api_logs 원본을 최근 API 호출 표로 변환한다."""

    directory = _user_directory(data)
    success = _api_success_series(frame)
    return pd.DataFrame(
        {
            "상태 코드": _column(frame, "status_code").map(_api_status_code_text),
            "요청": _column(frame, "api_name").map(_api_endpoint_text),
            "사용자": _column(frame, "user_id").map(
                lambda value: directory.get(str(value), _text(value, "알 수 없는 사용자"))
            ),
            "상태": [
                _api_status_text(status, ok)
                for status, ok in zip(_column(frame, "status_code"), success)
            ],
            "응답시간": _column(frame, "response_time_ms").map(_latency_precise_text),
            "일시": _column(frame, "requested_at").map(_datetime_text),
        },
        index=frame.index,
    )


def _api_endpoint_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """엔드포인트별 호출량·성공률·평균 응답시간을 집계한다."""

    working = pd.DataFrame(
        {
            "_endpoint": _column(frame, "api_name").map(_api_endpoint_text),
            "_success": _api_success_series(frame),
            "_latency": pd.to_numeric(
                _column(frame, "response_time_ms"), errors="coerce"
            ),
        },
        index=frame.index,
    )
    summary = (
        working.groupby("_endpoint", as_index=False)
        .agg(
            호출수=("_endpoint", "size"),
            성공률=("_success", "mean"),
            평균응답시간=("_latency", "mean"),
        )
        .sort_values("호출수", ascending=False)
    )
    if summary.empty:
        return pd.DataFrame(columns=["엔드포인트", "호출 수", "성공률", "평균 응답시간"])
    summary["성공률"] = summary["성공률"].map(
        lambda value: "-" if _missing(value) else f"{float(value) * 100:.1f}%"
    )
    summary["평균응답시간"] = summary["평균응답시간"].map(_latency_precise_text)
    return summary.rename(
        columns={
            "_endpoint": "엔드포인트",
            "호출수": "호출 수",
            "평균응답시간": "평균 응답시간",
        }
    )


def render_api_calls(data: DashboardData) -> None:
    """첨부 와이어프레임의 세 번째 화면인 API 호출을 표시한다."""

    _heading(4, "API 호출", "엔드포인트별 호출량 및 응답 상태 확인")
    _render_health_panel(data)
    frame = data.api_logs.copy()
    if frame.empty:
        st.info("API 호출 데이터가 없습니다.")
        return

    directory = _user_directory(data)
    frame["_endpoint"] = _column(frame, "api_name").map(_api_endpoint_text)
    frame["_user"] = _column(frame, "user_id").map(
        lambda value: directory.get(str(value), _text(value, "알 수 없는 사용자"))
    )
    endpoint_options = ["전체 엔드포인트", *sorted(frame["_endpoint"].unique())]
    user_options = ["전체 사용자", *sorted(frame["_user"].unique())]
    endpoint_filter, user_filter = st.columns([1, 1], gap="small")
    with endpoint_filter:
        selected_endpoint = st.selectbox(
            "엔드포인트", endpoint_options, key="api-endpoint"
        )
    with user_filter:
        selected_user = st.selectbox("사용자", user_options, key="api-user")

    if selected_endpoint != "전체 엔드포인트":
        frame = frame.loc[frame["_endpoint"].eq(selected_endpoint)].copy()
    if selected_user != "전체 사용자":
        frame = frame.loc[frame["_user"].eq(selected_user)].copy()

    success = _api_success_series(frame)
    statuses = pd.to_numeric(_column(frame, "status_code"), errors="coerce")
    latencies = pd.to_numeric(
        _column(frame, "response_time_ms"), errors="coerce"
    ).dropna()
    request_count = len(frame)
    success_rate = None if not request_count else float(success.mean() * 100)
    average_latency = None if latencies.empty else float(latencies.mean())
    failure_count = int((~success).sum())
    metric_values = (
        f"{request_count:,}",
        "-" if success_rate is None else f"{success_rate:.1f}%",
        _latency_precise_text(average_latency),
        f"{failure_count:,}",
    )
    metric_columns = st.columns(4, gap="small")
    for column, label, value in zip(
        metric_columns,
        ("API 요청", "성공률", "평균 latency", "오류 요청"),
        metric_values,
    ):
        with column:
            st.metric(label, value)

    st.markdown("#### 엔드포인트별 호출량")
    endpoint_summary = _api_endpoint_summary(frame)
    st.dataframe(
        endpoint_summary,
        width="stretch",
        hide_index=True,
        column_config={
            "엔드포인트": st.column_config.TextColumn("엔드포인트", width="large"),
            "호출 수": st.column_config.TextColumn("호출 수", width="small"),
            "성공률": st.column_config.TextColumn("성공률", width="small"),
            "평균 응답시간": st.column_config.TextColumn("평균 응답시간", width="medium"),
        },
    )

    st.markdown("#### 최근 API 호출")
    ordered = frame.assign(
        _requested_at=pd.to_datetime(
            _column(frame, "requested_at"), errors="coerce", utc=True
        )
    ).sort_values("_requested_at", ascending=False, na_position="last")
    latest_status_code = "-"
    if not ordered.empty:
        latest_status_code = _api_status_code_text(ordered.iloc[0].get("status_code"))
    st.markdown(
        f'<div class="subsync-latest-status"><strong>최근 상태 코드</strong><span>{escape(latest_status_code)}</span></div>',
        unsafe_allow_html=True,
    )
    recent = _api_request_frame(ordered.head(50), data)
    st.dataframe(
        recent.reset_index(drop=True),
        width="stretch",
        hide_index=True,
        column_config={
            "상태 코드": st.column_config.TextColumn("상태 코드", width="small"),
            "요청": st.column_config.TextColumn("요청", width="large"),
            "사용자": st.column_config.TextColumn("사용자", width="medium"),
            "상태": st.column_config.TextColumn("상태", width="small"),
            "응답시간": st.column_config.TextColumn("응답시간", width="medium"),
            "일시": st.column_config.TextColumn("일시", width="medium"),
        },
    )

    rate_limit_count = int(statuses.eq(429).fillna(False).sum())
    if rate_limit_count:
        st.info(
            f"429 rate limit 응답이 {rate_limit_count:,}건 있습니다. 제공자 fallback 또는 재시도 정책을 확인하세요."
        )


def _number_text(value: object) -> str:
    """토큰 수를 천 단위 구분 문자열로 표시한다."""

    if _missing(value):
        return "-"
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "-"


def _success_text(value: object) -> str:
    """llm_usage의 finish_reason을 성공 여부 라벨로 바꾼다."""

    if _missing(value) or not str(value).strip():
        return "-"
    reason = str(value).strip().lower()
    failure_words = {"error", "failed", "failure", "cancelled", "canceled", "timeout"}
    return "실패" if reason in failure_words or any(word in reason for word in failure_words) else "성공"


def _usage_detail_frame(frame: pd.DataFrame, data: DashboardData) -> pd.DataFrame:
    """llm_usage 원본을 관리자용 상세 요청 내역으로 변환한다."""

    directory = _user_directory(data)
    return pd.DataFrame(
        {
            "사용자": _column(frame, "user_id").map(
                lambda value: directory.get(str(value), _text(value, "알 수 없는 사용자"))
            ),
            "모델": _column(frame, "model_name").map(_model_label),
            "입력 토큰": _column(frame, "input_tokens").map(_number_text),
            "출력 토큰": _column(frame, "output_tokens").map(_number_text),
            "총 토큰": _column(frame, "total_tokens").map(_number_text),
            "응답 시간": _column(frame, "provider_latency").map(_latency_precise_text),
            "성공 여부": _column(frame, "finish_reason").map(_success_text),
            "일시": _column(frame, "used_at").map(_datetime_text),
        },
        index=frame.index,
    )


def _usage_summary_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """와이어프레임의 사용량 상세 표를 만든다."""

    input_tokens = pd.to_numeric(_column(frame, "input_tokens"), errors="coerce").fillna(0)
    output_tokens = pd.to_numeric(_column(frame, "output_tokens"), errors="coerce").fillna(0)
    total_tokens = pd.to_numeric(_column(frame, "total_tokens"), errors="coerce").fillna(0)
    latencies = pd.to_numeric(_column(frame, "provider_latency"), errors="coerce").dropna()
    finish_reasons = _column(frame, "finish_reason").map(_success_text)
    success_count = int(finish_reasons.eq("성공").sum())
    failure_count = int(finish_reasons.eq("실패").sum())
    average_latency = None if latencies.empty else float(latencies.mean())

    rows = [
        ("입력 토큰", _number_text(input_tokens.sum()), "provider"),
        ("출력 토큰", _number_text(output_tokens.sum()), "provider"),
        ("총 토큰", _number_text(total_tokens.sum()), "provider"),
        ("호출 수", f"{len(frame):,}건", "server"),
        ("평균 응답시간", _latency_precise_text(average_latency), "provider_latency"),
        ("성공 / 실패", f"{success_count:,}건 / {failure_count:,}건", "finish_reason"),
    ]
    return pd.DataFrame(rows, columns=["항목", "값", "소스"])


def _render_usage_bar_chart(counts: pd.Series, *, show_share: bool = False) -> None:
    """제공자·모델별 호출 수를 가로로 읽기 쉬운 막대 차트로 표시한다."""

    max_count = max(float(counts.max()), 1.0)
    total_count = max(float(counts.sum()), 1.0)
    rows = []
    for label, count in counts.items():
        numeric_count = float(count)
        bar_width = max(0.0, min(numeric_count / max_count * 100, 100))
        share = numeric_count / total_count * 100
        value = f"{int(numeric_count):,}건"
        if show_share:
            value = f"{value} · {share:.0f}%"
        rows.append(
            f'''
            <div class="subsync-model-chart-row">
              <div class="subsync-model-chart-label">{escape(str(label))}</div>
              <div class="subsync-model-chart-track"><div class="subsync-model-chart-bar" style="width: {bar_width:.2f}%"></div></div>
              <div class="subsync-model-chart-value">{escape(value)}</div>
            </div>
            '''
        )
    st.html(
        f'''
        <div class="subsync-model-usage-chart">
          <div class="subsync-model-chart-rows">{"".join(rows)}</div>
          <div class="subsync-chart-axis-title">호출 수 기준</div>
        </div>
        ''',
    )


def _render_daily_token_chart(daily: pd.Series) -> None:
    """날짜 눈금이 세로로 회전하지 않도록 SVG 차트로 표시한다."""

    chart_width = 720
    chart_height = 280
    left = 58
    right = 18
    top = 18
    bottom = 52
    plot_width = chart_width - left - right
    plot_height = chart_height - top - bottom
    values = pd.to_numeric(daily, errors="coerce").fillna(0)
    y_max = max(float(values.max()), 1.0)
    labels = [
        value.strftime("%m/%d") if hasattr(value, "strftime") else str(value)
        for value in daily.index
    ]
    point_count = len(values)
    x_positions = [
        left if point_count == 1 else left + index * plot_width / (point_count - 1)
        for index in range(point_count)
    ]
    y_positions = [
        top + plot_height - float(value) / y_max * plot_height for value in values
    ]

    grid_parts = []
    for tick in range(5):
        ratio = tick / 4
        y = top + plot_height - ratio * plot_height
        tick_value = y_max * ratio
        grid_parts.append(
            f'<line class="subsync-svg-grid" x1="{left}" y1="{y:.1f}" x2="{chart_width - right}" y2="{y:.1f}"/>'
            f'<text class="subsync-svg-y-label" x="{left - 10}" y="{y + 4:.1f}" text-anchor="end">{escape(_number_text(tick_value))}</text>'
        )

    path = " ".join(
        f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}"
        for index, (x, y) in enumerate(zip(x_positions, y_positions))
    )
    points = []
    for label, x, y, value in zip(labels, x_positions, y_positions, values):
        points.append(
            f'<circle class="subsync-svg-point" cx="{x:.1f}" cy="{y:.1f}" r="4"><title>{escape(label)}: {_number_text(value)} 토큰</title></circle>'
            f'<text class="subsync-svg-x-label" x="{x:.1f}" y="{chart_height - 29}" text-anchor="middle">{escape(label)}</text>'
        )
    st.markdown(
        f'''
        <div class="subsync-daily-token-chart">
          <svg viewBox="0 0 {chart_width} {chart_height}" role="img" aria-label="일별 토큰 추이">
            {"".join(grid_parts)}
            <path class="subsync-svg-line" d="{path}"/>
            {"".join(points)}
            <text class="subsync-svg-axis-title" x="{chart_width / 2}" y="{chart_height - 5}" text-anchor="middle">날짜</text>
          </svg>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def render_ai_usage(
    data: DashboardData,
    metrics: Mapping[str, object] | None = None,
) -> None:
    """와이어프레임 형태의 AI 제공자 사용량·상세 요청 내역을 표시한다."""

    _heading(3, "AI 사용량", "모델별 사용 현황 및 토큰 모니터링")
    api_health = _render_health_panel(data)
    frame = data.llm_usage.copy()
    if frame.empty:
        st.info("AI 사용량 데이터가 없습니다.")
        return

    frame["_provider"] = _column(frame, "provider").map(
        lambda value: _text(value, "unknown").lower()
    )
    frame["_model"] = _column(frame, "model_name").map(_model_label)
    for column in ("input_tokens", "output_tokens", "total_tokens"):
        frame[column] = pd.to_numeric(_column(frame, column), errors="coerce").fillna(0)

    directory = _user_directory(data)
    frame["_user"] = _column(frame, "user_id").map(
        lambda value: directory.get(str(value), _text(value, "알 수 없는 사용자"))
    )
    model_options = ["전체 모델", *sorted(frame["_model"].dropna().unique())]
    user_options = ["전체 사용자", *sorted(frame["_user"].dropna().unique())]
    filter_model, filter_user = st.columns([1, 1], gap="small")
    with filter_model:
        selected_model = st.selectbox("모델", model_options, key="usage-model")
    with filter_user:
        selected_user = st.selectbox("사용자", user_options, key="usage-user")

    if selected_model != "전체 모델":
        frame = frame.loc[frame["_model"].eq(selected_model)].copy()
    if selected_user != "전체 사용자":
        frame = frame.loc[frame["_user"].eq(selected_user)].copy()

    error_rate_value = api_health["error_rate"]
    if _missing(error_rate_value) and metrics:
        error_rate_value = metrics.get("error_rate")
    error_rate_text = "-" if _missing(error_rate_value) else f"{float(error_rate_value):.1f}%"
    p95_text = _latency_precise_text(api_health["p95_ms"])
    total_requests = len(frame)
    total_tokens = int(frame["total_tokens"].sum())
    provider_latencies = pd.to_numeric(
        _column(frame, "provider_latency"), errors="coerce"
    ).dropna()
    average_latency = (
        None if provider_latencies.empty else float(provider_latencies.mean())
    )
    if average_latency is None:
        api_latencies = pd.to_numeric(
            _column(data.api_logs, "response_time_ms"), errors="coerce"
        ).dropna()
        if not api_latencies.empty:
            average_latency = float(api_latencies.mean())
    if average_latency is None and metrics:
        fallback_latency = metrics.get("avg_tutor_latency_ms")
        if not _missing(fallback_latency):
            try:
                average_latency = float(fallback_latency)
            except (TypeError, ValueError):
                average_latency = None
    metric_columns = st.columns(5, gap="small")
    for column, label, value in zip(
        metric_columns,
        ("총 토큰 수", "평균 응답시간", "총 요청 수", "오류율", "P95 응답시간"),
        (
            f"{total_tokens:,}",
            _latency_precise_text(average_latency),
            f"{total_requests:,}",
            error_rate_text,
            p95_text,
        ),
    ):
        with column:
            st.metric(label, value)

    left, right = st.columns(2, gap="small")
    with left:
        st.markdown("#### 제공자별 호출량")
        provider_counts = frame.groupby("_provider").size().sort_values(ascending=False)
        provider_counts.index = provider_counts.index.map(provider_label)
        provider_counts = provider_counts.groupby(level=0).sum().sort_values(ascending=False)
        if provider_counts.empty:
            st.info("제공자 사용량이 없습니다.")
        else:
            _render_usage_bar_chart(provider_counts, show_share=True)
    with right:
        st.markdown("#### 일별 토큰 추이")
        frame["_date"] = pd.to_datetime(
            _column(frame, "used_at"), errors="coerce", utc=True
        ).dt.floor("D")
        daily = (
            frame.dropna(subset=["_date"])
            .groupby("_date")["total_tokens"]
            .sum()
            .sort_index()
        )
        if daily.empty:
            st.info("사용 일시 데이터가 없습니다.")
        else:
            _render_daily_token_chart(daily)

    st.markdown("#### 사용량 상세")
    st.caption("토큰은 provider 기록, 응답시간은 provider_latency, 성공 여부는 finish_reason 기준입니다.")
    summary_detail = _usage_summary_frame(frame)
    st.dataframe(
        summary_detail,
        width="stretch",
        hide_index=True,
        column_config={
            "항목": st.column_config.TextColumn("항목", width="medium"),
            "값": st.column_config.TextColumn("값", width="medium"),
            "소스": st.column_config.TextColumn("소스", width="medium"),
        },
    )

    summary = (
        frame.groupby(["_provider", "_model"], as_index=False)
        .agg(
            호출수=("_model", "size"),
            입력토큰=("input_tokens", "sum"),
            출력토큰=("output_tokens", "sum"),
            총토큰=("total_tokens", "sum"),
        )
        .sort_values("호출수", ascending=False)
    )
    summary["_provider"] = summary["_provider"].map(provider_label)
    summary = summary.rename(
        columns={
            "_provider": "제공자",
            "_model": "모델",
            "호출수": "호출 수",
            "입력토큰": "입력 토큰",
            "출력토큰": "출력 토큰",
            "총토큰": "총 토큰",
        }
    )
    for column in ("호출 수", "입력 토큰", "출력 토큰", "총 토큰"):
        summary[column] = summary[column].map(_number_text)
    st.dataframe(
        summary.reset_index(drop=True),
        width="stretch",
        hide_index=True,
        column_config={
            "제공자": st.column_config.TextColumn("제공자", width="small"),
            "모델": st.column_config.TextColumn("모델", width="medium"),
            "호출 수": st.column_config.TextColumn("호출 수", width="small"),
            "입력 토큰": st.column_config.TextColumn("입력 토큰", width="small"),
            "출력 토큰": st.column_config.TextColumn("출력 토큰", width="small"),
            "총 토큰": st.column_config.TextColumn("총 토큰", width="small"),
        },
    )

    st.markdown("#### 상세 요청 내역")
    st.caption("사용자별 모델, 토큰, 응답시간, 성공 여부를 확인할 수 있습니다.")
    detail = _usage_detail_frame(frame, data)
    st.dataframe(
        detail.reset_index(drop=True),
        width="stretch",
        hide_index=True,
        column_config={
            "사용자": st.column_config.TextColumn("사용자", width="medium"),
            "모델": st.column_config.TextColumn("모델", width="medium"),
            "입력 토큰": st.column_config.TextColumn("입력 토큰", width="small"),
            "출력 토큰": st.column_config.TextColumn("출력 토큰", width="small"),
            "총 토큰": st.column_config.TextColumn("총 토큰", width="small"),
            "응답 시간": st.column_config.TextColumn("응답 시간", width="small"),
            "성공 여부": st.column_config.TextColumn("성공 여부", width="small"),
            "일시": st.column_config.TextColumn("일시", width="medium"),
        },
    )


__all__ = [
    "render_api_calls",
    "render_ai_usage",
]
