"""시스템 로그 필터·표시 컴포넌트."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.display_labels import (
    event_type_label,
    severity_label,
    system_log_display_frame,
)


def render_logs(logs: pd.DataFrame) -> None:
    """severity와 event type을 필터링한 로그 표를 표시한다."""

    if logs.empty:
        st.info("선택한 기간에 시스템 로그가 없습니다.")
        return

    frame = logs.copy()
    severities = sorted(frame["severity"].astype(str).replace("", "info").unique())
    event_types = sorted(frame["event_type"].astype(str).unique())
    col1, col2 = st.columns(2)
    with col1:
        selected_severity = st.multiselect(
            "심각도",
            severities,
            default=severities,
            format_func=severity_label,
        )
    with col2:
        selected_events = st.multiselect(
            "이벤트 유형",
            event_types,
            default=event_types,
            format_func=event_type_label,
        )

    filtered = frame[
        frame["severity"].astype(str).replace("", "info").isin(selected_severity)
        & frame["event_type"].astype(str).isin(selected_events)
    ].copy()
    columns = ["created_at", "severity", "event_type", "status_code", "latency_ms", "message"]
    display = system_log_display_frame(filtered[columns])
    st.dataframe(display, width="stretch", hide_index=True)
    st.download_button(
        "로그 파일 내려받기",
        data=display.to_csv(index=False).encode("utf-8-sig"),
        file_name="subsync-시스템-로그.csv",
        mime="text/csv",
    )
