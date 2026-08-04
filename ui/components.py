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
    """items: (question, answer, note, colour) — always four, always in a row."""
    cells = "".join(
        f'<div class="check" style="--c:{c}">'
        f'<div class="q">{_esc(q)}</div>'
        f'<div class="a">{_esc(a)}</div>'
        f'<div class="n">{n}</div>'
        "</div>"
        for q, a, n, c in items
    )
    return f'<div class="checks">{cells}</div>'


def note(tag: str, heading: str, body: str, colour: str | None = None) -> str:
    """A margin annotation. Deliberately not a filled alert box."""
    c = colour or theme.SEVERITY_COLOR.get(tag, theme.INK_3)
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
    colour = theme.AWARE_COLOR.get(aware, theme.INK_3)
    return f'<span style="color:{colour};font-weight:600">{_esc(aware)}</span>'


def spectrum_mark(spectrum: int) -> str:
    """Five bands, narrow to last-line. Filled squares read faster than a number."""
    filled = "▪" * spectrum
    empty = "▫" * (5 - spectrum)
    colour = theme.SAFE if spectrum <= 2 else theme.CAUTION if spectrum <= 4 else theme.RX
    return f'<span style="color:{colour};letter-spacing:1px">{filled}{empty}</span>'
