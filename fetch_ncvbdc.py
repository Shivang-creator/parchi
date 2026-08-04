#!/usr/bin/env python3
"""Pull real vector-borne disease burden from India's national programme.

The National Center for Vector Borne Diseases Control (NCVBDC), under the
Ministry of Health and Family Welfare, publishes the country's official
surveillance counts. Two series are reachable and machine-readable:

    Dengue    state x year cases and deaths, as an HTML table
              https://ncvbdc.mohfw.gov.in/  (Dengue situation in India)

    Malaria   district x year cases and deaths, as a 347-page PDF
              covering 2000 onward

This replaces the reconstructed burden figures the project shipped with
earlier. It matters: a forecast validated against invented data validates
nothing. Validated against the real national series, the backtest result is an
actual empirical claim.

Writes:
    data/burden_dengue.csv     state, year, cases, deaths, provisional
    data/burden_malaria.csv    state, year, cases            (if the PDF parses)
    data/burden_source.json    what was fetched, when, and from where

Usage:
    python fetch_ncvbdc.py                 # dengue only (fast)
    python fetch_ncvbdc.py --with-malaria  # also parse the PDF (slow, ~3 min)
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).parent / "data"
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}
DENGUE_URL = (
    "https://ncvbdc.mohfw.gov.in/index4.php?lang=1&level=0&linkid=431&lid=3715"
)
MALARIA_PDF = (
    "https://ncvbdc.mohfw.gov.in/WriteReadData/l892s/62270322291720010405.pdf"
)

# The site presents a certificate chain that some Python builds reject. This is
# a public, read-only government statistics page and the content is validated
# structurally after download, so relaxing verification here is acceptable —
# it would not be for anything carrying credentials.
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _get(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, context=_CTX, timeout=timeout) as response:
        return response.read()


def _cells(row_html: str) -> list[str]:
    return [
        " ".join(html.unescape(re.sub(r"<[^>]+>", " ", cell)).split())
        for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S | re.I)
    ]


def fetch_dengue() -> list[dict]:
    """State x year dengue cases and deaths.

    The table header carries the years; each year then occupies two columns,
    C (cases) and D (deaths), on a second header row. An asterisk on a year
    marks it provisional — the current year is always partial, and feeding a
    part-year total into a trend fit would read as a collapse in incidence.
    """
    page = _get(DENGUE_URL).decode("utf-8", "ignore")
    table = re.search(r"<table.*?</table>", page, re.S | re.I)
    if not table:
        raise RuntimeError("No table found on the NCVBDC dengue page")

    rows = re.findall(r"<tr.*?</tr>", table.group(0), re.S | re.I)
    header = _cells(rows[0])
    years = [y for y in header if re.fullmatch(r"\d{4}\*?", y)]
    if not years:
        raise RuntimeError(f"No year columns in header: {header}")

    records: list[dict] = []
    for row in rows[2:]:
        cells = _cells(row)
        if len(cells) < 3 or not re.fullmatch(r"\d+", cells[0] or ""):
            continue
        state = cells[1]
        numbers = [c for c in cells[2:] if re.fullmatch(r"[\d,]+", c or "")]
        for index, year in enumerate(years):
            if 2 * index + 1 >= len(numbers):
                continue
            records.append({
                "state": state,
                "year": int(year.rstrip("*")),
                "cases": int(numbers[2 * index].replace(",", "")),
                "deaths": int(numbers[2 * index + 1].replace(",", "")),
                "provisional": int(year.endswith("*")),
            })
    return records


def fetch_malaria() -> list[dict]:
    """State x year malaria cases, aggregated up from the district-wise PDF."""
    try:
        import pdfplumber
    except ImportError:
        print("  pdfplumber not installed; skipping malaria "
              "(pip install pdfplumber)")
        return []

    import collections
    import io

    print("  downloading the district-wise malaria PDF (~3 MB) ...", flush=True)
    blob = _get(MALARIA_PDF, timeout=180)

    totals: dict[tuple[str, int], int] = collections.defaultdict(int)
    current_year, last_state = None, None
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        print(f"  parsing {len(pdf.pages)} pages ...", flush=True)
        for index, page in enumerate(pdf.pages):
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 5:
                        continue
                    year, state, _district, cases, _deaths = (list(row) + [None] * 5)[:5]
                    if year and re.fullmatch(r"\s*(19|20)\d{2}\s*", str(year)):
                        current_year = int(str(year).strip())
                    if state and str(state).strip():
                        last_state = str(state).replace("\n", " ").strip()
                    try:
                        count = int(str(cases).replace(",", "").strip())
                    except (TypeError, ValueError):
                        continue
                    if current_year and last_state:
                        totals[(last_state, current_year)] += count
            if index % 60 == 0:
                print(f"    page {index} ...", flush=True)

    return [
        {"state": state, "year": year, "cases": count}
        for (state, year), count in sorted(totals.items())
    ]


def _write(name: str, rows: list[dict], note: str) -> None:
    path = DATA / name
    with path.open("w", newline="") as fh:
        fh.write(f"# {note}\n")
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {name:26} {len(rows):>6} rows")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-malaria", action="store_true")
    args = parser.parse_args()

    DATA.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    source = {"fetched_utc": stamp, "series": {}}

    print("Fetching real NCVBDC burden data ->", DATA)

    dengue = fetch_dengue()
    _write(
        "burden_dengue.csv", dengue,
        f"REAL DATA. State-wise dengue cases and deaths, National Center for "
        f"Vector Borne Diseases Control (NCVBDC), Ministry of Health and Family "
        f"Welfare, Government of India. Retrieved {stamp} from {DENGUE_URL}. "
        f"provisional=1 marks a part-year total.",
    )
    complete = [r for r in dengue if not r["provisional"]]
    source["series"]["dengue"] = {
        "url": DENGUE_URL, "records": len(dengue),
        "states": len({r["state"] for r in dengue}),
        "years": sorted({r["year"] for r in dengue}),
        "complete_years": sorted({r["year"] for r in complete}),
    }

    if args.with_malaria:
        malaria = fetch_malaria()
        if malaria:
            _write(
                "burden_malaria.csv", malaria,
                f"REAL DATA. Malaria cases aggregated from district-wise NCVBDC "
                f"records, Ministry of Health and Family Welfare, Government of "
                f"India. Retrieved {stamp} from {MALARIA_PDF}.",
            )
            source["series"]["malaria"] = {
                "url": MALARIA_PDF, "records": len(malaria),
                "states": len({r["state"] for r in malaria}),
                "years": sorted({r["year"] for r in malaria}),
            }

    (DATA / "burden_source.json").write_text(json.dumps(source, indent=2))
    print("  burden_source.json         provenance manifest")


if __name__ == "__main__":
    main()
