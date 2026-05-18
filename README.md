# Adopt Me Value Tracker

Personal tool that cross-references current starpets.gg listings with community trade values and surfaces the best deals.

Auto-updates daily via GitHub Actions, served free via GitHub Pages.

## How it works

```
┌─────────────────────────┐
│  Daily at 06:00 UTC     │
│  GitHub Actions runs:   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐    ┌──────────────────┐
│  scripts/scrape.py      │───▶│  raw_prices.json │
│  hits starpets API      │    └──────────────────┘
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐    ┌──────────────────┐
│  scripts/combine.py     │───▶│  data.json       │
│  joins prices+values    │    └──────────────────┘
│  computes ratios+arbs   │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│  git commit + push      │
│  GitHub Pages redeploys │
└─────────────────────────┘
```

The frontend is a single `index.html` that fetches `data.json` and renders highlights + filterable tables.

## Setup

### 1. Create a new GitHub repo

Make a new **public** repo (private also works but uses your free Actions minutes). Drop everything in this folder into it.

```
your-repo/
├── .github/workflows/update.yml
├── scripts/
│   ├── scrape.py
│   └── combine.py
├── index.html
├── values.txt        ← YOU NEED TO ADD THIS
└── README.md
```

### 2. Add your `values.txt`

Copy your existing tab-separated value list (the one with `Pet name <tab> no_pot <tab> FR <tab> NFR <tab> MFR`) into the repo root and name it `values.txt`.

### 3. Run it once manually

Go to **Actions** tab in your repo → **Update prices** workflow → **Run workflow** button. This populates the first `data.json` so the site has something to display. After this, it'll auto-run daily.

### 4. Enable GitHub Pages

In repo **Settings** → **Pages**:
- Source: **Deploy from a branch**
- Branch: **main**, folder: **/ (root)**

Your site will be at `https://<your-username>.github.io/<repo-name>/`. First deploy takes a couple minutes.

## Things that might go wrong

**Scraper returns nothing or 403/429.** starpets.gg might block GitHub's IP range or rate-limit. If this happens:
- Check the Actions log for the actual error
- Increase the `time.sleep(1)` in `scrape.py` to 2-3 seconds
- As a last resort, add a proxy to the `requests.get()` call

**The Actions workflow fails on commit.** Make sure under repo **Settings** → **Actions** → **General** → **Workflow permissions**, you have **Read and write permissions** enabled.

**Values file format breaks.** `combine.py` expects tab-separated `name<tab>no_pot<tab>FR<tab>NFR<tab>MFR`. Doubled names like "Cat Cat" are auto-fixed but other quirks aren't.

**A pet shows up in starpets but not in your tracker.** It's probably missing from `values.txt`. Add it.

## Tweaking

- **Schedule:** edit the `cron:` line in `update.yml`. `0 6 * * *` = 06:00 UTC daily. [Crontab guru](https://crontab.guru/) helps if you want a different schedule.
- **Highlights cards:** edit `renderHighlights()` in `index.html`. You can change the filters or add more cards.
- **Filters:** add new filter inputs in the filter-bar div and update the `renderDeals()` filter function.
- **Aesthetics:** the CSS variables at the top of `index.html` control all colors.

## Caveats

- starpets.gg listings change throughout the day; this snapshot is from whenever the last scrape ran (see the "last sync" timestamp on the site).
- Pet values are community estimates and can drift fast for trendy items.
- Lowest-price listings are sometimes a single seller asking for a wishful price — the `Listings` column shows market depth so you can judge.
- This isn't affiliated with Adopt Me, Roblox, or starpets.gg.
