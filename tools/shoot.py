#!/usr/bin/env python3
"""Screenshot the running app, stop by stop, in either palette.

Streamlit renders over a websocket after page load, so Chrome's `--screenshot`
flag captures only the loading skeleton (and its --virtual-time-budget breaks
the socket handshake outright). Playwright can wait for real content.

Drives an already-installed Brave rather than downloading a browser.

    python tools/shoot.py                       # every stop, Paper
    python tools/shoot.py --theme Ink           # every stop, Ink
    python tools/shoot.py Doctor Pharmacy       # named stops only
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
URL = "http://localhost:8501"
OUT = Path("/tmp/shots")
STOPS = ["Reception", "Doctor", "Pharmacy", "Hospital", "Method"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stops", nargs="*", default=None)
    parser.add_argument("--theme", choices=["Paper", "Ink"], default="Paper")
    parser.add_argument("--suffix", default="")
    args = parser.parse_args()

    wanted = args.stops or STOPS
    OUT.mkdir(exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=BRAVE, args=["--no-sandbox"])
        page = browser.new_page(
            viewport={"width": 1560, "height": 1000},
            device_scale_factor=2,
            color_scheme="dark" if args.theme == "Ink" else "light",
        )
        page.goto(URL, wait_until="networkidle", timeout=90_000)
        page.wait_for_selector(".masthead", timeout=90_000)
        page.wait_for_timeout(4000)

        # The toggle names the palette you would switch TO, so it reads
        # "Ink theme" while Paper is active.
        if args.theme == "Ink":
            page.get_by_role("button", name="Ink theme").click()
            # A theme switch is a full rerun; wait for the toggle to flip its
            # own label rather than guessing at a delay.
            page.get_by_role("button", name="Paper theme").wait_for(timeout=60_000)
            page.wait_for_timeout(2500)

        # Select by position in the rail, not by accessible name: the CSS
        # ::after subtitle is folded into the computed name, so "Reception" is
        # really "Reception triage the queue" to an accessibility query.
        for name in wanted:
            index = STOPS.index(name)
            button = page.locator(".st-key-railnav button").nth(index)
            button.wait_for(timeout=60_000)
            button.click()
            page.wait_for_timeout(5000)
            path = OUT / f"{name.lower()}{args.suffix}.png"
            page.screenshot(path=str(path), full_page=True)
            print(f"  {path}  ({path.stat().st_size // 1024} KB)")

        browser.close()


if __name__ == "__main__":
    main()
