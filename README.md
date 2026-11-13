# Sector Rotation Map

An RRG-style relative rotation chart of the 11 SPDR sector ETFs against SPY: relative strength on the x-axis, its momentum on the y-axis.

The whole app is `index.html`. Prices are embedded in the page as a CSV snapshot.

## Automatic updates

`.github/workflows/update-prices.yml` runs every weekday at 22:30 UTC (after the US close). It runs `scripts/update_prices.py`, which:

1. fetches about 400 days of daily closes from `api.nasdaq.com` (falling back to Yahoo Finance if Nasdaq refuses),
2. rewrites the embedded snapshot in `index.html`,
3. commits the change if anything is new.

You can also run it by hand from the **Actions** tab (**Update prices → Run workflow**), or locally with `python scripts/update_prices.py`.

## Viewing it

Turn on GitHub Pages (**Settings → Pages → Deploy from a branch → `main` / root**). The site then serves the latest `index.html` and picks up each daily commit.
