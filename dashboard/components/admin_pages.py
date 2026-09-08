"""와이어프레임의 관리자용 목록·사용량 화면."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape

import pandas as pd
import streamlit as st

from dashboard.analytics.data_loader import DashboardData
from dashboard.components.display_labels import provider_label, rating_label


PAGE_COLUMNS = ["사용자", "질문 내용", "모델", "응답 시간", "일시", "평가"]


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


def _latency_text(value: object) -> str:
    """밀리초 응답시간을 초 단위로 표시한다."""

    if _missing(value):
        return "-"
    try:
        return f"{float(value) / 1_000:.1f}s"
    except (TypeError, ValueError):
        return "-"


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
    """사용자 검색·상태 필터·CSV 내보내기 화면을 표시한다."""

    _heading(2, "사용자 관리", "사용자 목록, 검색, 상태 관리")
    frame = data.users.copy()
    if frame.empty:
        st.info("사용자 데이터가 없습니다.")
        return

    frame["_name"] = [
        _user_name(email, account)
        for email, account in zip(_column(frame, "email"), _column(frame, "google_account_id"))
    ]
    frame["_email"] = _column(frame, "email").map(lambda value: _text(value))
    frame["_status"] = _column(frame, "is_active").map(
        lambda value: "활성" if not _missing(value) and bool(value) else "비활성"
    )

    search_col, status_col, export_col = st.columns([1.6, 0.8, 0.8], gap="small")
    with search_col:
        query = st.text_input("이름, 이메일로 검색", placeholder="검색어 입력", key="users-search")
    with status_col:
        status = st.selectbox("상태", ["전체 상태", "활성", "비활성"], key="users-status")

    filtered = frame.loc[_search_mask(frame, ["_name", "_email", "id"], query)].copy()
    if status != "전체 상태":
        filtered = filtered.loc[filtered["_status"].eq(status)].copy()

    display = pd.DataFrame(
        {
            "이름": filtered["_name"],
            "이메일": filtered["_email"],
            "가입일": _column(filtered, "created_at").map(_date_text),
            "최근 접속": _column(filtered, "last_login_at").map(_date_text),
            "상태": filtered["_status"],
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
                    "모델": _text(_first_value(tutor_rows, "model")),
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
                "모델": _text(model),
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


def render_ai_usage(data: DashboardData) -> None:
    """모델별 호출·토큰 사용량과 일별 추이를 표시한다."""

    _heading(5, "AI 사용량", "모델별 사용 현황 및 토큰 모니터링")
    frame = data.llm_usage.copy()
    if frame.empty:
        st.info("AI 사용량 데이터가 없습니다.")
        return

    frame["_provider"] = _column(frame, "provider").map(
        lambda value: _text(value, "unknown").lower()
    )
    frame["_model"] = _column(frame, "model_name").map(lambda value: _text(value, "unknown"))
    for column in ("input_tokens", "output_tokens", "total_tokens"):
        frame[column] = pd.to_numeric(_column(frame, column), errors="coerce").fillna(0)

    provider_options = ["전체 모델", *sorted(frame["_provider"].unique())]
    selected_provider = st.selectbox(
        "모델 필터",
        provider_options,
        format_func=lambda value: "전체 모델" if value == "전체 모델" else provider_label(value),
        key="usage-provider",
    )
    if selected_provider != "전체 모델":
        frame = frame.loc[frame["_provider"].eq(selected_provider)].copy()

    total_requests = len(frame)
    total_tokens = int(frame["total_tokens"].sum())
    input_tokens = int(frame["input_tokens"].sum())
    output_tokens = int(frame["output_tokens"].sum())
    metrics = st.columns(4, gap="small")
    for column, label, value in zip(
        metrics,
        ("총 요청 수", "총 토큰 수", "입력 토큰", "출력 토큰"),
        (f"{total_requests:,}", f"{total_tokens:,}", f"{input_tokens:,}", f"{output_tokens:,}"),
    ):
        with column:
            st.metric(label, value)

    left, right = st.columns(2, gap="small")
    with left:
        st.markdown("#### 모델별 사용 비중")
        model_counts = frame.groupby("_model").size().sort_values(ascending=False).rename("호출 수")
        if model_counts.empty:
            st.info("모델 사용량이 없습니다.")
        else:
            st.bar_chart(model_counts, color="#3f6fa8")
    with right:
        st.markdown("#### 일별 토큰 추이")
        frame["_date"] = pd.to_datetime(
            _column(frame, "used_at"), errors="coerce", utc=True
        ).dt.strftime("%Y.%m.%d")
        daily = frame.dropna(subset=["_date"]).groupby("_date")["total_tokens"].sum().sort_index()
        if daily.empty:
            st.info("사용 일시 데이터가 없습니다.")
        else:
            st.line_chart(daily, color="#3f6fa8")

    summary = (
        frame.groupby(["_provider", "_model"], as_index=False)
        .agg(
            호출수=("id", "size"),
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
        summary[column] = summary[column].map(lambda value: f"{int(value):,}")
    st.dataframe(summary.reset_index(drop=True), width="stretch", hide_index=True)


__all__ = [
    "render_ai_usage",
    "render_conversation_history",
    "render_user_management",
    "render_word_management",
]
