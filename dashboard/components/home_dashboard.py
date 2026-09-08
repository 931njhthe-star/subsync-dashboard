"""참고 와이어프레임 스타일의 SubSync 홈 대시보드."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape

import pandas as pd
import streamlit as st

from dashboard.analytics.data_loader import DashboardData


def _is_missing(value: object) -> bool:
    """스칼라 값의 결측 여부를 안전하게 판정한다."""

    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _text(value: object, fallback: str = "-") -> str:
    """화면에 표시할 문자열을 안전하게 반환한다."""

    return fallback if _is_missing(value) else str(value)


def _date_label(value: object) -> str:
    """날짜를 와이어프레임 표기 형식으로 변환한다."""

    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return "-" if pd.isna(parsed) else parsed.strftime("%Y.%m.%d")


def _user_labels(data: DashboardData) -> dict[str, str]:
    """user_id를 이메일 또는 짧은 사용자 식별자로 바꾼다."""

    if data.users.empty or "id" not in data.users or "email" not in data.users:
        return {}
    return {
        str(row["id"]): _text(row["email"], "알 수 없는 사용자")
        for _, row in data.users[["id", "email"]].iterrows()
    }


def _recent_users(data: DashboardData) -> list[tuple[str, str, str]]:
    """최근 가입 사용자 5건을 반환한다."""

    frame = data.users.copy()
    if frame.empty:
        return []

    frame["_sort"] = pd.to_datetime(frame.get("created_at"), errors="coerce", utc=True)
    frame = frame.sort_values("_sort", ascending=False, na_position="last").head(5)
    return [
        (
            _text(row.get("email"), _text(row.get("id"), "알 수 없는 사용자")),
            "신규 사용자 가입",
            _date_label(row.get("created_at")),
        )
        for _, row in frame.iterrows()
    ]


def _recent_questions(data: DashboardData) -> list[tuple[str, str, str]]:
    """최근 사용자 질문 5건을 반환한다."""

    frame = data.tutor_messages.copy()
    if not frame.empty and "sender" in frame:
        frame = frame[frame["sender"].astype(str).str.lower().eq("user")].copy()

    if frame.empty and not data.ai_conversations.empty:
        frame = data.ai_conversations.copy()
        frame = frame.rename(columns={"question": "message", "started_at": "created_at"})

    if frame.empty:
        return []

    labels = _user_labels(data)
    frame["_sort"] = pd.to_datetime(frame.get("created_at"), errors="coerce", utc=True)
    frame = frame.sort_values("_sort", ascending=False, na_position="last").head(5)
    return [
        (
            _text(row.get("message"), "질문 내용 없음"),
            labels.get(str(row.get("user_id")), _text(row.get("user_id"), "사용자")),
            _date_label(row.get("created_at")),
        )
        for _, row in frame.iterrows()
    ]


def _render_panel(
    title: str,
    rows: list[tuple[str, str, str]],
    *,
    row_icon: str,
    empty_text: str,
) -> None:
    """최근 활동 패널 하나를 렌더링한다."""

    if rows:
        icon_class = "bubble" if row_icon == "▣" else "avatar"
        rows_markup = "".join(
            f'<div class="subsync-list-row"><div class="subsync-list-icon {icon_class}">{escape(row_icon)}</div><div class="subsync-list-content"><div class="subsync-list-main">{escape(value)}</div><div class="subsync-list-secondary">{escape(detail)}</div></div><div class="subsync-list-date">{escape(when)}</div></div>'
            for value, detail, when in rows
        )
    else:
        rows_markup = f'<div class="subsync-empty">{escape(empty_text)}</div>'

    st.html(
        f"""
        <div class="subsync-home-panel">
            <div class="subsync-panel-head"><h3>{escape(title)}</h3><span>최근 5건</span></div>
            <div class="subsync-list">{rows_markup}</div>
            <div class="subsync-panel-foot">더보기 ›</div>
        </div>
        """
    )


def _latency_label(value: object) -> str:
    """밀리초 단위 평균 응답 시간을 초 단위로 표시한다."""

    if _is_missing(value):
        return "-"
    try:
        milliseconds = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{milliseconds / 1_000:.1f}s"


def _metric_card(label: str, value: str, detail: str, icon: str) -> None:
    """홈 화면 KPI 카드 하나를 렌더링한다."""

    st.markdown(
        f"""
        <div class="subsync-home-kpi">
            <div class="subsync-home-kpi-label">{escape(label)}</div>
            <div class="subsync-home-kpi-value">{escape(value)}</div>
            <div class="subsync-home-kpi-detail">{escape(detail)}</div>
            <div class="subsync-home-kpi-icon">{escape(icon)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home_dashboard(data: DashboardData, metrics: Mapping[str, object]) -> None:
    """참고 이미지의 첫 번째 화면인 관리자용 홈을 표시한다."""

    st.markdown(
        """
        <div class="subsync-page-heading">
            <div class="subsync-heading-number">1</div>
            <div>
                <h1>대시보드 (홈)</h1>
                <p>서비스 주요 현황을 한눈에 확인</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_users = int(metrics.get("total_users", 0) or 0) or len(data.users)
    saved_words = int(metrics.get("saved_words", 0) or 0) or len(data.saved_words)
    kpi_values = [
        ("전체 사용자", f"{total_users:,}", "전체 등록 사용자", "♙"),
        ("AI 질문 수", f"{int(metrics.get('tutor_questions', 0) or 0):,}", "사용자 질문 누적", "▣"),
        ("저장된 단어 수", f"{saved_words:,}", "전체 저장 단어", "▤"),
        ("평균 응답 시간", _latency_label(metrics.get("avg_tutor_latency_ms")), "튜터 응답 평균", "◷"),
    ]
    columns = st.columns(len(kpi_values), gap="small")
    for column, values in zip(columns, kpi_values):
        with column:
            _metric_card(*values)

    st.markdown(
        """
        <div class="subsync-callout">
            <span class="subsync-callout-mark">✦</span>
            <span><strong>운영 요약</strong>　현재 선택한 기간의 사용자·AI 학습 활동을 최신 기록부터 보여줍니다.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="small")
    with left:
        _render_panel(
            "최근 사용자 가입",
            _recent_users(data),
            row_icon="♙",
            empty_text="최근 가입 사용자가 없습니다.",
        )
    with right:
        _render_panel(
            "최근 AI 대화",
            _recent_questions(data),
            row_icon="▣",
            empty_text="최근 AI 질문이 없습니다.",
        )
