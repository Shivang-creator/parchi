#!/usr/bin/env python3
"""Screenshot the running app, tab by tab.

Streamlit renders over a websocket after page load, so Chrome's `--screenshot`
flag (which fires on the load event, and whose --virtual-time-budget breaks the
socket handshake entirely) captures only the loading skeleton. Playwright can
wait for real content instead.

Drives an already-installed Brave rather than downloading a browser.

    python tools/shoot.py                  # all tabs
    python tools/shoot.py Consult Surge    # named tabs only
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
URL = "http://localhost:8501"
OUT = Path("/tmp/shots")
TABS = ["Consult", "Day 3 · Culture", "Surge", "Escalation", "Method"]


def slug(name: str) -> str:
    return (
        name.lower().replace(" · ", "-").replace(" ", "-").replace("3", "3")
    )


def main() -> None:
    wanted = sys.argv[1:] or TABS
    OUT.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=BRAVE, args=["--no-sandbox"])
        page = browser.new_page(
            viewport={"width": 1500, "height": 1000},
            device_scale_factor=2,
            color_scheme="light",
        )
        page.goto(URL, wait_until="networkidle", timeout=90_000)

        # Wait for the app to actually paint, not just for the socket to open.
        page.wait_for_selector(".masthead", timeout=90_000)
        page.wait_for_timeout(4500)

        for name in wanted:
            if name != "Consult":
                page.get_by_role("tab", name=name).click()
                page.wait_for_timeout(4000)
            path = OUT / f"{slug(name)}.png"
            page.screenshot(path=str(path), full_page=True)
            print(f"  {path}  ({path.stat().st_size // 1024} KB)")

        browser.close()


if __name__ == "__main__":
    main()
