"""
Scrape all current pet listings from starpets.gg.

Fixed: keeps ALL listings per (variant, name) instead of deduplicating to lowest,
so we can analyze market depth.
"""
import json
import time
import sys
import requests
from pathlib import Path

API_BASE = "https://starpets.gg/api/v1/products"
GAME_ID = 1  # Adopt Me

# Variant determination
# Adopt Me API returns: pumping (default/neon/mega), flyable (bool), rideable (bool)
def variant_code(p):
    pumping = (p.get("pumping") or "default").lower()
    fly = bool(p.get("flyable"))
    ride = bool(p.get("rideable"))

    if pumping == "default":
        if not fly and not ride:
            return "Normal"
        suffix = ("F" if fly else "") + ("R" if ride else "")
        return suffix  # F, R, or FR
    elif pumping == "neon":
        suffix = ("F" if fly else "") + ("R" if ride else "")
        return "N" + suffix  # N, NF, NR, NFR
    elif pumping == "mega":
        suffix = ("F" if fly else "") + ("R" if ride else "")
        return "M" + suffix  # M, MF, MR, MFR
    return "Unknown"


def fetch_page(page, retries=3):
    """Fetch one page of listings."""
    params = {
        "game_id": GAME_ID,
        "page": page,
        "per_page": 100,
        "category": "pet",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; pet-price-tracker/1.0)",
        "Accept": "application/json",
    }
    for attempt in range(retries):
        try:
            r = requests.get(API_BASE, params=params, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  Retry {attempt+1} for page {page}: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)


def scrape_all():
    """Scrape every page of pet listings."""
    all_listings = []
    page = 1
    while True:
        print(f"Fetching page {page}...", file=sys.stderr)
        data = fetch_page(page)
        items = data.get("data", []) if isinstance(data, dict) else data
        if not items:
            break

        for p in items:
            name = (p.get("name") or "").strip()
            price = p.get("price")
            if not name or price is None:
                continue
            try:
                price = float(price)
            except (ValueError, TypeError):
                continue
            all_listings.append({
                "name": name,
                "variant": variant_code(p),
                "price": price,
                "id": p.get("id"),
            })

        # Pagination — break if we got fewer than per_page items
        if len(items) < 100:
            break
        page += 1
        time.sleep(1)  # Be polite

    return all_listings


def main():
    listings = scrape_all()
    print(f"Scraped {len(listings)} total listings", file=sys.stderr)
    output = Path(__file__).resolve().parent.parent / "raw_prices.json"
    output.write_text(json.dumps(listings, indent=2))
    print(f"Wrote {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
