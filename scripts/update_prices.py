#!/usr/bin/env python3
"""Fetch daily closes for SPY and the 11 SPDR sector ETFs and embed them in index.html.

Primary source: api.nasdaq.com. Falls back to Yahoo Finance's chart API if Nasdaq
refuses the request (it sometimes blocks cloud IPs). Exits non-zero if neither works,
so the scheduled workflow fails visibly instead of publishing stale data silently.
"""
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

TICKERS = "SPY XLK XLF XLI XLE XLV XLY XLP XLC XLB XLU XLRE".split()
HISTORY_DAYS = 400
ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def get_json(url):
    # curl, not urllib: Nasdaq's Akamai front end rejects Python's HTTP client.
    out = subprocess.run(
        ["curl", "-sSf", "--compressed", "-m", "60", "-A", UA, "-H", "Accept: application/json", url],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)


def from_nasdaq(tk, start, end):
    url = (f"https://api.nasdaq.com/api/quote/{tk}/historical?assetclass=etf"
           f"&fromdate={start}&todate={end}&limit=9999")
    rows = get_json(url)["data"]["tradesTable"]["rows"]
    out = {}
    for r in rows:
        m, d, y = r["date"].split("/")
        out[f"{y}-{m}-{d}"] = float(r["close"].replace(",", "").replace("$", ""))
    return out


def from_yahoo(tk, start, end):
    p1 = int(dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc).timestamp())
    p2 = int(dt.datetime.fromisoformat(end).replace(tzinfo=dt.timezone.utc).timestamp()) + 86400
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}"
           f"?period1={p1}&period2={p2}&interval=1d")
    res = get_json(url)["chart"]["result"][0]
    out = {}
    for ts, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        if c is not None:
            out[dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d")] = float(c)
    return out


def fetch_all(fetch, start, end):
    data = {}
    for tk in TICKERS:
        data[tk] = fetch(tk, start, end)
        if not data[tk]:
            raise RuntimeError(f"no rows for {tk}")
    return data


def main():
    end = dt.date.today().isoformat()
    start = (dt.date.today() - dt.timedelta(days=HISTORY_DAYS)).isoformat()
    source, data = None, None
    for name, fn in (("Nasdaq", from_nasdaq), ("Yahoo Finance", from_yahoo)):
        try:
            data, source = fetch_all(fn, start, end), name
            break
        except Exception as e:  # noqa: BLE001 - try the next source
            print(f"{name} failed: {e}", file=sys.stderr)
    if data is None:
        sys.exit("All price sources failed")

    dates = sorted(set.intersection(*(set(v) for v in data.values())))
    lines = ["Date," + ",".join(TICKERS)]
    lines += [d + "," + ",".join(f"{data[t][d]:.2f}" for t in TICKERS) for d in dates]
    csv = "\n".join(lines)

    html = PAGE.read_text()
    block = f'const SNAPSHOT={{asof:"{dates[-1]}",fetched:"{end}",csv:`{csv}`}};'
    html, n = re.subn(r"const SNAPSHOT=\{.*?`\};", lambda _: block, html, count=1, flags=re.S)
    if n != 1:
        sys.exit("SNAPSHOT block not found in index.html")
    # Keep the on-page source labels in sync with where the data came from.
    html = re.sub(r"`(Nasdaq|Yahoo Finance) · close \$\{last\}`", f"`{source} · close ${{last}}`", html)
    html = re.sub(r"liveMsg\(`(Nasdaq|Yahoo Finance) daily closes", f"liveMsg(`{source} daily closes", html)
    PAGE.write_text(html)
    print(f"{source}: {len(dates)} rows, {dates[0]} to {dates[-1]}")


if __name__ == "__main__":
    main()
