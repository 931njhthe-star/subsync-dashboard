"""대시보드 KPI 카드 렌더링."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st


def render_kpi_grid(metrics: Mapping[str, object]) -> None:
    """전달받은 KPI를 4열 카드로 표시한다."""

    cards = [
        ("활성 사용자", f"{metrics['active_users']:,}", "최근 데이터 기준"),
        ("누적 시청", f"{metrics['watch_hours']:,.1f}시간", "영상 시청 시간"),
        ("저장 단어", f"{metrics['saved_words']:,}", "단어장 누적"),
        ("튜터 질문", f"{metrics['tutor_questions']:,}", "사용자 질문 수"),
    ]
    columns = st.columns(len(cards))
    for column, (label, value, caption) in zip(columns, cards):
        with column:
            st.markdown(
                f"""
                <div class="subsync-kpi-card">
                  <div class="subsync-kpi-label">{label}</div>
                  <div class="subsync-kpi-value">{value}</div>
                  <div class="subsync-kpi-caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
