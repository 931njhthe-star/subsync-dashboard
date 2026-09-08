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
<style>
/* Wireframe-inspired light admin theme. The original selectors remain above
   so the existing analytics pages keep their component contracts. */
:root {
  --subsync-ink: #1f2d3d;
  --subsync-muted: #718096;
  --subsync-line: #dbe3ec;
  --subsync-line-soft: #e9eef4;
  --subsync-blue: #3f6fa8;
  --subsync-blue-soft: #e7f0fb;
  --subsync-canvas: #f7f9fc;
}
html, body, [class*="css"] { font-family: Inter, "Noto Sans KR", "Malgun Gothic", sans-serif; }
[data-testid="stAppViewContainer"] { background: var(--subsync-canvas); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }
section[data-testid="stSidebar"] { background: #f3f6fa; border-right: 1px solid var(--subsync-line-soft); }
section[data-testid="stSidebar"] > div:first-child { padding: 1.5rem 1rem 1.25rem; }
.block-container { max-width: 1480px; padding: 1.75rem 2.25rem 3rem; }
.subsync-sidebar-brand { border-bottom: 1px solid #e0e7ef; margin-bottom: 1.1rem; padding: .45rem .75rem 1.15rem; }
.subsync-sidebar-name { color: #172438 !important; font-size: 1.35rem; font-weight: 800; letter-spacing: -.04em; }
.subsync-sidebar-desc { color: #66758a !important; font-size: .7rem; line-height: 1.55; margin-top: .2rem; }
.subsync-sidebar-label { color: #68788d !important; font-size: .62rem; font-weight: 700; letter-spacing: .13em; padding: 0 .75rem .55rem; }
.subsync-sidebar-footer { border-top: 1px solid #e0e7ef; color: #66758a !important; font-size: .68rem; line-height: 1.7; margin: 1.5rem .75rem 0; padding-top: 1rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stDateInput label { color: #66758a !important; }

div[role="radiogroup"] { gap: .3rem; }
div[role="radiogroup"] > label { background: transparent; border-radius: .55rem; color: #526174; cursor: pointer; margin: 0; padding: .6rem .75rem; }
div[role="radiogroup"] > label p { color: #526174 !important; }
div[role="radiogroup"] > label:hover { background: #e9eff7; color: #294e78; }
div[role="radiogroup"] > label:has(input:checked) { background: #dce9f8; color: #28558b; font-weight: 700; }
div[role="radiogroup"] > label:has(input:checked) p { color: #28558b !important; }
div[role="radiogroup"] > label > div:first-child { display: none; }

.subsync-hero { align-items: flex-end; background: #fff; border: 1px solid var(--subsync-line); border-radius: .75rem; box-shadow: 0 7px 18px rgba(40, 67, 96, .05); display: flex; gap: 1rem; justify-content: space-between; margin-bottom: 1.4rem; padding: 1.15rem 1.35rem; }
.subsync-brand-line { align-items: center; color: #1b2a3e; display: flex; font-size: 1.9rem; font-weight: 800; gap: .7rem; letter-spacing: -.07em; line-height: 1; }
.subsync-brand-badge { background: var(--subsync-blue-soft); border: 1px solid #d7e5f8; border-radius: .45rem; color: #315989; font-size: .76rem; font-weight: 600; letter-spacing: 0; padding: .38rem .65rem; }
.subsync-eyebrow { color: var(--subsync-blue); font-size: .63rem; font-weight: 700; letter-spacing: .13em; margin-top: .7rem; text-transform: uppercase; }
.subsync-title { color: var(--subsync-ink); font-size: 1.45rem; font-weight: 800; letter-spacing: -.04em; line-height: 1.15; margin-top: .35rem; }
.subsync-subtitle { color: #748296; font-size: .78rem; margin-top: .42rem; }

.subsync-page-heading { align-items: center; display: flex; gap: .7rem; margin: .1rem 0 .85rem; }
.subsync-heading-number { align-items: center; background: #353d46; border-radius: 50%; color: #fff; display: flex; flex: 0 0 2rem; font-size: 1rem; font-weight: 700; height: 2rem; justify-content: center; width: 2rem; }
.subsync-page-heading h1 { color: var(--subsync-ink); font-size: 1.25rem; margin: 0; }
.subsync-page-heading p { color: #788596; font-size: .75rem; margin: .2rem 0 0; }

.subsync-home-kpi { background: #fff; border: 1px solid var(--subsync-line); border-radius: .6rem; min-height: 7.1rem; padding: .9rem 1rem .8rem; position: relative; }
.subsync-home-kpi-label { color: #6f7e90; font-size: .68rem; }
.subsync-home-kpi-value { color: #182536; font-size: 1.42rem; font-weight: 800; margin-top: .6rem; }
.subsync-home-kpi-detail { color: #8a96a5; font-size: .62rem; margin-top: .35rem; }
.subsync-home-kpi-icon { align-items: center; background: #eff5fc; border-radius: .45rem; bottom: .75rem; color: var(--subsync-blue); display: flex; font-size: 1.15rem; height: 2rem; justify-content: center; position: absolute; right: .7rem; width: 2rem; }
.subsync-callout { align-items: center; background: #edf4fd; border: 1px solid #d9e7f8; border-radius: .6rem; color: #46678e; display: flex; font-size: .72rem; gap: .55rem; margin: .9rem 0 1rem; padding: .65rem .8rem; }
.subsync-callout strong { color: #2e5c91; }
.subsync-callout-mark { color: #3f6fa8; font-size: 1rem; }

.subsync-health-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .6rem; margin: .8rem 0 1rem; }
.subsync-health-card { background: #fff; border: 1px solid var(--subsync-line); border-radius: .6rem; padding: .75rem .85rem; }
.subsync-health-card.ok { border-left: 3px solid #4f9d78; }
.subsync-health-card.warn { border-left: 3px solid #d99b3c; }
.subsync-health-card.neutral { border-left: 3px solid #8aa0b8; }
.subsync-health-label { color: #68788d; font-size: .68rem; }
.subsync-health-value { color: #182536; font-size: 1rem; font-weight: 800; margin-top: .35rem; }
.subsync-health-detail { color: #8794a5; font-size: .62rem; margin-top: .2rem; }
@media (max-width: 800px) { .subsync-health-grid { grid-template-columns: 1fr; } }
.subsync-health-note { align-items: flex-start; border: 1px solid; border-radius: .6rem; display: flex; font-size: .72rem; gap: .55rem; line-height: 1.55; margin: .8rem 0 1rem; padding: .65rem .8rem; }
.subsync-health-note strong { font-weight: 800; }
.subsync-health-note.warning { background: #fff7e8; border-color: #f0d49b; color: #7d5b18; }
.subsync-health-note.warning strong, .subsync-health-note.warning .subsync-callout-mark { color: #a46b0c; }
.subsync-health-note.ok { background: #eff9f3; border-color: #cee9d8; color: #48745a; }
.subsync-health-note.ok strong, .subsync-health-note.ok .subsync-callout-mark { color: #39805a; }
.subsync-health-note.neutral { background: #f1f5f9; border-color: #d7e0ea; color: #66758a; }
.subsync-health-note.neutral strong, .subsync-health-note.neutral .subsync-callout-mark { color: #506b88; }
.subsync-latest-status { align-items: center; background: #edf4fd; border: 1px solid #d9e7f8; border-radius: .55rem; color: #46678e; display: flex; gap: .6rem; margin: .45rem 0 .7rem; padding: .55rem .75rem; }
.subsync-latest-status strong { color: #2e5c91; font-size: .72rem; }
.subsync-latest-status span { background: #fff; border: 1px solid #c9dced; border-radius: .35rem; color: #1f4f83; font-size: .78rem; font-weight: 800; padding: .18rem .45rem; }
.subsync-model-usage-chart, .subsync-daily-token-chart { background: #fff; border: 1px solid var(--subsync-line-soft); border-radius: .45rem; min-height: 16rem; padding: 1rem .85rem .55rem; }
.subsync-model-chart-rows { display: flex; flex-direction: column; gap: 1.15rem; padding: 1.2rem 0 1rem; }
.subsync-model-chart-row { align-items: center; display: grid; gap: .65rem; grid-template-columns: minmax(8.5rem, 11rem) minmax(0, 1fr) minmax(5.5rem, 7rem); }
.subsync-model-chart-label { color: #52677e; font-size: .74rem; line-height: 1.25; overflow-wrap: anywhere; }
.subsync-model-chart-track { background: #eef2f6; border-radius: .25rem; height: 2.1rem; overflow: hidden; }
.subsync-model-chart-bar { background: #4679b2; border-radius: .25rem; height: 100%; min-width: .25rem; }
.subsync-model-chart-value { color: #425b75; font-size: .68rem; font-weight: 700; text-align: right; white-space: nowrap; }
.subsync-chart-axis-title { border-top: 1px solid #dce5ee; color: #6f7e90; font-size: .7rem; margin: 0 7.7rem 0 11.2rem; padding-top: .45rem; text-align: center; }
.subsync-daily-token-chart svg { display: block; height: 16rem; overflow: visible; width: 100%; }
.subsync-svg-grid { stroke: #e1e8f0; stroke-width: 1; }
.subsync-svg-y-label, .subsync-svg-x-label { fill: #718096; font-family: Inter, "Noto Sans KR", "Malgun Gothic", sans-serif; font-size: 12px; }
.subsync-svg-axis-title { fill: #6f7e90; font-family: Inter, "Noto Sans KR", "Malgun Gothic", sans-serif; font-size: 12px; }
.subsync-svg-line { fill: none; stroke: #3f6fa8; stroke-linecap: round; stroke-linejoin: round; stroke-width: 3; }
.subsync-svg-point { fill: #3f6fa8; stroke: #fff; stroke-width: 2; }
@media (max-width: 800px) { .subsync-model-chart-row { grid-template-columns: minmax(6.5rem, 8rem) minmax(0, 1fr) minmax(5rem, 6.5rem); } .subsync-chart-axis-title { margin-left: 8.2rem; margin-right: 7.2rem; } }

.subsync-home-panel { background: #fff; border: 1px solid var(--subsync-line); border-radius: .65rem; overflow: hidden; }
.subsync-panel-head { align-items: center; border-bottom: 1px solid var(--subsync-line-soft); display: flex; justify-content: space-between; padding: .75rem .85rem .65rem; }
.subsync-panel-head h3 { color: #1f2c3b; font-size: .82rem; margin: 0; }
.subsync-panel-head span { color: #97a2b0; font-size: .62rem; }
.subsync-list-row { align-items: center; border-bottom: 1px solid #f0f3f7; display: flex; gap: .55rem; min-height: 3.05rem; padding: .4rem .8rem; }
.subsync-list-row:last-child { border-bottom: 0; }
.subsync-list-icon { align-items: center; background: #edf2f7; border: 1px solid #cbd5e1; border-radius: 50%; color: #62758a; display: flex; flex: 0 0 1.6rem; font-size: .75rem; height: 1.6rem; justify-content: center; width: 1.6rem; }
.subsync-list-icon.bubble { background: #edf4fc; border-color: #cfdeef; border-radius: .42rem; color: #3a699f; }
.subsync-list-content { flex: 1; min-width: 0; }
.subsync-list-main { color: #425166; font-size: .69rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.subsync-list-secondary { color: #a1adba; font-size: .6rem; margin-top: .12rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.subsync-list-date { color: #8793a3; font-size: .6rem; white-space: nowrap; }
.subsync-panel-foot { border-top: 1px solid var(--subsync-line-soft); color: #5b6b7e; font-size: .65rem; padding: .55rem .8rem; text-align: right; }
.subsync-empty { color: #8794a5; font-size: .7rem; padding: 2rem .6rem; text-align: center; }
div[data-testid="stVerticalBlockBorderWrapper"] { background: #fff; border: 1px solid var(--subsync-line); border-radius: .65rem; padding: .1rem .2rem; }
.subsync-list-table { border-collapse: collapse; width: 100%; }
.subsync-list-table td { border-bottom: 1px solid #f0f3f7; padding: .4rem .8rem; vertical-align: middle; }
.subsync-list-table tr:last-child td { border-bottom: 0; }
.subsync-list-table td:first-child { padding-right: 0; width: 2.5rem; }
.subsync-list-table td:nth-child(2) { min-width: 0; width: 100%; }
.subsync-list-table td:last-child { padding-left: .2rem; text-align: right; }
.subsync-list-table .subsync-list-icon { display: flex; }

[data-testid="stDataFrame"] { border: 1px solid var(--subsync-line); border-radius: .55rem; overflow: hidden; }
.stButton > button, .stDownloadButton > button { border: 1px solid #d5e0eb; border-radius: .45rem; color: #486176; font-size: .72rem; font-weight: 600; }
.stMetric { background: #fff; border: 1px solid var(--subsync-line); border-radius: .6rem; padding: .75rem .85rem; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color: #68788d !important; }
[data-testid="stMetricValue"] { color: #182536 !important; }
[data-testid="stMetricDelta"] { color: #5d6d80 !important; }
.stTextInput input, .stDateInput input { border-color: #d8e1eb; border-radius: .45rem; font-size: .72rem; }
.stSelectbox div[data-baseweb="select"] { border-color: #d8e1eb; border-radius: .45rem; font-size: .72rem; }
.stTextInput label, .stSelectbox label, .stDateInput label { color: #69788a; font-size: .68rem; }
h1, h2, h3, h4, h5, h6 { color: var(--subsync-ink) !important; }
[data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] { color: #5d6d80; }
</style>
"""


def inject_styles() -> None:
    """대시보드 화면에 SubSync 스타일을 주입한다."""

    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
