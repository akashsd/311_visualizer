"""
Sample script for exploring CARB's air quality & emissions data page.

NOTE: This was written WITHOUT being able to read the page (my sandbox was
blocked / got a 419 from the site), so the endpoint details are NOT verified.
Workflow:
  1. Run `python carb_query.py discover`  -> lists data-related links on the page.
  2. Pick the endpoint/file you want, then run
     `python carb_query.py query <URL> [key=value ...]`
     e.g. python carb_query.py query https://example.carb.endpoint/data.csv year=2024

Shortcuts: `python carb_query.py epa` and `python carb_query.py carb` run the
sample values defined near the top of this file.

Requires: pip install requests
"""

import re
import sys
from urllib.parse import urljoin

import requests

PAGE_URL = "https://ww2.arb.ca.gov/capp/cst/rdi/air-quality-and-emissions-data"

# ---- Sample values (edit these) --------------------------------------------
# UNVERIFIED guess: replace with the real endpoint printed by `discover`.
CARB_URL = "https://ww2.arb.ca.gov/REPLACE-WITH-ENDPOINT-FROM-DISCOVER"
CARB_PARAMS = {"pollutant": "PM25", "site": "Los Angeles", "start": "2024-01-01", "end": "2024-01-31"}

# Documented alternative that works today (CA monitors, incl. CARB-operated):
# EPA AQS API. Free key: GET https://aqs.epa.gov/data/api/signup?email=YOU@example.com
# then use the key emailed to you. Param 88101 = PM2.5, state 06 = California.
EPA_URL = "https://aqs.epa.gov/data/api/dailyData/byState"
EPA_PARAMS = {"email": "YOU@example.com", "key": "YOUR_KEY", "param": "88101",
              "bdate": "20240101", "edate": "20240131", "state": "06"}

# Identify yourself honestly. If the site rejects this (e.g. HTTP 419/403),
# email webmaster@arb.ca.gov rather than spoofing a browser.
HEADERS = {"User-Agent": "carb-data-exploration-script/0.1 (personal, low-volume)"}


def discover():
    """Fetch the page and print links that look data/API related."""
    resp = requests.get(PAGE_URL, headers=HEADERS, timeout=30)
    print(f"HTTP {resp.status_code}, {len(resp.text)} bytes")
    if resp.status_code != 200:
        print("Page body:", resp.text[:300])
        return

    # Crude link extraction: (href, link text) pairs.
    links = re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.S | re.I)
    keywords = re.compile(r"api|data|csv|download|query|aqs|monitor|emission|json", re.I)
    seen = set()
    for href, text in links:
        text = re.sub(r"<[^>]+>", "", text).strip()
        url = urljoin(PAGE_URL, href)
        if url in seen or not keywords.search(url + " " + text):
            continue
        seen.add(url)
        print(f"- {text[:70]!r}\n    {url}")


def query(url, params):
    """GET an endpoint with query params and preview the response."""
    resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
    print("Requested:", resp.url)          # shows the final URL with params
    print(f"HTTP {resp.status_code}  Content-Type: {resp.headers.get('Content-Type')}")
    resp.raise_for_status()                # stop on 4xx/5xx

    ctype = resp.headers.get("Content-Type", "")
    if "json" in ctype:
        data = resp.json()
        print(type(data).__name__, "with", len(data), "top-level items")
        print(str(data)[:1000])            # preview first 1000 chars
    else:
        # CSV / text: print the first few lines
        for line in resp.text.splitlines()[:10]:
            print(line)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("discover", "query", "epa", "carb"):
        print(__doc__)
    elif sys.argv[1] == "epa":      # run the sample EPA AQS query above
        query(EPA_URL, EPA_PARAMS)
    elif sys.argv[1] == "carb":     # run the sample CARB query above
        query(CARB_URL, CARB_PARAMS)
    elif sys.argv[1] == "discover":
        discover()
    else:
        # Remaining args after the URL are key=value query params.
        extra = dict(arg.split("=", 1) for arg in sys.argv[3:])
        query(sys.argv[2], extra)
