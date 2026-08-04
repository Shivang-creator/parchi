#!/usr/bin/env python3
"""Verify the deployed app the way a judge will actually meet it.

An HTTP 200 proves nothing here: Streamlit renders over a websocket after page
load, and a private app answers 200 with an auth redirect loop. This loads the
real URL in a fresh anonymous browser context, waits for the masthead, walks
every stop, and asserts that specific expected content is on the page.

    python tools/verify_live.py [url]
"""

from __future__ import annotations

import sys
import time

from playwright.sync_api import sync_playwright

BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
URL = sys.argv[1] if len(sys.argv) > 1 else "https://parchi-india.streamlit.app"
STOPS = ["Reception", "Doctor", "Pharmacy", "Hospital", "Method"]
PROBES = {
    "Doctor": ["CREATININE CLEARANCE", "EXPECTED COVERAGE", "WILL IT WORK"],
    "Pharmacy": ["DAYS OF INCOME", "abandonment risk"],
    "Hospital": ["Peak month", "Peak to trough"],
    "Reception": ["VITALS AT THE WINDOW", "NEWS2"],
    "Method": ["Provenance", "Data layer"],
}


def main() -> None:
    failures = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=BRAVE, args=["--no-sandbox"])
        # Fresh context with no storage = exactly what an anonymous judge gets.
        context = browser.new_context(viewport={"width": 1560, "height": 1000})
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)[:140]))

        started = time.time()
        page.goto(URL, wait_until="domcontentloaded", timeout=180_000)
        page.wait_for_selector(".masthead", timeout=180_000)
        print(f"  first paint      {time.time() - started:5.1f}s   {page.url}")
        print(f"  title            {page.title()}")
        page.wait_for_timeout(5000)

        for index, name in enumerate(STOPS):
            page.locator(".st-key-railnav button").nth(index).click()
            page.wait_for_timeout(5500)
            text = " ".join(page.inner_text("body").split())
            missing = [p for p in PROBES.get(name, []) if p not in text]
            status = "OK  " if not missing else "MISS"
            print(f"  {status} {name:11} {len(text):>6} chars"
                  + (f"   missing: {missing}" if missing else ""))
            if missing:
                failures.append((name, missing))

        page.get_by_role("button", name="Ink theme").click()
        page.wait_for_timeout(4000)
        dark_ok = page.get_by_role("button", name="Paper theme").count() > 0
        print(f"  {'OK  ' if dark_ok else 'FAIL'} Ink theme toggles")
        if not dark_ok:
            failures.append(("theme", ["toggle"]))

        page.screenshot(path="/tmp/live_final.png", full_page=False)
        print(f"  js errors        {errors or 'none'}")
        browser.close()

    print()
    print("  VERDICT:", "live and complete" if not failures
          else f"{len(failures)} problem(s): {failures}")


if __name__ == "__main__":
    main()
