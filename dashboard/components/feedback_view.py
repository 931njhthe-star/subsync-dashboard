"""튜터 피드백 품질 컴포넌트."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.display_labels import feedback_display_frame, provider_display_frame


def render_feedback(feedback: pd.DataFrame, providers: pd.DataFrame) -> None:
    """튜터 만족도와 제공자별 지연시간을 표시한다."""

    if feedback.empty:
        st.info("아직 튜터 평가 데이터가 없습니다.")
    else:
        feedback_display = feedback_display_frame(feedback)
        chart = feedback_display.set_index("평가")["응답 수"]
        st.bar_chart(chart, color="#3f7ff5")
        st.dataframe(feedback_display, width="stretch", hide_index=True)

    st.markdown("#### 제공자 성능")
    if providers.empty:
        st.info("제공자 사용량 데이터가 없습니다.")
    else:
        st.dataframe(provider_display_frame(providers), width="stretch", hide_index=True)
