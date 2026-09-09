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


def _load_local_env_file() -> None:
    """개발 환경의 루트 ``.env``를 서버 프로세스에만 주입한다.

    배포 환경에서는 플랫폼 secret store가 우선하며, 이미 존재하는 환경변수는
    덮어쓰지 않는다. 값은 화면·캐시·로그로 보내지 않는다.
    """

    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not name.isidentifier() or name in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        os.environ[name] = value


_load_local_env_file()


def _load_streamlit_secrets() -> None:
    """배포 환경의 Streamlit secrets를 서버 환경변수처럼 사용한다.

    로컬 ``.env``와 이미 주입된 환경변수를 우선하며, secret 값 자체는 화면·로그·
    캐시에 넣지 않는다. Streamlit Cloud의 Advanced settings에 입력한 평문 키도
    기존 데이터 로더가 같은 방식으로 읽을 수 있게 한다.
    """

    secret_names = (
        "SUPABASE_URL",
        "SUPABASE_SECRET_KEY",
        "SUPABASE_KEY",
    )
    for name in secret_names:
        if os.getenv(name, "").strip():
            continue
        try:
            value = st.secrets.get(name, "")
        except Exception:
            # 로컬에서 secrets.toml이 없어도 기본 실행이 중단되지 않아야 한다.
            continue
        if value is not None and str(value).strip():
            os.environ[name] = str(value).strip()


_load_streamlit_secrets()

from dashboard.analytics.data_loader import (
    DashboardDataSourceError,
    filter_by_date,
    load_dashboard_data,
    summarize_metrics,
)
from dashboard.components.admin_pages import (
    render_api_calls,
    render_ai_usage,
)
from dashboard.components.display_labels import page_label
from dashboard.components.home_dashboard import render_home_dashboard
from dashboard.dashboard_api import (
    DEFAULT_DASHBOARD_API_TIMEOUT_SECONDS,
    DEFAULT_DASHBOARD_API_URL,
    DashboardApiError,
    load_dashboard_api_snapshot,
)
from dashboard.styles import inject_styles


st.set_page_config(
    page_title="SubSync 분석 대시보드",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()


PAGE_OPTIONS = ["Dashboard", "AI Usage", "API Calls"]


@st.cache_data(ttl=60, show_spinner=False)
def cached_data(supabase_url: str, supabase_key_configured: bool):
    """Streamlit rerun 사이에 데이터 snapshot을 짧게 캐시한다.

    원문 Supabase 키는 캐시 함수의 인자나 캐시 키에 넣지 않는다. 실제 키는
    ``load_dashboard_data``가 서버 프로세스 환경에서만 읽는다.
    """

    # 설정 여부는 credential 유무가 바뀔 때 캐시 namespace를 구분하는 용도다.
    _ = supabase_key_configured
    return load_dashboard_data(
        "supabase",
        supabase_url=supabase_url or None,
    )


@st.cache_data(ttl=60, show_spinner=False)
def cached_dashboard_api_snapshot(
    start_date_text: str,
    end_date_text: str,
    api_base_url: str,
    timeout_seconds: float,
):
    """선택한 기간의 세 Dashboard API 응답을 짧게 캐시한다.

    API snapshot에는 Supabase secret이 들어가지 않으며, 캐시 키에도 날짜·API 주소·
    timeout만 포함한다. 상세 화면은 이 snapshot을 기존 DashboardData로 변환해
    사용하므로 기존 UI를 제거하지 않는다.
    """

    try:
        start_date = date.fromisoformat(start_date_text)
        end_date = date.fromisoformat(end_date_text)
    except ValueError as exc:
        raise DashboardApiError("조회 날짜 형식이 올바르지 않습니다.") from exc
    return load_dashboard_api_snapshot(
        start_date,
        end_date,
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    )


with st.sidebar:
    st.markdown(
        """
        <div class="subsync-sidebar-brand">
          <div class="subsync-sidebar-name">SubSync</div>
          <div class="subsync-sidebar-desc">사용자와 AI 사용 현황을 한눈에<br/>더 나은 학습 경험을 위해</div>
        </div>
        <div class="subsync-sidebar-label">WORKSPACE</div>
        """,
        unsafe_allow_html=True,
    )
    page = st.radio(
        "화면",
        PAGE_OPTIONS,
        format_func=page_label,
        label_visibility="collapsed",
        key="page",
    )
    st.divider()

source_mode = os.getenv("SUBSYNC_DASHBOARD_SOURCE", "dashboard_api").strip().lower()
legacy_source = source_mode in {"legacy-supabase", "direct-supabase"}
demo_source = source_mode == "demo"

if demo_source or legacy_source:
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key_configured = bool(
        os.getenv("SUPABASE_SECRET_KEY", "") or os.getenv("SUPABASE_KEY", "")
    )
    try:
        if demo_source:
            data = load_dashboard_data("demo")
        else:
            data = cached_data(supabase_url, supabase_key_configured)
    except DashboardDataSourceError as exc:
        st.error(f"Supabase 데이터를 불러오지 못했습니다: {exc}")
        st.stop()

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
else:
    # FastAPI가 정확한 시작일·종료일을 받으므로 API 모드에서는 데이터 조회 전에
    # 최근 90일 범위의 달력만 만든다. 선택된 날짜는 현재 화면 조회에 적용된다.
    max_date = date.today()
    min_date = max_date - timedelta(days=89)


def _period_widget_key(page_name: str) -> str:
    """페이지별 날짜 입력 위젯 키를 만든다."""

    return f"dashboard_period_widget_{page_name.lower().replace(' ', '_')}"


period_values = st.session_state.setdefault("dashboard_period_values", {})
default_period = (max(max_date - timedelta(days=6), min_date), max_date)
if page not in period_values:
    period_values[page] = default_period

with st.sidebar:
    selected_dates = st.date_input(
        f"{page_label(page)} 조회 기간",
        value=period_values[page],
        min_value=min_date,
        max_value=max_date,
        format="YYYY.MM.DD",
        key=_period_widget_key(page),
        help="현재 선택한 화면의 통계·그래프·상세 내역에 적용됩니다.",
    )
    st.caption(f"{page_label(page)} 화면에만 적용 · 다른 화면의 기간은 유지됩니다")

period_values[page] = selected_dates

if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates

if demo_source or legacy_source:
    filtered_data = filter_by_date(data, start_date, end_date)
    metrics = summarize_metrics(filtered_data)
else:
    api_base_url = os.getenv("DASHBOARD_API_URL", DEFAULT_DASHBOARD_API_URL)
    try:
        api_timeout = float(
            os.getenv(
                "DASHBOARD_API_TIMEOUT_SECONDS",
                str(DEFAULT_DASHBOARD_API_TIMEOUT_SECONDS),
            )
        )
    except ValueError:
        api_timeout = DEFAULT_DASHBOARD_API_TIMEOUT_SECONDS
    try:
        snapshot = cached_dashboard_api_snapshot(
            start_date.isoformat(),
            end_date.isoformat(),
            api_base_url,
            api_timeout,
        )
    except DashboardApiError as exc:
        st.error(f"Dashboard API 데이터를 불러오지 못했습니다: {exc}")
        st.info("FastAPI 서버가 https://subsync-backend-4bmh.onrender.com//에서 실행 중인지 확인해 주세요.")
        st.stop()
    filtered_data = snapshot.data
    metrics = snapshot.metrics
date_range_text = f"{start_date:%Y.%m.%d} ~ {end_date:%Y.%m.%d}"

st.markdown(
    f"""
    <div class="subsync-hero">
      <div>
        <div class="subsync-brand-line">SubSync <span class="subsync-brand-badge">Admin Dashboard</span></div>
        <div class="subsync-eyebrow">SubSync / 분석</div>
        <div class="subsync-title">학습 흐름을 한눈에 확인하세요.</div>
        <div class="subsync-subtitle">영상 시청, 단어 학습, 비디오 튜터 품질을 하나의 화면에서 확인합니다.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f'''
    <div class="subsync-filter-banner">
      <strong>{page_label(page)} 조회 기간</strong><span>{date_range_text}</span>
      <em>선택한 기간 기준으로 집계됨</em>
    </div>
    ''',
    unsafe_allow_html=True,
)

if page == "Dashboard":
    render_home_dashboard(filtered_data, metrics)
elif page == "API Calls":
    render_api_calls(filtered_data)
else:
    render_ai_usage(filtered_data, metrics)

st.divider()
st.caption("SubSync 관리자 대시보드 · FastAPI Dashboard API를 통해 연결된 운영 데이터")
