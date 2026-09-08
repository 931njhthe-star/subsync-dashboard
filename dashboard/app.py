"""SubSync Streamlit 운영·분석 대시보드 진입점."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
import sys

import streamlit as st

# Streamlit이 파일 경로로 실행될 때는 dashboard 폴더만 sys.path에 들어갈 수
# 있으므로, 상위 프로젝트 루트를 명시적으로 import 경로에 등록한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.analytics.ai_quality_eval import feedback_breakdown, provider_summary
from dashboard.analytics.data_loader import (
    DashboardDataSourceError,
    filter_by_date,
    load_dashboard_data,
    summarize_metrics,
)
from dashboard.analytics.user_patterns import daily_activity, top_words, video_summary
from dashboard.components.display_labels import page_label, source_label, translate_frame_columns
from dashboard.components.feedback_view import render_feedback
from dashboard.components.kpi_metrics import render_kpi_grid
from dashboard.components.realtime_logs import render_logs
from dashboard.styles import inject_styles


st.set_page_config(
    page_title="SubSync 분석 대시보드",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()


def _source_label(source: str) -> str:
    """내부 source 값을 사용자용 label로 변환한다."""

    return source_label(source)


@st.cache_data(ttl=60, show_spinner=False)
def cached_data(source: str, json_path: str, supabase_url: str, supabase_key_configured: bool):
    """Streamlit rerun 사이에 데이터 snapshot을 짧게 캐시한다.

    원문 Supabase 키는 캐시 함수의 인자나 캐시 키에 넣지 않는다. 실제 키는
    ``load_dashboard_data``가 서버 프로세스 환경에서만 읽는다.
    """

    # 설정 여부는 credential 유무가 바뀔 때 demo와 live 캐시 namespace를 구분하는 용도다.
    _ = supabase_key_configured
    return load_dashboard_data(
        source,
        json_path=json_path or None,
        supabase_url=supabase_url or None,
    )


with st.sidebar:
    st.markdown("### ◈ SubSync")
    st.caption("학습 분석 운영 화면")
    st.divider()
    page = st.radio(
        "화면",
        ["Overview", "Learning Activity", "Tutor Quality", "System Logs"],
        format_func=page_label,
        label_visibility="collapsed",
    )
    st.divider()
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key_configured = bool(os.getenv("SUPABASE_KEY", ""))
    source_options = ["demo", "auto", "json", "supabase"]
    configured_source = os.getenv("SUBSYNC_DASHBOARD_SOURCE", "").strip().lower()
    if configured_source not in source_options:
        configured_source = "auto" if supabase_url and supabase_key_configured else "demo"
    source = st.selectbox(
        "데이터 원천",
        source_options,
        index=source_options.index(configured_source),
        format_func=source_label,
    )
    json_path = st.text_input("자료 파일 경로", value="", disabled=source not in {"json", "demo"})
    if source in {"auto", "supabase"}:
        st.caption("수파베이스 접속 정보는 대시보드 서버 환경변수에서 읽습니다.")
    if configured_source == "demo" and not (supabase_url and supabase_key_configured):
        st.caption("기본 모드는 로컬 샘플 자료입니다.")

try:
    data = cached_data(source, json_path, supabase_url, supabase_key_configured)
    source_error = None
except DashboardDataSourceError as exc:
    source_error = str(exc)
    data = cached_data("demo", "", "", False)

if source_error:
    st.warning(f"외부 데이터 원천을 사용할 수 없어 샘플 데이터로 표시합니다: {source_error}")

available_dates = []
for frame, column in [
    (data.video_history, "updated_at"),
    (data.click_events, "created_at"),
    (data.tutor_messages, "created_at"),
    (data.saved_words, "created_at"),
    (data.login_history, "login_at"),
    (data.ai_conversations, "started_at"),
    (data.llm_usage, "used_at"),
    (data.api_logs, "requested_at"),
]:
    if not frame.empty and column in frame and frame[column].notna().any():
        available_dates.extend(frame[column].dropna().dt.date.tolist())

max_date = max(available_dates) if available_dates else date.today()
min_date = min(available_dates) if available_dates else max_date - timedelta(days=30)
with st.sidebar:
    selected_dates = st.date_input(
        "조회 기간",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates
filtered_data = filter_by_date(data, start_date, end_date)
metrics = summarize_metrics(filtered_data)

st.markdown(
    f"""
    <div class="subsync-hero">
      <div>
        <div class="subsync-eyebrow">SubSync / 분석</div>
        <div class="subsync-title">학습 흐름을 한눈에 확인하세요.</div>
        <div class="subsync-subtitle">영상 시청, 단어 학습, 비디오 튜터 품질을 하나의 화면에서 확인합니다.</div>
      </div>
      <div class="subsync-source">{_source_label(data.source)}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if page == "Overview":
    render_kpi_grid(metrics)
    st.markdown("### 활동 개요")
    activity = daily_activity(filtered_data)
    if activity.empty:
        st.info("선택한 기간에 활동 데이터가 없습니다.")
    else:
        chart = translate_frame_columns(
            activity.set_index("date")[["watch_hours", "word_clicks", "tutor_questions"]],
            "activity",
        )
        st.area_chart(chart, color=["#3f7ff5", "#66a0ff", "#93c5fd"])
    left, right = st.columns(2)
    with left:
        st.markdown("#### 자주 학습한 단어")
        st.dataframe(translate_frame_columns(top_words(filtered_data), "words"), width="stretch", hide_index=True)
    with right:
        st.markdown("#### 많이 본 영상")
        st.dataframe(translate_frame_columns(video_summary(filtered_data), "videos"), width="stretch", hide_index=True)

elif page == "Learning Activity":
    st.markdown("### 학습 활동")
    st.caption("저장 단어와 클릭 학습, 영상별 누적 시청시간을 분석합니다.")
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### 단어 학습 순위")
        words = top_words(filtered_data, limit=20)
        if words.empty:
            st.info("단어 활동 데이터가 없습니다.")
        else:
            word_chart = translate_frame_columns(words.set_index("word")[["clicks", "saves"]], "words")
            st.bar_chart(word_chart, color=["#3f7ff5", "#93c5fd"])
            st.dataframe(translate_frame_columns(words, "words"), width="stretch", hide_index=True)
    with right:
        st.markdown("#### 영상별 시청시간")
        videos = video_summary(filtered_data, limit=20)
        if videos.empty:
            st.info("시청 기록이 없습니다.")
        else:
            video_chart = translate_frame_columns(videos.set_index("video_title")[["watch_hours"]], "videos")
            st.bar_chart(video_chart, color="#3f7ff5")
            st.dataframe(translate_frame_columns(videos, "videos"), width="stretch", hide_index=True)

elif page == "Tutor Quality":
    st.markdown("### 튜터 품질")
    st.caption("튜터 만족도, 제공자·모델 사용량, 전체 튜터 API 응답시간을 확인합니다.")
    quality_left, quality_right = st.columns(2)
    with quality_left:
        st.metric("도움됨 비율", "-" if metrics["tutor_helpful_rate"] is None else f"{metrics['tutor_helpful_rate']:.1f}%")
        st.metric("평균 응답시간", "-" if metrics["avg_tutor_latency_ms"] is None else f"{metrics['avg_tutor_latency_ms']:.0f} 밀리초")
    with quality_right:
        st.metric("오류율", "-" if metrics["error_rate"] is None else f"{metrics['error_rate']:.1f}%")
        st.metric("질문 수", f"{metrics['tutor_questions']:,}")
    render_feedback(feedback_breakdown(filtered_data), provider_summary(filtered_data))

else:
    st.markdown("### 시스템 로그")
    st.caption("백엔드 API 요청의 상태 코드·응답시간·오류를 확인합니다.")
    render_logs(filtered_data.system_logs)

st.divider()
st.caption("SubSync 분석 대시보드 · 안전한 샘플 분석 화면 · 실제 자료 연결은 환경변수로 전환")
