"""Parchi's visual language.

The design has one idea and everything follows from it: a *parchi* is a piece
of paper. So the app is a document, not a dashboard — warm stock, ink, a red
℞, hairline rules, and type doing the work that boxes and gradients usually
do badly.

Practical consequences of committing to that:

  - Warm cream ground, never white and never charcoal. White is a browser
    default; charcoal-with-a-blue-accent is the house style of every generated
    dashboard on earth.
  - Ink is warm near-black, not #000. Real ink on real paper is never neutral.
  - ONE signature colour — the ℞ red — plus muted, desaturated status inks.
    A six-colour semantic rainbow reads as a control panel.
  - Rules, not borders. A 1px hairline at low opacity separates things on
    paper; a 1px box around everything is a wireframe that never got designed.
  - 3px radii. Paper does not have 14px rounded corners.
  - A serif for anything a human reads as language, a humanist sans for
    interface furniture, a mono for anything that is a measurement.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Ink and paper
# --------------------------------------------------------------------------
PAPER = "#FBF8F1"          # the sheet
PAPER_WARM = "#F4EEE1"     # a second sheet beneath, and the sidebar
PAPER_BRIGHT = "#FFFDF8"   # the prescription slip itself, catching light
RULE = "#DDD4C0"           # hairline
RULE_SOFT = "#EAE3D4"

INK = "#17150F"            # primary text — warm near-black
INK_2 = "#55503F"          # secondary
INK_3 = "#8A8270"          # muted / captions

RX = "#B03A2E"             # the signature: ℞ red, and anything that stops you
SAFE = "#2D6A4F"           # deep forest, not neon
CAUTION = "#9A6B1E"        # goldenrod ink
DANGER = "#A32B22"
STAMP = "#2C5F7C"          # the blue of an official stamp
RESERVE = "#6B4C8A"        # last-line agents

TIER_COLOR = {"ADEQUATE": SAFE, "MARGINAL": CAUTION, "INADEQUATE": DANGER}
TIER_LABEL = {
    "ADEQUATE": "Meets the empiric standard",
    "MARGINAL": "Below standard — culture and review",
    "INADEQUATE": "Not adequate as monotherapy",
}
SEVERITY_COLOR = {
    "BANNED": DANGER, "MAJOR": DANGER,
    "RESTRICTED": CAUTION, "MODERATE": CAUTION, "IRRATIONAL": CAUTION,
    "ROUTING": CAUTION, "INFO": STAMP,
}
AWARE_COLOR = {"Access": SAFE, "Watch": CAUTION, "Reserve": RESERVE}

# A very fine grain, so the ground reads as stock rather than as a flat fill.
GRAIN = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='180' height='180'%3E%3Cfilter id='g'%3E%3CfeTurbulence "
    "type='fractalNoise' baseFrequency='0.85' numOctaves='4'/%3E%3C/filter%3E"
    "%3Crect width='180' height='180' filter='url(%23g)' opacity='0.04'/%3E"
    "%3C/svg%3E\")"
)

# --------------------------------------------------------------------------
# Charts — same ink, same paper
# --------------------------------------------------------------------------
SERIES = [STAMP, RX, SAFE, CAUTION, RESERVE, INK_3]

_AXIS = dict(
    gridcolor=RULE_SOFT, zerolinecolor=RULE, linecolor=RULE,
    tickfont=dict(color=INK_3),
)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="'IBM Plex Sans', system-ui, sans-serif", color=INK_2, size=12),
    margin=dict(l=8, r=8, t=28, b=8),
    hoverlabel=dict(
        bgcolor=PAPER_BRIGHT, bordercolor=RULE,
        font=dict(family="'IBM Plex Sans', sans-serif", color=INK, size=12),
    ),
    xaxis=dict(_AXIS),
    yaxis=dict(_AXIS),
    colorway=SERIES,
)


def layout(**overrides) -> dict:
    """Base chart layout merged with per-chart overrides.

    Spreading PLOTLY_LAYOUT and *also* passing `yaxis=` is a TypeError, because
    both define the same keyword. Axis dicts merge one level deep so a caller
    can set just a title or a range without restating the ink.
    """
    merged = {k: (dict(v) if isinstance(v, dict) else v)
              for k, v in PLOTLY_LAYOUT.items()}
    for key, value in overrides.items():
        if key in ("xaxis", "yaxis") and isinstance(value, dict):
            merged[key] = {**merged.get(key, {}), **value}
        else:
            merged[key] = value
    return merged


def chart_title(text: str) -> dict:
    return dict(text=text, font=dict(family="Newsreader, serif", size=15, color=INK))


def tier_style(tier: str) -> str:
    return TIER_COLOR.get(tier, INK_3)


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300..700;1,6..72,300..600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ---------- ground ---------- */
.stApp {{
  background-color: {PAPER};
  background-image: {GRAIN};
}}
html, body, [class*="css"] {{
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
  color: {INK};
  -webkit-font-smoothing: antialiased;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{
  padding-top: 2.6rem; padding-bottom: 5rem;
  max-width: 1120px;
}}

/* ---------- type ---------- */
h1, h2, h3 {{
  font-family: 'Newsreader', Georgia, serif;
  font-weight: 500; color: {INK}; letter-spacing: -0.011em;
}}
h1 {{ font-size: 2.1rem; }}
h2 {{ font-size: 1.5rem; margin-top: 0.4rem; }}
h3 {{ font-size: 1.18rem; }}
p, li {{ color: {INK_2}; line-height: 1.68; }}
a {{ color: {STAMP}; }}

.label {{
  font-size: 10.5px; font-weight: 600; letter-spacing: 0.15em;
  text-transform: uppercase; color: {INK_3};
  display: block; margin-bottom: 9px;
}}
.rule {{ height: 1px; background: {RULE}; margin: 26px 0 20px; border: 0; }}
.rule-soft {{ height: 1px; background: {RULE_SOFT}; margin: 16px 0; border: 0; }}

/* ---------- masthead ---------- */
.masthead {{
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 20px; border-bottom: 2px solid {INK}; padding-bottom: 12px;
  margin-bottom: 6px;
}}
.masthead .wordmark {{
  font-family: 'Newsreader', Georgia, serif; font-size: 2.5rem;
  font-weight: 500; line-height: 1; color: {INK}; letter-spacing: -0.02em;
}}
.masthead .wordmark .deva {{ margin-right: 10px; color: {RX}; }}
.masthead .standfirst {{
  font-family: 'Newsreader', Georgia, serif; font-style: italic;
  font-size: 1.02rem; color: {INK_2}; padding-bottom: 5px; text-align: right;
  max-width: 420px; line-height: 1.4;
}}
.masthead-sub {{
  display: flex; justify-content: space-between;
  font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase;
  color: {INK_3}; padding-top: 7px; margin-bottom: 24px;
}}

/* ---------- the slip ---------- */
.slip {{
  position: relative; background: {PAPER_BRIGHT};
  border: 1px solid {RULE}; border-radius: 3px;
  box-shadow: 0 1px 2px rgba(23,21,15,0.05), 0 8px 22px -12px rgba(23,21,15,0.16);
  padding: 26px 30px 22px;
}}
.slip::before {{
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: var(--accent, {RX}); border-radius: 3px 0 0 3px;
}}
.slip-head {{
  display: flex; align-items: baseline; gap: 12px;
  border-bottom: 1px solid {RULE_SOFT}; padding-bottom: 11px; margin-bottom: 16px;
}}
.rx {{
  font-family: 'Newsreader', Georgia, serif; font-size: 2.5rem;
  color: {RX}; line-height: 0.8; font-weight: 500;
}}
.slip-head .who {{ font-size: 12.5px; color: {INK_3}; line-height: 1.5; }}
.slip-head .who b {{ color: {INK_2}; font-weight: 600; }}

.slip .drug {{
  font-family: 'Newsreader', Georgia, serif; font-size: 2.15rem;
  font-weight: 500; color: {INK}; line-height: 1.12; letter-spacing: -0.015em;
}}
.slip .sig {{
  font-family: 'IBM Plex Mono', monospace; font-size: 13.5px;
  color: {INK_2}; margin-top: 7px; letter-spacing: -0.01em;
}}
.slip .why {{
  font-size: 13.5px; color: {INK_2}; line-height: 1.65;
  margin-top: 15px; padding-top: 13px; border-top: 1px dashed {RULE};
}}
.slip .adjunct {{
  font-family: 'IBM Plex Mono', monospace; font-size: 12.5px;
  color: {INK_2}; padding: 4px 0 4px 16px; border-left: 2px solid {RULE};
  margin-top: 8px;
}}

/* ---------- the verdict ---------- */
.verdict {{
  background: {PAPER_BRIGHT}; border: 1px solid {RULE}; border-radius: 3px;
  padding: 22px 20px; text-align: center; height: 100%;
  box-shadow: 0 1px 2px rgba(23,21,15,0.04);
}}
.verdict .n {{
  font-family: 'IBM Plex Mono', monospace; font-size: 3.4rem;
  font-weight: 600; line-height: 0.95; color: var(--c); letter-spacing: -0.04em;
}}
.verdict .n .pct {{ font-size: 1.3rem; font-weight: 500; }}
.verdict .say {{
  font-size: 12.5px; color: {INK_2}; margin-top: 12px; line-height: 1.5;
}}
.verdict .bar {{
  height: 3px; background: {RULE_SOFT}; margin: 14px 0 10px; position: relative;
}}
.verdict .bar i {{
  position: absolute; left: 0; top: 0; bottom: 0; background: var(--c);
}}
.verdict .bar u {{
  position: absolute; top: -3px; bottom: -3px; width: 1px;
  background: {INK_2}; text-decoration: none;
}}

/* ---------- check row ---------- */
.checks {{
  display: grid; grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid {RULE}; border-bottom: 1px solid {RULE};
  margin: 22px 0 20px;
}}
.check {{ padding: 15px 18px 14px; border-left: 1px solid {RULE_SOFT}; }}
.check:first-child {{ border-left: 0; padding-left: 0; }}
.check .q {{
  font-size: 10.5px; letter-spacing: 0.13em; text-transform: uppercase;
  color: {INK_3}; font-weight: 600;
}}
.check .a {{
  font-family: 'IBM Plex Mono', monospace; font-size: 1.42rem;
  font-weight: 600; color: var(--c); margin: 7px 0 5px; letter-spacing: -0.02em;
}}
.check .n {{ font-size: 12px; color: {INK_3}; line-height: 1.55; }}

/* ---------- annotations, not alert boxes ---------- */
.note {{
  border-left: 2px solid var(--c); padding: 3px 0 3px 15px; margin-bottom: 14px;
}}
.note .h {{ font-size: 14px; font-weight: 600; color: {INK}; }}
.note .h .tag {{
  font-family: 'IBM Plex Mono', monospace; font-size: 9.5px; font-weight: 600;
  letter-spacing: 0.1em; color: var(--c); border: 1px solid var(--c);
  padding: 1px 6px; border-radius: 2px; margin-right: 9px;
  position: relative; top: -1px;
}}
.note .b {{ font-size: 13px; color: {INK_2}; line-height: 1.62; margin-top: 4px; }}

/* ---------- patient strip ---------- */
.strip {{
  display: flex; flex-wrap: wrap; gap: 0; border-bottom: 1px solid {RULE};
  margin-bottom: 22px;
}}
.strip div {{
  padding: 0 20px 12px 0; margin-right: 20px; border-right: 1px solid {RULE_SOFT};
}}
.strip div:last-child {{ border-right: 0; }}
.strip .k {{
  font-size: 10px; letter-spacing: 0.13em; text-transform: uppercase;
  color: {INK_3}; font-weight: 600; display: block; margin-bottom: 3px;
}}
.strip .v {{
  font-family: 'IBM Plex Mono', monospace; font-size: 15px;
  font-weight: 500; color: {INK};
}}
.strip .v small {{ color: {INK_3}; font-size: 11px; }}

/* ---------- caveat ---------- */
.caveat {{
  font-size: 11.5px; color: {INK_3}; line-height: 1.6;
  border-top: 1px solid {RULE_SOFT}; padding-top: 10px; margin-top: 6px;
}}
.caveat b {{ color: {RX}; font-weight: 600; }}

.stamp {{
  display: inline-block; font-family: 'IBM Plex Mono', monospace;
  font-size: 10px; font-weight: 600; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--c); border: 1.5px solid var(--c);
  padding: 3px 9px; border-radius: 2px; transform: rotate(-1.2deg);
  opacity: 0.85;
}}

/* ---------- streamlit furniture ---------- */
section[data-testid="stSidebar"] {{
  background: {PAPER_WARM}; border-right: 1px solid {RULE};
}}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1.6rem; }}
section[data-testid="stSidebar"] h4 {{
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 10.5px !important; font-weight: 600 !important;
  letter-spacing: 0.15em; text-transform: uppercase; color: {INK_3} !important;
  border-bottom: 1px solid {RULE}; padding-bottom: 7px; margin: 20px 0 12px !important;
}}
section[data-testid="stSidebar"] label {{ font-size: 12.5px !important; color: {INK_2} !important; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 26px; border-bottom: 1px solid {RULE}; }}
.stTabs [data-baseweb="tab"] {{
  background: transparent !important; padding: 8px 0 11px;
  font-size: 11px; font-weight: 600; letter-spacing: 0.13em;
  text-transform: uppercase; color: {INK_3};
}}
.stTabs [aria-selected="true"] {{
  color: {INK} !important; box-shadow: inset 0 -2px 0 {RX};
}}
.stTabs [data-baseweb="tab-highlight"] {{ background: transparent !important; }}

div[data-testid="stMetricValue"] {{
  font-family: 'IBM Plex Mono', monospace; font-weight: 600;
  font-size: 1.55rem; color: {INK};
}}
div[data-testid="stMetricLabel"] p {{
  font-size: 10.5px !important; letter-spacing: 0.13em; text-transform: uppercase;
  color: {INK_3} !important; font-weight: 600;
}}
div[data-testid="stMetricDelta"] {{ font-size: 12px; }}

.stButton button {{
  border-radius: 3px; font-weight: 600; font-size: 13px;
  border: 1px solid {RULE}; background: {PAPER_BRIGHT}; color: {INK};
  transition: background 120ms ease, border-color 120ms ease;
}}
.stButton button:hover {{ border-color: {INK_3}; background: {PAPER_WARM}; color: {INK}; }}
.stButton button[kind="primary"] {{
  background: {INK}; border-color: {INK}; color: {PAPER};
}}
.stButton button[kind="primary"]:hover {{ background: {RX}; border-color: {RX}; color: {PAPER}; }}

div[data-testid="stExpander"] {{
  border: 1px solid {RULE_SOFT}; border-radius: 3px; background: transparent;
}}
div[data-testid="stExpander"] summary {{ font-size: 12.5px; color: {INK_2}; }}

.stDataFrame, div[data-testid="stDataFrame"] {{
  border: 1px solid {RULE}; border-radius: 3px;
}}
div[data-testid="stAlert"] {{ border-radius: 3px; font-size: 13px; }}

.stSlider [data-baseweb="slider"] div[role="slider"] {{ background: {RX} !important; }}

/* Multiselect tags inherit primaryColor and come out shouting red, which reads
   as an error state on what is just a selected option. Mute them to ink. */
span[data-baseweb="tag"] {{
  background-color: {PAPER_WARM} !important;
  border: 1px solid {RULE} !important;
  color: {INK_2} !important;
  border-radius: 3px !important;
  font-size: 12px !important;
}}
span[data-baseweb="tag"] span[role="presentation"] svg {{ fill: {INK_3} !important; }}

/* The signature rule at the foot of the slip — a real parchi has one. */
.slip-foot {{
  display: flex; justify-content: space-between; align-items: flex-end;
  margin-top: 20px; padding-top: 14px; border-top: 1px solid {RULE_SOFT};
}}
.slip-foot .marks {{ font-size: 11px; color: {INK_3}; line-height: 1.9; }}
.slip-foot .marks b {{ color: {INK_2}; font-weight: 600; }}
.slip-foot .sign {{ text-align: right; min-width: 190px; }}
.slip-foot .sign i {{
  display: block; border-bottom: 1px dotted {INK_3}; height: 26px; margin-bottom: 5px;
}}
.slip-foot .sign span {{
  font-size: 10px; letter-spacing: 0.13em; text-transform: uppercase; color: {INK_3};
}}
.stCaption, .stCaption p {{ color: {INK_3} !important; font-size: 11.5px !important; }}
</style>
"""
