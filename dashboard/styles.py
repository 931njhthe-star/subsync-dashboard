"""SubSync 대시보드 전용 스타일."""

from __future__ import annotations

import streamlit as st


DASHBOARD_CSS = """
<style>
:root { --subsync-blue: #3f7ff5; --subsync-ink: #0b1220; }
[data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at 10% 0%, rgba(63,127,245,.13), transparent 32%), #09111f;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0d192b 0%, #09111f 100%);
  border-right: 1px solid rgba(148,163,184,.14);
}
.block-container { max-width: 1480px; padding-top: 2.2rem; padding-bottom: 3rem; }
.subsync-hero {
  display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem;
  padding: 1.35rem 1.5rem; margin-bottom: 1.25rem;
  border: 1px solid rgba(148,163,184,.16); border-radius: 24px;
  background: linear-gradient(135deg, rgba(20,35,59,.88), rgba(13,24,42,.68));
  box-shadow: 0 22px 60px rgba(0,0,0,.2); backdrop-filter: blur(18px);
}
.subsync-eyebrow { color: #7fa8ff; font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 700; }
.subsync-title { color: #f8fafc; font-size: 2rem; line-height: 1.1; font-weight: 800; margin-top: .35rem; }
.subsync-subtitle { color: #94a3b8; margin-top: .45rem; font-size: .92rem; }
.subsync-source { color: #bfdbfe; background: rgba(63,127,245,.14); border: 1px solid rgba(96,165,250,.28); border-radius: 999px; padding: .45rem .72rem; font-size: .78rem; white-space: nowrap; }
.subsync-kpi-card {
  min-height: 126px; padding: 1.1rem 1.2rem; border-radius: 20px;
  border: 1px solid rgba(148,163,184,.16); background: rgba(15,28,48,.78);
  box-shadow: 0 16px 36px rgba(0,0,0,.16); backdrop-filter: blur(16px);
}
.subsync-kpi-label { color: #94a3b8; font-size: .8rem; font-weight: 600; }
.subsync-kpi-value { color: #f8fafc; font-size: 1.85rem; font-weight: 800; margin: .6rem 0 .25rem; }
.subsync-kpi-caption { color: #64748b; font-size: .72rem; }
[data-testid="stMetricValue"] { color: #f8fafc; }
[data-testid="stDataFrame"] { border: 1px solid rgba(148,163,184,.14); border-radius: 16px; overflow: hidden; }
.stButton > button, .stDownloadButton > button { border-radius: 10px; border: 1px solid rgba(96,165,250,.28); }
</style>
"""


def inject_styles() -> None:
    """대시보드 화면에 SubSync 스타일을 주입한다."""

    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
