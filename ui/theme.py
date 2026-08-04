"""Parchi's visual language, in two moods.

The design has one idea and everything follows from it: a *parchi* is a piece
of paper. So the app is a document, not a dashboard — stock, ink, a red ℞,
hairline rules, and type doing the work that boxes and gradients usually do
badly.

Two palettes, both committed to that idea:

    Paper   warm cream stock, warm near-black ink — a slip on a desk
    Ink     the same slip under a reading lamp at 2am: warm near-black
            ground, cream ink, the same ℞ red pushed up for contrast

Deliberately *not* a second theme in the usual sense. Dark mode here is not
"the blue-grey one" — it is the same document, lit differently. Neutral
charcoal with a blue accent is the house style of every generated dashboard
on earth, and adopting it would throw away the only thing that makes this look
like someone designed it.

## How the switch works

Colours are read at *render* time, not import time, through PEP 562 module
`__getattr__`. That means every existing call site — `theme.SAFE`,
`theme.INK_2` — keeps working untouched and silently resolves against
whichever palette is active. Without it, every colour reference in every
screen would have had to be rewritten to thread a palette object through.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Palette:
    name: str
    dark: bool

    PAPER: str          # the ground
    PAPER_WARM: str     # sidebar, second sheet
    PAPER_BRIGHT: str   # the slip itself, catching light
    RULE: str           # hairline
    RULE_SOFT: str

    INK: str            # primary text
    INK_2: str          # secondary
    INK_3: str          # muted / captions

    RX: str             # the signature colour
    SAFE: str
    CAUTION: str
    DANGER: str
    STAMP: str
    RESERVE: str

    MAP_STYLE: str
    GRAIN_OPACITY: float
    SHADOW: str


PAPER_THEME = Palette(
    name="Paper", dark=False,
    PAPER="#FBF8F1", PAPER_WARM="#F4EEE1", PAPER_BRIGHT="#FFFDF8",
    RULE="#DDD4C0", RULE_SOFT="#EAE3D4",
    INK="#17150F", INK_2="#55503F", INK_3="#8A8270",
    RX="#B03A2E", SAFE="#2D6A4F", CAUTION="#9A6B1E",
    DANGER="#A32B22", STAMP="#2C5F7C", RESERVE="#6B4C8A",
    MAP_STYLE="carto-positron", GRAIN_OPACITY=0.04,
    SHADOW="0 1px 2px rgba(23,21,15,0.05), 0 8px 22px -12px rgba(23,21,15,0.16)",
)

INK_THEME = Palette(
    name="Ink", dark=True,
    # Warm near-black, never neutral charcoal — this is the same paper stock
    # in low light, not a different product.
    PAPER="#14110C", PAPER_WARM="#1B1711", PAPER_BRIGHT="#221D15",
    RULE="#3B3428", RULE_SOFT="#2A241B",
    INK="#F3ECDD", INK_2="#BEB4A0", INK_3="#8B8271",
    # Every accent is lifted for contrast against a dark ground; the hues are
    # unchanged, so the app reads as the same object.
    RX="#E0705B", SAFE="#5FB98C", CAUTION="#DDA94E",
    DANGER="#E8776A", STAMP="#6BA8CC", RESERVE="#B294DC",
    MAP_STYLE="carto-darkmatter", GRAIN_OPACITY=0.05,
    SHADOW="0 1px 2px rgba(0,0,0,0.35), 0 10px 26px -14px rgba(0,0,0,0.7)",
)

THEMES = {"Paper": PAPER_THEME, "Ink": INK_THEME}
_TOKENS = {f.name for f in fields(Palette)}


def palette() -> Palette:
    """The active palette, read fresh on every access."""
    try:
        import streamlit as st

        return THEMES.get(st.session_state.get("theme_name", "Paper"), PAPER_THEME)
    except Exception:      # noqa: BLE001 — importable outside a Streamlit run
        return PAPER_THEME


def __getattr__(name: str):
    """Resolve colour tokens against whichever palette is live.

    PEP 562. This is what lets `theme.SAFE` mean one thing in Paper and
    another in Ink without a single call site knowing a theme exists.
    """
    if name in _TOKENS:
        return getattr(palette(), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# --------------------------------------------------------------------------
# Semantic maps — functions, because they depend on the active palette
# --------------------------------------------------------------------------
TIER_LABEL = {
    "ADEQUATE": "Meets the empiric standard",
    "MARGINAL": "Below standard — culture and review",
    "INADEQUATE": "Not adequate as monotherapy",
}


def tier_colors() -> dict:
    p = palette()
    return {"ADEQUATE": p.SAFE, "MARGINAL": p.CAUTION, "INADEQUATE": p.DANGER}


def severity_colors() -> dict:
    p = palette()
    return {
        "BANNED": p.DANGER, "MAJOR": p.DANGER, "CONTRAINDICATED": p.DANGER,
        "RESTRICTED": p.CAUTION, "MODERATE": p.CAUTION, "IRRATIONAL": p.CAUTION,
        "ROUTING": p.CAUTION, "CAPACITY": p.CAUTION, "DURATION": p.CAUTION,
        "INFO": p.STAMP, "CLEAR": p.SAFE,
    }


def aware_colors() -> dict:
    p = palette()
    return {"Access": p.SAFE, "Watch": p.CAUTION, "Reserve": p.RESERVE}


def risk_colors() -> dict:
    p = palette()
    return {
        "Low": p.SAFE, "Routine": p.SAFE, "Moderate": p.CAUTION,
        "Medium": p.CAUTION, "High": p.DANGER, "Catastrophic": p.DANGER,
    }


def tier_style(tier: str) -> str:
    return tier_colors().get(tier, palette().INK_3)


def series() -> list[str]:
    p = palette()
    return [p.STAMP, p.RX, p.SAFE, p.CAUTION, p.RESERVE, p.INK_3]


def grain() -> str:
    p = palette()
    return (
        "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
        "width='180' height='180'%3E%3Cfilter id='g'%3E%3CfeTurbulence "
        "type='fractalNoise' baseFrequency='0.85' numOctaves='4'/%3E%3C/filter%3E"
        f"%3Crect width='180' height='180' filter='url(%23g)' opacity='{p.GRAIN_OPACITY}'/%3E"
        "%3C/svg%3E\")"
    )


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def layout(**overrides) -> dict:
    """Base chart layout, in the active palette, merged with per-chart overrides.

    Axis dicts merge one level deep so a caller can set just a title or a range
    without restating the ink. (Spreading a base layout dict and *also* passing
    `yaxis=` is a TypeError — both define the same keyword.)
    """
    p = palette()
    axis = dict(gridcolor=p.RULE_SOFT, zerolinecolor=p.RULE, linecolor=p.RULE,
                tickfont=dict(color=p.INK_3))
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="'IBM Plex Sans', system-ui, sans-serif",
                  color=p.INK_2, size=12),
        margin=dict(l=8, r=8, t=28, b=8),
        hoverlabel=dict(
            bgcolor=p.PAPER_BRIGHT, bordercolor=p.RULE,
            font=dict(family="'IBM Plex Sans', sans-serif", color=p.INK, size=12),
        ),
        xaxis=dict(axis), yaxis=dict(axis),
        colorway=series(),
    )
    for key, value in overrides.items():
        if key in ("xaxis", "yaxis") and isinstance(value, dict):
            base[key] = {**base[key], **value}
        else:
            base[key] = value
    return base


def chart_title(text: str) -> dict:
    p = palette()
    return dict(text=text, x=0, xanchor="left", y=0.97,
                font=dict(family="Newsreader, serif", size=15, color=p.INK))


# --------------------------------------------------------------------------
# Navigation rail
# --------------------------------------------------------------------------
# The nav is one control, not two. An HTML rail for looks plus a button row to
# actually click is duplicated navigation and duplicated vertical space, so the
# buttons ARE the rail: styled into connected segments, with the icon painted
# on as a background image and the subtitle injected through ::after.
# Both have to be CSS because a Streamlit button label is plain text.
_NAV_ICONS = {
    "reception": "<path d='M4 20V7l8-3 8 3v13'/><path d='M9 20v-5h6v5'/><path d='M4 20h16'/>",
    "doctor": "<path d='M8 3v5a4 4 0 0 0 8 0V3'/><path d='M12 12v3a5 5 0 0 0 10 0v-1'/>"
              "<circle cx='22' cy='12' r='1.6'/>",
    "pharmacy": "<rect x='3' y='9' width='18' height='12' rx='2'/>"
                "<path d='M7 9V6a5 5 0 0 1 10 0v3'/><path d='M12 12v6M9 15h6'/>",
    "hospital": "<path d='M3 21V8l9-5 9 5v13'/><path d='M12 10v6M9 13h6'/>",
    "method": "<path d='M4 4h9a3 3 0 0 1 3 3v13a2.5 2.5 0 0 0-2.5-2.5H4z'/>"
              "<path d='M20 4h-2a3 3 0 0 0-3 3v13a2.5 2.5 0 0 1 2.5-2.5H20z'/>",
}
NAV_STOPS = [
    ("reception", "triage the queue"),
    ("doctor", "choose the drug"),
    ("pharmacy", "price the slip"),
    ("hospital", "what is coming"),
    ("method", "data and model"),
]


def _icon_uri(name: str, colour: str) -> str:
    from urllib.parse import quote

    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
        f"viewBox='0 0 24 24' fill='none' stroke='{colour}' stroke-width='1.5' "
        f"stroke-linecap='round' stroke-linejoin='round'>{_NAV_ICONS[name]}</svg>"
    )
    return f"url(\"data:image/svg+xml,{quote(svg, safe='')}\")"


def _nav_css(p: Palette) -> str:
    rules = [f"""
.st-key-railnav div[data-testid="stHorizontalBlock"] {{
  gap: 0 !important; border: 1px solid {p.RULE}; border-radius: 3px;
  overflow: hidden; background: {p.PAPER_BRIGHT}; margin-bottom: 24px;
}}
.st-key-railnav div[data-testid="stColumn"] {{ border-left: 1px solid {p.RULE_SOFT}; }}
.st-key-railnav div[data-testid="stColumn"]:first-child {{ border-left: 0; }}
.st-key-railnav .stButton button {{
  width: 100%; border: 0 !important; border-radius: 0 !important;
  background-color: transparent !important; text-align: left !important;
  padding: 44px 16px 30px 16px !important; position: relative;
  font-size: 13.5px !important; font-weight: 600 !important;
  color: {p.INK_3} !important; justify-content: flex-start !important;
  background-repeat: no-repeat !important; background-position: 16px 14px !important;
}}
.st-key-railnav .stButton button:hover {{ background-color: {p.PAPER_WARM} !important; }}
.st-key-railnav .stButton button p {{ text-align: left; }}
.st-key-railnav .stButton button[kind="primary"] {{
  background-color: {p.PAPER_WARM} !important; color: {p.INK} !important;
  box-shadow: inset 0 -2px 0 {p.RX};
  background-repeat: no-repeat !important; background-position: 16px 14px !important;
}}
.st-key-railnav .stButton button::after {{
  position: absolute; left: 16px; bottom: 10px;
  font-size: 11px; font-weight: 400; color: {p.INK_3}; opacity: 0.85;
  letter-spacing: 0; text-transform: none;
}}"""]
    for index, (name, subtitle) in enumerate(NAV_STOPS, start=1):
        rules.append(f"""
.st-key-railnav div[data-testid="stColumn"]:nth-of-type({index}) .stButton button {{
  background-image: {_icon_uri(name, p.INK_3)} !important;
}}
.st-key-railnav div[data-testid="stColumn"]:nth-of-type({index}) .stButton button[kind="primary"] {{
  background-image: {_icon_uri(name, p.RX)} !important;
}}
.st-key-railnav div[data-testid="stColumn"]:nth-of-type({index}) .stButton button::after {{
  content: "{subtitle}";
}}""")
    return "\n".join(rules)


# --------------------------------------------------------------------------
# Stylesheet
# --------------------------------------------------------------------------
def css() -> str:
    p = palette()
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300..700;1,6..72,300..600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {{
  --paper: {p.PAPER}; --paper-warm: {p.PAPER_WARM}; --paper-bright: {p.PAPER_BRIGHT};
  --rule: {p.RULE}; --rule-soft: {p.RULE_SOFT};
  --ink: {p.INK}; --ink-2: {p.INK_2}; --ink-3: {p.INK_3};
  --rx: {p.RX}; --safe: {p.SAFE}; --caution: {p.CAUTION};
  --danger: {p.DANGER}; --stamp: {p.STAMP}; --reserve: {p.RESERVE};
  --shadow: {p.SHADOW};
}}

/* ---------- ground ---------- */
.stApp {{ background-color: var(--paper); background-image: {grain()}; }}
html, body, [class*="css"] {{
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
  color: var(--ink); -webkit-font-smoothing: antialiased;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 5rem; max-width: 1180px; }}

/* ---------- type ---------- */
h1, h2, h3 {{
  font-family: 'Newsreader', Georgia, serif; font-weight: 500;
  color: var(--ink); letter-spacing: -0.011em;
}}
h1 {{ font-size: 2.1rem; }}
h2 {{ font-size: 1.5rem; margin-top: 0.4rem; }}
h3 {{ font-size: 1.18rem; }}
p, li {{ color: var(--ink-2); line-height: 1.68; }}
a {{ color: var(--stamp); }}
code {{ background: var(--paper-warm); color: var(--ink-2); border-radius: 2px; }}

.label {{
  font-size: 10.5px; font-weight: 600; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--ink-3); display: block; margin-bottom: 9px;
}}
.rule {{ height: 1px; background: var(--rule); margin: 26px 0 20px; border: 0; }}
.rule-soft {{ height: 1px; background: var(--rule-soft); margin: 16px 0; border: 0; }}

/* ---------- masthead ---------- */
.masthead {{
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 20px; border-bottom: 2px solid var(--ink); padding-bottom: 12px; margin-bottom: 6px;
}}
.masthead .wordmark {{
  font-family: 'Newsreader', Georgia, serif; font-size: 2.5rem; font-weight: 500;
  line-height: 1; color: var(--ink); letter-spacing: -0.02em;
}}
.masthead .wordmark .deva {{ margin-right: 10px; color: var(--rx); }}
.masthead .standfirst {{
  font-family: 'Newsreader', Georgia, serif; font-style: italic; font-size: 1.02rem;
  color: var(--ink-2); padding-bottom: 5px; text-align: right; max-width: 430px; line-height: 1.4;
}}
.masthead-sub {{
  display: flex; justify-content: space-between; font-size: 10.5px;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-3);
  padding-top: 7px; margin-bottom: 18px;
}}

/* ---------- the journey rail ---------- */
.rail {{
  display: flex; align-items: stretch; gap: 0; border: 1px solid var(--rule);
  border-radius: 3px; overflow: hidden; margin-bottom: 26px; background: var(--paper-bright);
}}
.rail .stop {{
  flex: 1; padding: 13px 16px; border-left: 1px solid var(--rule-soft);
  position: relative; min-width: 0;
}}
.rail .stop:first-child {{ border-left: 0; }}
.rail .stop .n {{
  font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: var(--ink-3);
  letter-spacing: 0.1em;
}}
.rail .stop .t {{
  font-size: 13.5px; font-weight: 600; color: var(--ink-3); margin-top: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.rail .stop .d {{ font-size: 11px; color: var(--ink-3); margin-top: 2px; opacity: 0.8; }}
.rail .stop.on {{ background: var(--paper-warm); }}
.rail .stop.on::after {{
  content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 2px; background: var(--rx);
}}
.rail .stop.on .t {{ color: var(--ink); }}
.rail .stop.done .t {{ color: var(--ink-2); }}

/* ---------- the slip ---------- */
.slip {{
  position: relative; background: var(--paper-bright); border: 1px solid var(--rule);
  border-radius: 3px; box-shadow: var(--shadow); padding: 26px 30px 22px;
}}
.slip::before {{
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: var(--accent, var(--rx)); border-radius: 3px 0 0 3px;
}}
.slip-head {{
  display: flex; align-items: baseline; gap: 12px;
  border-bottom: 1px solid var(--rule-soft); padding-bottom: 11px; margin-bottom: 16px;
}}
.rx {{
  font-family: 'Newsreader', Georgia, serif; font-size: 2.5rem; color: var(--rx);
  line-height: 0.8; font-weight: 500;
}}
.slip-head .who {{ font-size: 12.5px; color: var(--ink-3); line-height: 1.5; }}
.slip-head .who b {{ color: var(--ink-2); font-weight: 600; }}
.slip .drug {{
  font-family: 'Newsreader', Georgia, serif; font-size: 2.15rem; font-weight: 500;
  color: var(--ink); line-height: 1.12; letter-spacing: -0.015em;
}}
.slip .sig {{
  font-family: 'IBM Plex Mono', monospace; font-size: 13.5px; color: var(--ink-2);
  margin-top: 7px; letter-spacing: -0.01em;
}}
.slip .why {{
  font-size: 13.5px; color: var(--ink-2); line-height: 1.65; margin-top: 15px;
  padding-top: 13px; border-top: 1px dashed var(--rule);
}}
.slip .adjunct {{
  font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: var(--ink-2);
  padding: 4px 0 4px 16px; border-left: 2px solid var(--rule); margin-top: 8px;
}}
.slip-foot {{
  display: flex; justify-content: space-between; align-items: flex-end;
  margin-top: 20px; padding-top: 14px; border-top: 1px solid var(--rule-soft);
}}
.slip-foot .marks {{ font-size: 11px; color: var(--ink-3); line-height: 1.9; }}
.slip-foot .marks b {{ color: var(--ink-2); font-weight: 600; }}
.slip-foot .sign {{ text-align: right; min-width: 190px; }}
.slip-foot .sign i {{
  display: block; border-bottom: 1px dotted var(--ink-3); height: 26px; margin-bottom: 5px;
}}
.slip-foot .sign span {{
  font-size: 10px; letter-spacing: 0.13em; text-transform: uppercase; color: var(--ink-3);
}}

/* ---------- verdict ---------- */
.verdict {{
  background: var(--paper-bright); border: 1px solid var(--rule); border-radius: 3px;
  padding: 22px 20px; text-align: center; height: 100%; box-shadow: var(--shadow);
}}
.verdict .n {{
  font-family: 'IBM Plex Mono', monospace; font-size: 3.4rem; font-weight: 600;
  line-height: 0.95; color: var(--c); letter-spacing: -0.04em;
}}
.verdict .n .pct {{ font-size: 1.3rem; font-weight: 500; }}
.verdict .say {{ font-size: 12.5px; color: var(--ink-2); margin-top: 12px; line-height: 1.5; }}
.verdict .bar {{ height: 3px; background: var(--rule-soft); margin: 14px 0 10px; position: relative; }}
.verdict .bar i {{ position: absolute; left: 0; top: 0; bottom: 0; background: var(--c); }}
.verdict .bar u {{
  position: absolute; top: -3px; bottom: -3px; width: 1px; background: var(--ink-2);
  text-decoration: none;
}}

/* ---------- check row ---------- */
.checks {{
  display: grid; grid-template-columns: repeat(var(--cols, 4), 1fr);
  border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); margin: 22px 0 20px;
}}
.check {{ padding: 15px 18px 14px; border-left: 1px solid var(--rule-soft); }}
.check:first-child {{ border-left: 0; padding-left: 0; }}
.check .q {{
  font-size: 10.5px; letter-spacing: 0.13em; text-transform: uppercase;
  color: var(--ink-3); font-weight: 600;
}}
.check .a {{
  font-family: 'IBM Plex Mono', monospace; font-size: 1.42rem; font-weight: 600;
  color: var(--c); margin: 7px 0 5px; letter-spacing: -0.02em;
}}
.check .n {{ font-size: 12px; color: var(--ink-3); line-height: 1.55; }}

/* ---------- annotations ---------- */
.note {{ border-left: 2px solid var(--c); padding: 3px 0 3px 15px; margin-bottom: 14px; }}
.note .h {{ font-size: 14px; font-weight: 600; color: var(--ink); }}
.note .h .tag {{
  font-family: 'IBM Plex Mono', monospace; font-size: 9.5px; font-weight: 600;
  letter-spacing: 0.1em; color: var(--c); border: 1px solid var(--c);
  padding: 1px 6px; border-radius: 2px; margin-right: 9px; position: relative; top: -1px;
}}
.note .b {{ font-size: 13px; color: var(--ink-2); line-height: 1.62; margin-top: 4px; }}

/* ---------- patient strip ---------- */
.strip {{ display: flex; flex-wrap: wrap; border-bottom: 1px solid var(--rule); margin-bottom: 22px; }}
.strip div {{
  padding: 0 20px 12px 0; margin-right: 20px; border-right: 1px solid var(--rule-soft);
}}
.strip div:last-child {{ border-right: 0; }}
.strip .k {{
  font-size: 10px; letter-spacing: 0.13em; text-transform: uppercase;
  color: var(--ink-3); font-weight: 600; display: block; margin-bottom: 3px;
}}
.strip .v {{ font-family: 'IBM Plex Mono', monospace; font-size: 15px; font-weight: 500; color: var(--ink); }}
.strip .v small {{ color: var(--ink-3); font-size: 11px; }}

/* ---------- gauge / meters ---------- */
.meter {{ margin-bottom: 13px; }}
.meter .row {{ display: flex; justify-content: space-between; align-items: baseline; font-size: 12.5px; }}
.meter .row span {{ color: var(--ink-2); }}
.meter .row b {{ font-family: 'IBM Plex Mono', monospace; color: var(--c); font-weight: 600; }}
.meter .track {{ height: 5px; background: var(--rule-soft); border-radius: 3px; margin-top: 5px; position: relative; }}
.meter .track i {{ position: absolute; left: 0; top: 0; bottom: 0; background: var(--c); border-radius: 3px; }}

/* ---------- caveat / stamp ---------- */
.caveat {{
  font-size: 11.5px; color: var(--ink-3); line-height: 1.6;
  border-top: 1px solid var(--rule-soft); padding-top: 10px; margin-top: 6px;
}}
.caveat b {{ color: var(--rx); font-weight: 600; }}
.stamp {{
  display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: 10px;
  font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--c);
  border: 1.5px solid var(--c); padding: 3px 9px; border-radius: 2px;
  transform: rotate(-1.2deg); opacity: 0.88;
}}

/* ---------- streamlit furniture ---------- */
section[data-testid="stSidebar"] {{ background: var(--paper-warm); border-right: 1px solid var(--rule); }}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1.4rem; }}
section[data-testid="stSidebar"] h4 {{
  font-family: 'IBM Plex Sans', sans-serif !important; font-size: 10.5px !important;
  font-weight: 600 !important; letter-spacing: 0.15em; text-transform: uppercase;
  color: var(--ink-3) !important; border-bottom: 1px solid var(--rule);
  padding-bottom: 7px; margin: 20px 0 12px !important;
}}
section[data-testid="stSidebar"] label {{ font-size: 12.5px !important; color: var(--ink-2) !important; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 26px; border-bottom: 1px solid var(--rule); }}
.stTabs [data-baseweb="tab"] {{
  background: transparent !important; padding: 8px 0 11px; font-size: 11px;
  font-weight: 600; letter-spacing: 0.13em; text-transform: uppercase; color: var(--ink-3);
}}
.stTabs [aria-selected="true"] {{ color: var(--ink) !important; box-shadow: inset 0 -2px 0 var(--rx); }}
.stTabs [data-baseweb="tab-highlight"] {{ background: transparent !important; }}

div[data-testid="stMetricValue"] {{
  font-family: 'IBM Plex Mono', monospace; font-weight: 600; font-size: 1.5rem; color: var(--ink);
}}
div[data-testid="stMetricLabel"] p {{
  font-size: 10.5px !important; letter-spacing: 0.13em; text-transform: uppercase;
  color: var(--ink-3) !important; font-weight: 600;
}}
div[data-testid="stMetricDelta"] {{ font-size: 12px; }}

.stButton button {{
  border-radius: 3px; font-weight: 600; font-size: 13px; border: 1px solid var(--rule);
  background: var(--paper-bright); color: var(--ink);
  transition: background 120ms ease, border-color 120ms ease;
}}
.stButton button:hover {{ border-color: var(--ink-3); background: var(--paper-warm); color: var(--ink); }}
.stButton button[kind="primary"] {{ background: var(--ink); border-color: var(--ink); color: var(--paper); }}
.stButton button[kind="primary"]:hover {{ background: var(--rx); border-color: var(--rx); color: #fff; }}

div[data-testid="stExpander"] {{ border: 1px solid var(--rule-soft); border-radius: 3px; background: transparent; }}
div[data-testid="stExpander"] summary {{ font-size: 12.5px; color: var(--ink-2); }}
.stDataFrame, div[data-testid="stDataFrame"] {{ border: 1px solid var(--rule); border-radius: 3px; }}
div[data-testid="stAlert"] {{ border-radius: 3px; font-size: 13px; }}
.stSlider [data-baseweb="slider"] div[role="slider"] {{ background: var(--rx) !important; }}
.stCaption, .stCaption p {{ color: var(--ink-3) !important; font-size: 11.5px !important; }}

span[data-baseweb="tag"] {{
  background-color: var(--paper-warm) !important; border: 1px solid var(--rule) !important;
  color: var(--ink-2) !important; border-radius: 3px !important; font-size: 12px !important;
}}
span[data-baseweb="tag"] span[role="presentation"] svg {{ fill: var(--ink-3) !important; }}

{_nav_css(p)}

/* Inputs need explicit ink in the dark palette — BaseWeb defaults to light. */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
.stTextArea textarea, .stNumberInput input {{
  background-color: var(--paper-bright) !important;
  border-color: var(--rule) !important;
  color: var(--ink) !important;
}}
div[data-baseweb="popover"] li {{ background: var(--paper-bright) !important; color: var(--ink) !important; }}
div[data-baseweb="popover"] li:hover {{ background: var(--paper-warm) !important; }}

/* BaseWeb keeps light chrome on steppers, sliders and checkboxes regardless of
   the app theme, so they have to be told explicitly. */
.stNumberInput button, div[data-testid="stNumberInputStepUp"],
div[data-testid="stNumberInputStepDown"] {{
  background-color: var(--paper-warm) !important;
  border-color: var(--rule) !important; color: var(--ink-2) !important;
}}
.stNumberInput button svg {{ fill: var(--ink-2) !important; }}
div[data-testid="stFileUploaderDropzone"] {{
  background-color: var(--paper-warm) !important; border-color: var(--rule) !important;
}}
div[data-testid="stFileUploaderDropzone"] * {{ color: var(--ink-2) !important; }}
.stCheckbox svg {{ stroke: var(--paper) !important; }}
.stSlider [data-baseweb="slider"] [role="slider"] ~ div {{ color: var(--ink-2) !important; }}
div[data-baseweb="tab-panel"] {{ background: transparent !important; }}
.stExpander summary svg {{ fill: var(--ink-3) !important; }}
</style>
"""
