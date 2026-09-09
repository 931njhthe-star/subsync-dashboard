"""참고 와이어프레임 스타일의 SubSync 홈 대시보드."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape

import pandas as pd
import streamlit as st

from dashboard.analytics.data_loader import DashboardData
from dashboard.components.display_labels import provider_label


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


def _number_label(value: object) -> str:
    """차트 눈금에 사용할 천 단위 구분 문자열을 반환한다."""

    if _is_missing(value):
        return "-"
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "-"


def _model_label(value: object) -> str:
    """AI 모델 식별자를 홈 화면용 짧은 이름으로 바꾼다."""

    raw = _text(value, "알 수 없는 모델").strip()
    known = {
        "gemini-3.6-flash": "Gemini 3.6 Flash",
        "gemini:3.6-flash": "Gemini 3.6 Flash",
        "openai/gpt-oss-20b": "GPT-OSS 20B",
        "gpt-oss-20b": "GPT-OSS 20B",
    }.get(raw.lower())
    if known:
        return known
    pretty = raw.replace("/", " ").replace(":", " ").replace("_", " ").replace("-", " ")
    return " ".join(
        word.upper() if word.lower() in {"ai", "api", "gpt", "oss"} else word.capitalize()
        for word in pretty.split()
    )


def _latency_precise_label(value: object) -> str:
    """밀리초 값을 관리자 화면에서 읽기 쉬운 형태로 표시한다."""

    if _is_missing(value):
        return "-"
    try:
        milliseconds = float(value)
    except (TypeError, ValueError):
        return "-"
    if milliseconds < 0:
        return "-"
    return f"{milliseconds / 1_000:.2f}s"


def _recent_ai_activity(data: DashboardData) -> pd.DataFrame:
    """최근 llm_usage 기록을 홈 화면의 AI 활동 표로 만든다."""

    frame = data.llm_usage.copy()
    if frame.empty:
        return pd.DataFrame(columns=["사용자", "모델", "토큰", "응답시간", "일시"])

    labels = _user_labels(data)
    frame["_sort"] = pd.to_datetime(
        frame.get("used_at"), errors="coerce", utc=True
    )
    frame = frame.sort_values("_sort", ascending=False, na_position="last").head(5)
    totals = pd.to_numeric(frame.get("total_tokens"), errors="coerce")
    return pd.DataFrame(
        {
            "사용자": frame.get("user_id", pd.Series(index=frame.index)).map(
                lambda value: labels.get(str(value), _text(value, "사용자"))
            ),
            "모델": frame.get("model_name", pd.Series(index=frame.index)).map(_model_label),
            "토큰": totals.map(_number_label),
            "응답시간": frame.get(
                "provider_latency", pd.Series(index=frame.index)
            ).map(_latency_precise_label),
            "일시": frame["_sort"].map(_date_label),
        },
        index=frame.index,
    ).reset_index(drop=True)


def _render_daily_ai_chart(data: DashboardData) -> None:
    """날짜 라벨이 회전하지 않는 일별 AI 호출 추이 차트를 표시한다."""

    usage = data.llm_usage.copy()
    if usage.empty:
        st.info("일별 AI 사용량 데이터가 없습니다.")
        return

    timestamps = pd.to_datetime(usage.get("used_at"), errors="coerce", utc=True)
    daily = (
        usage.assign(_date=timestamps.dt.floor("D"))
        .dropna(subset=["_date"])
        .groupby("_date")
        .size()
        .sort_index()
    )
    if daily.empty:
        st.info("일별 AI 사용량 데이터가 없습니다.")
        return

    chart_width = 720
    chart_height = 250
    left, right, top, bottom = 54, 16, 18, 48
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
        grid_parts.append(
            f'<line class="subsync-svg-grid" x1="{left}" y1="{y:.1f}" x2="{chart_width - right}" y2="{y:.1f}"/>'
            f'<text class="subsync-svg-y-label" x="{left - 9}" y="{y + 4:.1f}" text-anchor="end">{escape(_number_label(y_max * ratio))}</text>'
        )
    path = " ".join(
        f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}"
        for index, (x, y) in enumerate(zip(x_positions, y_positions))
    )
    points = []
    for label, x, y, value in zip(labels, x_positions, y_positions, values):
        points.append(
            f'<circle class="subsync-svg-point" cx="{x:.1f}" cy="{y:.1f}" r="4"><title>{escape(label)}: {_number_label(value)}회</title></circle>'
            f'<text class="subsync-svg-x-label" x="{x:.1f}" y="{chart_height - 25}" text-anchor="middle">{escape(label)}</text>'
        )
    st.markdown(
        f'''
        <div class="subsync-daily-token-chart subsync-home-daily-chart">
          <svg viewBox="0 0 {chart_width} {chart_height}" role="img" aria-label="일별 AI 사용량">
            {"".join(grid_parts)}
            <path class="subsync-svg-line" d="{path}"/>
            {"".join(points)}
            <text class="subsync-svg-axis-title" x="{chart_width / 2}" y="{chart_height - 4}" text-anchor="middle">일</text>
          </svg>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def _provider_note(data: DashboardData) -> str:
    """현재 조회 기간의 제공자별 호출 비중을 운영 메모로 요약한다."""

    usage = data.llm_usage
    if usage.empty or "provider" not in usage:
        return "사용량 데이터가 없어 제공자 비중을 계산할 수 없습니다."
    providers = usage["provider"].fillna("unknown").astype(str).map(provider_label)
    counts = providers.value_counts()
    total = max(int(counts.sum()), 1)
    return " · ".join(
        f"{label} {int(count / total * 100)}%" for label, count in counts.items()
    )


def render_home_dashboard(data: DashboardData, metrics: Mapping[str, object]) -> None:
    """첨부 와이어프레임의 첫 번째 화면인 Dashboard Home을 표시한다."""

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
    ai_requests = int(metrics.get("tutor_questions", 0) or 0)
    if not ai_requests:
        ai_requests = len(data.llm_usage)
    kpi_values = [
        ("조회 기간 사용자", f"{total_users:,}", "선택 기간 내 가입자", "♙"),
        ("AI 호출", f"{ai_requests:,}", "선택 기간의 튜터 요청", "▣"),
    ]
    columns = st.columns(2, gap="small")
    for column, values in zip(columns, kpi_values):
        with column:
            _metric_card(*values)

    st.markdown("#### 일별 AI 사용량")
    _render_daily_ai_chart(data)

    st.markdown("#### 최근 AI 활동")
    recent_ai_activity = _recent_ai_activity(data)
    if recent_ai_activity.empty:
        st.info("최근 AI 활동 데이터가 없습니다.")
    else:
        st.dataframe(
            recent_ai_activity,
            width="stretch",
            hide_index=True,
            column_config={
                "사용자": st.column_config.TextColumn("사용자", width="medium"),
                "모델": st.column_config.TextColumn("모델", width="medium"),
                "토큰": st.column_config.TextColumn("토큰", width="small"),
                "응답시간": st.column_config.TextColumn("응답시간", width="small"),
                "일시": st.column_config.TextColumn("일시", width="medium"),
            },
        )

    st.markdown(
        f'''
        <div class="subsync-callout">
            <span class="subsync-callout-mark">✦</span>
            <span><strong>운영 메모</strong>　현재 조회 기간의 제공자 호출 비중: {escape(_provider_note(data))}</span>
        </div>
        ''',
        unsafe_allow_html=True,
    )
