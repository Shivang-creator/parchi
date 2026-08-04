#!/usr/bin/env python3
"""Pull real health facilities from OpenStreetMap for the escalation map.

Extends the Overpass fetcher originally written for a civic health-mapping
project. The addition here is TIER CLASSIFICATION: a facility's name in India
reliably encodes what it is allowed to do, and the Indian Public Health
Standards define exactly what each tier must be able to provide.

    Sub-centre        first aid, referral only
    PHC               outpatient, basic obstetrics, no surgery, no blood
    CHC               emergency surgery, blood storage, 24h obstetrics
    District Hospital blood bank, ICU, most emergency surgery
    Medical College   cath lab, neurosurgery, everything above

That mapping is what makes "nearest hospital" the wrong question. A stroke or
a myocardial infarction needs a specific capability, not a signboard.

Usage:  python fetch_facilities.py            # default region
        python fetch_facilities.py --radius 80000
"""

from __future__ import annotations

import argparse
import csv
import json
import ssl
import urllib.parse
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # pragma: no cover - offline fallback
    SSL_CTX = ssl._create_unverified_context()

OVERPASS = "https://overpass-api.de/api/interpreter"
UA = "Parchi/1.0 (hackathon prototype; health facility mapping)"

# Anchors chosen to give a realistic mix of urban tertiary care and genuinely
# rural catchment — the contrast is the whole point of the analysis.
REGIONS = {
    # Kerala has the strongest public health system in India. Including it is
    # the control: if a gap shows up even here, it is real everywhere.
    "kerala": [
        ("Kollam", "Kerala", 8.8932, 76.6141),
        ("Pathanamthitta", "Kerala", 9.2648, 76.7870),
        ("Idukki", "Kerala", 9.8497, 76.9681),
    ],
    # Districts at the other end of the distribution — large, rural, tribal,
    # and among the least served in the country.
    "underserved": [
        ("Gadchiroli", "Maharashtra", 20.1809, 80.0033),
        ("Jagdalpur", "Chhattisgarh", 19.0748, 82.0231),
        ("Malkangiri", "Odisha", 18.3479, 81.8880),
        ("Sitamarhi", "Bihar", 26.5950, 85.4899),
    ],
}

TIER_RULES = [
    # (keywords, tier, rank) — checked in order, most specific first
    (("medical college", "aiims", "institute of medical", "super speciality",
      "superspeciality", "medical sciences"), "Medical College", 5),
    (("district hospital", "general hospital", "govt. hospital",
      "government hospital", "taluk hospital", "civil hospital"), "District Hospital", 4),
    (("community health", " chc", "chc ", "community health centre"), "CHC", 3),
    (("primary health", " phc", "phc ", "primary health centre",
      "family health"), "PHC", 2),
    (("sub centre", "sub-centre", "subcentre", "health centre"), "Sub-centre", 1),
]

# What each tier can actually do, per IPHS norms.
#
# IMPORTANT: capability is only inferred for the PUBLIC tiers, where IPHS
# defines a mandated service package. OpenStreetMap tags a one-doctor nursing
# home and a 900-bed tertiary centre identically as amenity=hospital, so
# crediting every private facility with an ICU would be fiction. Private
# facilities are recorded with NO inferred capability unless the name itself
# carries a scale marker. The honest statement is that open data can describe
# the public system and cannot describe the private one.
CAPABILITY = {
    "Sub-centre": [],
    "Clinic": [],
    "Private Clinic / Nursing home": [],
    "PHC": ["Outpatient care", "Normal delivery"],
    "CHC": ["Outpatient care", "Normal delivery", "Emergency surgery",
            "Caesarean section", "Blood storage"],
    "District Hospital": ["Outpatient care", "Normal delivery", "Emergency surgery",
                          "Caesarean section", "Blood storage", "Blood bank",
                          "Intensive care", "Dialysis"],
    "Medical College": ["Outpatient care", "Normal delivery", "Emergency surgery",
                        "Caesarean section", "Blood storage", "Blood bank",
                        "Intensive care", "Dialysis", "Cardiac catheterisation",
                        "Neurosurgery", "Stroke thrombolysis"],
    "Private Multispeciality": ["Outpatient care", "Emergency surgery",
                                "Caesarean section", "Intensive care"],
}

# Only a private facility naming itself at this scale gets credited with
# surgical and critical-care capability.
SCALE_MARKERS = (
    "multi speciality", "multispeciality", "multi-speciality",
    "super speciality", "superspeciality", "super-speciality",
    "medical centre", "medical center", "institute", "trust hospital",
    "mission hospital", "memorial hospital", "apollo", "fortis", "manipal",
    "kims", "amrita", "aster", "narayana",
)


def classify(name: str, tags: dict) -> tuple[str, int]:
    lowered = f" {name.lower()} "
    for keywords, tier, rank in TIER_RULES:
        if any(k in lowered for k in keywords):
            return tier, rank
    if tags.get("amenity") == "hospital":
        if any(marker in lowered for marker in SCALE_MARKERS):
            return "Private Multispeciality", 4
        return "Private Clinic / Nursing home", 2
    return "Clinic", 1


def query(lat: float, lon: float, radius: int) -> list[dict]:
    q = f"""
    [out:json][timeout:60];
    (
      node["amenity"~"hospital|clinic|doctors"](around:{radius},{lat},{lon});
      way["amenity"~"hospital|clinic"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    request = urllib.request.Request(
        OVERPASS,
        data=urllib.parse.urlencode({"data": q}).encode(),
        headers={"User-Agent": UA},
    )
    with urllib.request.urlopen(request, context=SSL_CTX, timeout=90) as response:
        return json.loads(response.read().decode())["elements"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=int, default=45000)
    parser.add_argument("--out", default="data/facilities.csv")
    parser.add_argument("--regions", nargs="*", default=list(REGIONS),
                        choices=list(REGIONS))
    parser.add_argument("--retries", type=int, default=3,
                        help="Overpass is a free shared endpoint and 504s often.")
    args = parser.parse_args()

    anchors = [a for region in args.regions for a in REGIONS[region]]
    seen: set[tuple] = set()
    rows: list[dict] = []

    for city, state, lat, lon in anchors:
        print(f"  fetching {city}, {state} (r={args.radius}m) ...", flush=True)
        elements = None
        for attempt in range(1, args.retries + 1):
            try:
                elements = query(lat, lon, args.radius)
                break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                print(f"    attempt {attempt}/{args.retries} failed: {exc}")
                if attempt < args.retries:
                    time.sleep(6 * attempt)
        if elements is None:
            print("    giving up on this anchor")
            continue

        kept = 0
        for element in elements:
            tags = element.get("tags", {})
            name = tags.get("name")
            if not name:
                continue
            plat = element.get("lat") or element.get("center", {}).get("lat")
            plon = element.get("lon") or element.get("center", {}).get("lon")
            if plat is None or plon is None:
                continue

            key = (round(plat, 4), round(plon, 4))
            if key in seen:
                continue
            seen.add(key)

            tier, rank = classify(name, tags)
            rows.append(
                {
                    "name": name,
                    "tier": tier,
                    "tier_rank": rank,
                    "state": state,
                    "anchor": city,
                    "latitude": round(float(plat), 6),
                    "longitude": round(float(plon), 6),
                    "capabilities": "|".join(CAPABILITY.get(tier, [])),
                }
            )
            kept += 1
        print(f"    kept {kept}")
        time.sleep(3)  # be polite to a free, shared, unauthenticated endpoint

    if not rows:
        print("No facilities fetched — leaving any existing file untouched.")
        return

    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as fh:
        fh.write("# Live OpenStreetMap extract. Tier inferred from facility name;\n")
        fh.write("# capabilities follow Indian Public Health Standards for that tier.\n")
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} facilities to {out}")
    from collections import Counter

    for tier, count in Counter(r["tier"] for r in rows).most_common():
        print(f"  {tier:20} {count}")


if __name__ == "__main__":
    import urllib.parse  # noqa: E402  (kept local to the CLI path)

    main()
