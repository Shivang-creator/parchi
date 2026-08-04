"""Reusable pieces of the paper.

Every bit of raw HTML in Parchi is built here, so the screens stay readable
and the markup stays consistent. If a component needs a colour it takes one —
none of these decide policy.
"""

from __future__ import annotations

import html

from . import theme


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def label(text: str) -> str:
    return f'<span class="label">{_esc(text)}</span>'


def rule(soft: bool = False) -> str:
    return f'<hr class="{"rule-soft" if soft else "rule"}">'


def masthead(standfirst: str, left: str, right: str) -> str:
    return (
        '<div class="masthead">'
        '<div class="wordmark"><span class="deva">पर्ची</span>Parchi</div>'
        f'<div class="standfirst">{standfirst}</div>'
        "</div>"
        f'<div class="masthead-sub"><span>{_esc(left)}</span>'
        f"<span>{_esc(right)}</span></div>"
    )


def patient_strip(fields: list[tuple[str, str, str]]) -> str:
    """fields: (label, value, sub) — sub may be empty."""
    cells = "".join(
        f'<div><span class="k">{_esc(k)}</span>'
        f'<span class="v">{_esc(v)}'
        f'{f" <small>{_esc(s)}</small>" if s else ""}</span></div>'
        for k, v, s in fields
    )
    return f'<div class="strip">{cells}</div>'


def slip(
    drug: str,
    sig: str,
    who: str,
    why: str,
    accent: str,
    adjuncts: list[str] | None = None,
    marks: list[tuple[str, str]] | None = None,
) -> str:
    """The prescription itself — the one thing on screen that must dominate.

    `marks` are the small facts a pharmacist reads off the foot of a slip
    (spectrum, AWaRe class, route), rendered against a dotted signature rule so
    the card reads as a document rather than a widget.
    """
    extra = "".join(f'<div class="adjunct">{_esc(a)}</div>' for a in (adjuncts or []))
    mark_html = "".join(
        f"<div>{_esc(k)} &nbsp;<b>{v}</b></div>" for k, v in (marks or [])
    )
    return (
        f'<div class="slip" style="--accent:{accent}">'
        f'<div class="slip-head"><span class="rx">&#8478;</span>'
        f'<span class="who">{who}</span></div>'
        f'<div class="drug">{_esc(drug)}</div>'
        f'<div class="sig">{_esc(sig)}</div>'
        f"{extra}"
        f'<div class="why">{why}</div>'
        f'<div class="slip-foot"><div class="marks">{mark_html}</div>'
        f'<div class="sign"><i></i><span>Signature</span></div></div>'
        "</div>"
    )


def verdict(value: float, caption: str, colour: str, target: float | None = None) -> str:
    """The headline number, with the bar it has to clear drawn on the scale."""
    marker = (
        f'<u style="left:{min(max(target * 100, 0), 100):.1f}%"></u>'
        if target is not None else ""
    )
    return (
        f'<div class="verdict" style="--c:{colour}">'
        f'{label("Expected coverage")}'
        f'<div class="n">{value:.0f}<span class="pct">%</span></div>'
        f'<div class="bar"><i style="width:{min(max(value, 0), 100):.1f}%"></i>{marker}</div>'
        f'<div class="say">{caption}</div>'
        "</div>"
    )


def checks(items: list[tuple[str, str, str, str]]) -> str:
    """items: (question, answer, note, colour) — one row, however many checks."""
    cells = "".join(
        f'<div class="check" style="--c:{c}">'
        f'<div class="q">{_esc(q)}</div>'
        f'<div class="a">{_esc(a)}</div>'
        f'<div class="n">{n}</div>'
        "</div>"
        for q, a, n, c in items
    )
    return f'<div class="checks" style="--cols:{len(items)}">{cells}</div>'


def note(tag: str, heading: str, body: str, colour: str | None = None) -> str:
    """A margin annotation. Deliberately not a filled alert box."""
    c = colour or theme.severity_colors().get(tag, theme.INK_3)
    return (
        f'<div class="note" style="--c:{c}">'
        f'<div class="h"><span class="tag">{_esc(tag)}</span>{_esc(heading)}</div>'
        f'<div class="b">{body}</div>'
        "</div>"
    )


def stamp(text: str, colour: str) -> str:
    return f'<span class="stamp" style="--c:{colour}">{_esc(text)}</span>'


def caveat(text: str) -> str:
    return f'<div class="caveat">{text}</div>'


def aware_mark(aware: str) -> str:
    """WHO AWaRe classification, coloured by how hard we should be avoiding it."""
    colour = theme.aware_colors().get(aware, theme.INK_3)
    return f'<span style="color:{colour};font-weight:600">{_esc(aware)}</span>'


# --------------------------------------------------------------------------
# Icons — inline line-art SVG, so they inherit ink and need no network
# --------------------------------------------------------------------------
# Deliberately not emoji: emoji are somebody else's illustration style,
# they render differently on every platform, and they cannot take the ink
# colour. These are 1.5px strokes on a 24-unit grid, matching the hairlines.
_ICONS = {
    "reception": "<path d='M4 20V7l8-3 8 3v13'/><path d='M9 20v-5h6v5'/><path d='M4 20h16'/>",
    "doctor": "<path d='M8 3v5a4 4 0 0 0 8 0V3'/><path d='M12 12v3a5 5 0 0 0 10 0v-1'/>"
              "<circle cx='22' cy='12' r='1.6'/>",
    "pharmacy": "<rect x='3' y='9' width='18' height='12' rx='2'/>"
                "<path d='M7 9V6a5 5 0 0 1 10 0v3'/><path d='M12 12v6M9 15h6'/>",
    "hospital": "<path d='M3 21V8l9-5 9 5v13'/><path d='M12 10v6M9 13h6'/>",
    "method": "<path d='M4 4h9a3 3 0 0 1 3 3v13a2.5 2.5 0 0 0-2.5-2.5H4z'/>"
              "<path d='M20 4h-2a3 3 0 0 0-3 3v13a2.5 2.5 0 0 1 2.5-2.5H20z'/>",
    "sun": "<circle cx='12' cy='12' r='4'/><path d='M12 2v2M12 20v2M2 12h2M20 12h2"
           "M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4'/>",
    "moon": "<path d='M21 13.2A9 9 0 1 1 10.8 3a7 7 0 0 0 10.2 10.2z'/>",
    "clock": "<circle cx='12' cy='12' r='9'/><path d='M12 7v5l3 2'/>",
    "rupee": "<path d='M6 4h12M6 9h12M16 4c0 4-3 5-6 5l7 10'/><path d='M6 9h4'/>",
    "alert": "<path d='M12 3l9.5 17H2.5z'/><path d='M12 10v4M12 17.5v.01'/>",
    "pin": "<path d='M12 21s7-6.3 7-11a7 7 0 1 0-14 0c0 4.7 7 11 7 11z'/>"
           "<circle cx='12' cy='10' r='2.5'/>",
}


def icon(name: str, size: int = 16, colour: str | None = None) -> str:
    """A line-art glyph that inherits ink rather than importing a font."""
    body = _ICONS.get(name)
    if not body:
        return ""
    stroke = colour or "currentColor"
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' "
        f"stroke='{stroke}' stroke-width='1.5' stroke-linecap='round' "
        f"stroke-linejoin='round' style='vertical-align:-2px'>{body}</svg>"
    )


def rail(stops: list[tuple[str, str, str, str]], active: str) -> str:
    """The journey rail — reception, doctor, pharmacy, and the wider hospital.

    stops: (key, icon name, title, subtitle). The rail exists because the
    screens are not five unrelated tools; they are four points on one patient's
    walk through a building, and the navigation should say so.
    """
    cells = []
    seen_active = False
    for key, glyph, title, subtitle in stops:
        if key == active:
            state, seen_active = "on", True
        else:
            state = "done" if not seen_active else ""
        cells.append(
            f'<div class="stop {state}">'
            f'<div class="n">{icon(glyph, 15)}</div>'
            f'<div class="t">{_esc(title)}</div>'
            f'<div class="d">{_esc(subtitle)}</div>'
            "</div>"
        )
    return f'<div class="rail">{"".join(cells)}</div>'


def meter(label: str, value: float, maximum: float, colour: str,
          display: str | None = None, sub: str = "") -> str:
    """A labelled horizontal bar. Reads faster than a number in a box."""
    pct = 0.0 if maximum <= 0 else min(max(value / maximum, 0.0), 1.0) * 100
    shown = display if display is not None else f"{value:,.0f}"
    return (
        f'<div class="meter" style="--c:{colour}">'
        f'<div class="row"><span>{_esc(label)}</span><b>{_esc(shown)}</b></div>'
        f'<div class="track"><i style="width:{pct:.1f}%"></i></div>'
        + (f'<div style="font-size:11px;color:var(--ink-3);margin-top:4px">{sub}</div>'
           if sub else "")
        + "</div>"
    )


def spectrum_mark(spectrum: int) -> str:
    """Five bands, narrow to last-line. Filled squares read faster than a number."""
    filled = "▪" * spectrum
    empty = "▫" * (5 - spectrum)
    colour = theme.SAFE if spectrum <= 2 else theme.CAUTION if spectrum <= 4 else theme.RX
    return f'<span style="color:{colour};letter-spacing:1px">{filled}{empty}</span>'
