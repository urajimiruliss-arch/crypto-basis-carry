# -*- coding: utf-8 -*-
"""Downloads public funding-rate and price history for the basis study. Standard library only, no account needed.

Sources (public endpoints, no authentication):
  Kraken Futures  /derivatives/api/v4/historicalfundingrates  - the venue an EEA retail client can actually use
  OKX             /api/v5/public/funding-rate-history          - second EEA-authorised venue (X-Perps)
  Binance Futures /fapi/v1/fundingRate and /fapi/v1/klines     - longest history, reference only

Usage:
    python download.py            # incremental: keeps what is already saved
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "data", "raw")
UA = {"User-Agent": "crypto-basis-research/1.0"}
PAUSE = 0.35


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    return None


def save(name, obj):
    path = os.path.join(RAW, name)
    blob = json.dumps(obj, ensure_ascii=False).encode()
    with open(path, "wb") as f:
        f.write(blob)
    return {"file": name, "rows": len(obj), "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(),
            "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def kraken_funding(symbol):
    """Kraken Futures publishes the full history of its perpetual funding rates in one call."""
    d = get(f"https://futures.kraken.com/derivatives/api/v4/historicalfundingrates?symbol={symbol}")
    return d.get("rates", [])


def okx_funding(inst):
    """OKX returns 100 rows per call, paging backwards with `after` = oldest fundingTime seen."""
    rows, after = [], None
    while True:
        url = f"https://www.okx.com/api/v5/public/funding-rate-history?instId={inst}&limit=100"
        if after:
            url += f"&after={after}"
        d = get(url)
        batch = d.get("data") or []
        if not batch:
            break
        rows.extend(batch)
        after = batch[-1]["fundingTime"]
        time.sleep(PAUSE)
        if len(rows) > 20000:
            break
    return rows


def binance_funding(symbol):
    rows, start = [], 1567296000000          # 2019-09-01, before the first BTCUSDT perp funding
    while True:
        d = get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&startTime={start}&limit=1000")
        if not d:
            break
        rows.extend(d)
        if len(d) < 1000:
            break
        start = d[-1]["fundingTime"] + 1
        time.sleep(PAUSE)
    return rows


def binance_klines(symbol, interval="8h"):
    rows, start = [], 1567296000000
    while True:
        d = get(f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}"
                f"&startTime={start}&limit=1500")
        if not d:
            break
        rows.extend(d)
        if len(d) < 1500:
            break
        start = d[-1][0] + 1
        time.sleep(PAUSE)
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(RAW, exist_ok=True)
    manifest = {}
    jobs = [
        ("kraken_funding_PF_XBTUSD.json", lambda: kraken_funding("PF_XBTUSD")),
        ("kraken_funding_PF_ETHUSD.json", lambda: kraken_funding("PF_ETHUSD")),
        ("okx_funding_BTC-USDT-SWAP.json", lambda: okx_funding("BTC-USDT-SWAP")),
        ("okx_funding_ETH-USDT-SWAP.json", lambda: okx_funding("ETH-USDT-SWAP")),
        ("binance_funding_BTCUSDT.json", lambda: binance_funding("BTCUSDT")),
        ("binance_funding_ETHUSDT.json", lambda: binance_funding("ETHUSDT")),
        ("binance_klines_8h_BTCUSDT.json", lambda: binance_klines("BTCUSDT")),
        ("binance_klines_8h_ETHUSDT.json", lambda: binance_klines("ETHUSDT")),
    ]
    for name, fn in jobs:
        try:
            data = fn()
            info = save(name, data)
            manifest[name] = info
            print(f"{name}: {info['rows']:,} rows, {info['bytes'] / 1024:,.0f} KB", flush=True)
        except Exception as e:
            print(f"{name}: FAILED ({type(e).__name__}: {e})", flush=True)
    with open(os.path.join(BASE, "data", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
