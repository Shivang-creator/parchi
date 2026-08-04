"""Visual language for Parchi.

Clinical software is read at speed by tired people. Everything here optimises
for one thing: a number's colour should tell you what to do before you have
read the number.
"""

from __future__ import annotations

INK = "#0B1220"
SURFACE = "#111A2B"
SURFACE_2 = "#16223A"
LINE = "#22314F"
TEXT = "#E6EDF7"
MUTED = "#8FA3C0"

GOOD = "#2FBF71"
WARN = "#E8A33D"
BAD = "#E5484D"
ACCENT = "#4C9AFF"
RESERVE = "#B57BEE"

TIER_COLOR = {"ADEQUATE": GOOD, "MARGINAL": WARN, "INADEQUATE": BAD}
TIER_LABEL = {
    "ADEQUATE": "Meets empiric standard",
    "MARGINAL": "Below standard — culture and review",
    "INADEQUATE": "Not adequate as monotherapy",
}
SEVERITY_COLOR = {
    "BANNED": BAD, "MAJOR": BAD,
    "RESTRICTED": WARN, "MODERATE": WARN, "IRRATIONAL": WARN,
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, system-ui, sans-serif", color=TEXT, size=13),
    margin=dict(l=10, r=10, t=30, b=10),
    hoverlabel=dict(bgcolor=SURFACE_2, bordercolor=LINE, font_size=13),
    xaxis=dict(gridcolor=LINE, zerolinecolor=LINE),
    yaxis=dict(gridcolor=LINE, zerolinecolor=LINE),
)


CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

  .stApp {{ background: {INK}; }}
  html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, system-ui, sans-serif; }}

  #MainMenu, footer, header {{ visibility: hidden; }}
  .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1240px; }}

  h1, h2, h3, h4 {{ color: {TEXT}; letter-spacing: -0.02em; }}

  /* ---------- masthead ---------- */
  .masthead {{
    display: flex; align-items: baseline; gap: 14px;
    border-bottom: 1px solid {LINE}; padding-bottom: 14px; margin-bottom: 22px;
  }}
  .masthead .logo {{
    font-size: 30px; font-weight: 700; letter-spacing: -0.03em; color: {TEXT};
  }}
  .masthead .logo span {{ color: {ACCENT}; }}
  .masthead .tag {{ color: {MUTED}; font-size: 14px; }}

  /* ---------- cards ---------- */
  .card {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 14px;
    padding: 18px 20px; margin-bottom: 14px;
  }}
  .card-label {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: {MUTED}; margin-bottom: 10px;
  }}

  /* the drafted prescription — the one thing on screen that must dominate */
  .draft {{
    background: linear-gradient(135deg, {SURFACE_2} 0%, {SURFACE} 100%);
    border: 1px solid {LINE}; border-left: 4px solid var(--tier);
    border-radius: 14px; padding: 22px 24px; margin-bottom: 16px;
  }}
  .draft .drug {{
    font-size: 30px; font-weight: 700; color: {TEXT};
    letter-spacing: -0.02em; line-height: 1.15;
  }}
  .draft .dose {{
    font-family: 'JetBrains Mono', monospace; font-size: 15px;
    color: {ACCENT}; margin-top: 6px;
  }}
  .draft .rationale {{ color: {MUTED}; font-size: 13.5px; margin-top: 12px; line-height: 1.6; }}

  .bignum {{
    font-family: 'JetBrains Mono', monospace; font-size: 42px;
    font-weight: 700; line-height: 1; color: var(--tier);
  }}
  .bignum-sub {{ font-size: 12px; color: {MUTED}; margin-top: 6px; }}

  /* ---------- check tiles ---------- */
  .check {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 12px;
    border-top: 3px solid var(--c); padding: 14px 16px; height: 100%;
  }}
  .check .h {{
    font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: {MUTED}; font-weight: 600;
  }}
  .check .v {{
    font-family: 'JetBrains Mono', monospace; font-size: 22px;
    font-weight: 700; color: var(--c); margin: 6px 0 4px;
  }}
  .check .d {{ font-size: 12.5px; color: {MUTED}; line-height: 1.5; }}

  /* ---------- alerts ---------- */
  .alert {{
    background: {SURFACE}; border: 1px solid {LINE}; border-left: 3px solid var(--c);
    border-radius: 10px; padding: 12px 15px; margin-bottom: 9px;
  }}
  .alert .t {{ font-weight: 600; color: {TEXT}; font-size: 14px; }}
  .alert .b {{ color: {MUTED}; font-size: 13px; margin-top: 4px; line-height: 1.55; }}
  .pill {{
    display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    padding: 2px 8px; border-radius: 20px; margin-right: 8px;
    background: var(--c); color: {INK};
  }}

  .chip {{
    display: inline-block; background: {SURFACE_2}; border: 1px solid {LINE};
    color: {MUTED}; font-size: 12px; padding: 4px 11px; border-radius: 20px;
    margin: 0 6px 6px 0;
  }}
  .chip b {{ color: {TEXT}; font-family: 'JetBrains Mono', monospace; }}

  .disclaimer {{
    background: rgba(229,72,77,0.08); border: 1px solid rgba(229,72,77,0.3);
    color: #FFC9CB; border-radius: 10px; padding: 10px 14px;
    font-size: 12.5px; margin-bottom: 18px; line-height: 1.55;
  }}

  /* ---------- streamlit overrides ---------- */
  section[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {LINE}; }}
  section[data-testid="stSidebar"] .block-container {{ padding-top: 1.4rem; }}

  .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {LINE}; }}
  .stTabs [data-baseweb="tab"] {{
    background: transparent; color: {MUTED}; font-weight: 600; font-size: 14px;
    padding: 9px 16px; border-radius: 8px 8px 0 0;
  }}
  .stTabs [aria-selected="true"] {{ color: {TEXT} !important; background: {SURFACE} !important; }}

  div[data-testid="stMetricValue"] {{ font-family: 'JetBrains Mono', monospace; }}
  .stButton button {{ border-radius: 9px; font-weight: 600; border: 1px solid {LINE}; }}
  .stDataFrame {{ border: 1px solid {LINE}; border-radius: 10px; }}
</style>
"""


def tier_style(tier: str) -> str:
    return TIER_COLOR.get(tier, MUTED)
