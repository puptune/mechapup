"""
Combine scraped prices with the static value list.

For each (variant, pet), compute:
- lowest_price (the floor)
- median_price (to filter outliers)
- listing_count (liquidity proxy)
- value (from correct column based on variant)
- value_per_dollar (the ratio)

Also compute Neon→Mega arbitrage opportunities.

Outputs `data.json` for the frontend.
"""
import json
import re
import statistics
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent

# Map variant to which column of (no_pot, fr, nfr, mfr) gives its value
VARIANT_COL = {
    "Normal": 0,
    "F": 1, "R": 1, "FR": 1,
    "N": 2, "NF": 2, "NR": 2, "NFR": 2,
    "M": 3, "MF": 3, "MR": 3, "MFR": 3,
}


def normalize(name):
    return name.lower().replace(".", "").replace("-", " ").replace("'", "").strip()


def load_values():
    """Parse values.txt → {normalized_name: (canonical, (no_pot, fr, nfr, mfr))}."""
    values = {}
    path = ROOT / "values.txt"
    with path.open() as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = re.split(r"\t+", line)
            if len(parts) < 5:
                continue
            name = parts[0].strip()
            # Fix doubled-name artifacts (e.g. "Cat Cat" → "Cat")
            w = name.split()
            h = len(w) // 2
            if len(w) % 2 == 0 and w[:h] == w[h:]:
                name = " ".join(w[:h])
            try:
                values[normalize(name)] = (name, tuple(float(p) for p in parts[1:5]))
            except ValueError:
                pass
    return values


def load_listings():
    return json.loads((ROOT / "raw_prices.json").read_text())


def aggregate(listings, values):
    """Group listings by (variant, name), compute stats, attach value."""
    groups = {}
    for it in listings:
        groups.setdefault((it["variant"], it["name"]), []).append(it["price"])

    rows = []
    for (variant, name), prices in groups.items():
        norm = normalize(name)
        if norm not in values:
            continue
        canonical, vals = values[norm]
        col = VARIANT_COL.get(variant)
        if col is None:
            continue
        value = vals[col]
        if value <= 0:
            continue

        prices_sorted = sorted(prices)
        lowest = prices_sorted[0]
        rows.append({
            "name": canonical,
            "variant": variant,
            "lowest_price": round(lowest, 2),
            "median_price": round(statistics.median(prices_sorted), 2),
            "listing_count": len(prices_sorted),
            "value": value,
            "value_per_dollar": round(value / lowest, 2) if lowest > 0 else 0,
            "no_pot_val": vals[0],
            "fr_val": vals[1],
            "nfr_val": vals[2],
            "mfr_val": vals[3],
        })
    return rows


def compute_arbitrage(rows):
    """For each pet, compute the 4-Neon-combine vs direct-Mega path."""
    # Index by (variant, name)
    idx = {(r["variant"], r["name"]): r for r in rows}
    arbs = []
    for (n_var, m_var) in [("N", "M"), ("NF", "MF"), ("NR", "MR"), ("NFR", "MFR")]:
        for r in rows:
            if r["variant"] != n_var:
                continue
            mkey = (m_var, r["name"])
            if mkey not in idx:
                continue
            mrow = idx[mkey]
            cost_4n = 4 * r["lowest_price"]
            m_price = mrow["lowest_price"]
            if cost_4n <= 0:
                continue
            arbs.append({
                "name": r["name"],
                "pair": f"{n_var}→{m_var}",
                "n_price": r["lowest_price"],
                "cost_4n": round(cost_4n, 2),
                "m_price": m_price,
                "savings": round(m_price - cost_4n, 2),
                "savings_pct": round((m_price - cost_4n) / m_price * 100, 1) if m_price > 0 else 0,
                "m_value": mrow["value"],
                "combine_ratio": round(mrow["value"] / cost_4n, 2),
                "direct_ratio": round(mrow["value"] / m_price, 2) if m_price > 0 else 0,
                "n_listings": r["listing_count"],
                "m_listings": mrow["listing_count"],
            })
    return arbs


def main():
    print("Loading values...")
    values = load_values()
    print(f"  {len(values)} pets in value list")

    print("Loading listings...")
    listings = load_listings()
    print(f"  {len(listings)} raw listings")

    print("Aggregating...")
    rows = aggregate(listings, values)
    print(f"  {len(rows)} (variant, pet) combinations matched")

    print("Computing arbitrage...")
    arbs = compute_arbitrage(rows)
    print(f"  {len(arbs)} N→M combine paths analyzed")

    # Sort everything by best ratio first
    rows.sort(key=lambda r: -r["value_per_dollar"])
    arbs.sort(key=lambda a: -a["combine_ratio"])

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "deals": rows,
        "arbitrage": arbs,
    }
    (ROOT / "data.json").write_text(json.dumps(output, separators=(",", ":")))
    print(f"Wrote data.json ({len(rows)} deals, {len(arbs)} arbs)")


if __name__ == "__main__":
    main()
