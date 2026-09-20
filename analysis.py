# -*- coding: utf-8 -*-
"""Basis-trade study strictly per PREREGISTRATION.md.

Usage:
    python analysis.py exploration          # 2019-09-10 .. 2024-12-31
    python analysis.py holdout --one-look   # 2025-01-01 .. 2026-09-20, ONCE (writes outputs/holdout/LOCK)
"""
import collections
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "outputs")

EXPLORATION = ("2019-09-10", "2024-12-31")
HOLDOUT = ("2025-01-01", "2026-09-20")
ROUND_TRIP = 0.0055          # 0.55% of notional per entry+exit
MARGIN = 0.20                # capital = 1.20 per 1 notional
CAPITAL = 1.0 + MARGIN
TAX = 0.15
PERIODS_PER_YEAR = 3 * 365   # 8-hour funding
BLOCK = 3
N_BOOT = 10_000
SEED = 20260920
ALPHA = 0.01
H1, H2 = 0.015, 0.04


def load(name):
    with open(os.path.join(RAW, name), encoding="utf-8") as f:
        return json.load(f)


def ts(ms):
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc)


def binance_series(asset):
    fund = [(ts(r["fundingTime"]), float(r["fundingRate"])) for r in load(f"binance_funding_{asset}USDT.json")]
    px = [(ts(k[0]), float(k[4])) for k in load(f"binance_klines_8h_{asset}USDT.json")]
    return sorted(fund), sorted(px)


def in_range(t, lo, hi):
    return lo <= t.strftime("%Y-%m-%d") <= hi


def drawdown(curve):
    peak, worst = curve[0], 0.0
    for x in curve:
        peak = max(peak, x)
        worst = min(worst, x - peak)
    return worst


def buffer_moves(px, lo, hi, days):
    """Largest adverse (upward) move of the price over `days`, as a share — the short leg's stress."""
    steps = days * 3
    vals = [(t, p) for t, p in px if in_range(t, lo, hi)]
    worst = 0.0
    for i in range(len(vals) - steps):
        worst = max(worst, vals[i + steps][1] / vals[i][1] - 1.0)
    return worst


def block_bootstrap_p(monthly, threshold, rng_seed=SEED):
    """One-sided p that the mean monthly net carry is above `threshold`/12, circular block bootstrap."""
    import random
    xs = [m - threshold / 12 for m in monthly]
    n = len(xs)
    if n < BLOCK * 2:
        return float("nan")
    rnd = random.Random(rng_seed)
    n_blocks = math.ceil(n / BLOCK)
    below = 0
    for _ in range(N_BOOT):
        s, cnt = 0.0, 0
        for _ in range(n_blocks):
            st = rnd.randrange(n)
            for k in range(BLOCK):
                s += xs[(st + k) % n]
                cnt += 1
        if s / cnt <= 0:
            below += 1
    return below / N_BOOT


def analyse(asset, lo, hi):
    fund, px = binance_series(asset)
    rows = [(t, r) for t, r in fund if in_range(t, lo, hi)]
    if len(rows) < 100:
        return None
    years = len(rows) / PERIODS_PER_YEAR
    gross = sum(r for _, r in rows)
    by_month = collections.defaultdict(float)
    for t, r in rows:
        by_month[t.strftime("%Y-%m")] += r
    months = sorted(by_month)
    # net per euro of capital: funding on 1 notional, minus one round trip a year, minus tax, divided by 1.20
    def net_annual(gross_sum, n_years, entries_per_year):
        gross_a = gross_sum / n_years
        cost_a = ROUND_TRIP * entries_per_year
        pre_tax = (gross_a - cost_a) / CAPITAL
        return pre_tax * (1 - TAX) if pre_tax > 0 else pre_tax
    monthly_net = [(by_month[m] - ROUND_TRIP / 12) / CAPITAL * (1 - TAX) for m in months]
    curve, s = [], 0.0
    for _, r in rows:
        s += r
        curve.append(s)
    neg = [1 if r < 0 else 0 for _, r in rows]
    longest, cur = 0, 0
    for x in neg:
        cur = cur + 1 if x else 0
        longest = max(longest, cur)
    worst30 = min(sum(r for _, r in rows[i:i + 90]) for i in range(max(len(rows) - 90, 1)))
    by_year = {}
    for y in sorted({t.year for t, _ in rows}):
        yr = [r for t, r in rows if t.year == y]
        by_year[y] = {"periods": len(yr), "gross_annualised": sum(yr) / (len(yr) / PERIODS_PER_YEAR),
                      "share_negative": sum(1 for r in yr if r < 0) / len(yr)}
    return {
        "asset": asset, "from": rows[0][0].strftime("%Y-%m-%d"), "to": rows[-1][0].strftime("%Y-%m-%d"),
        "years": round(years, 2), "periods": len(rows),
        "gross_annualised": gross / years,
        "net_annualised_yearly_entry": net_annual(gross, years, 1),
        "net_annualised_monthly_entry": net_annual(gross, years, 12),
        "share_negative": sum(neg) / len(neg), "longest_negative_run_periods": longest,
        "worst_30d_funding": worst30,
        "max_drawdown_gross": drawdown(curve),
        "buffer_1d": buffer_moves(px, lo, hi, 1), "buffer_3d": buffer_moves(px, lo, hi, 3),
        "buffer_7d": buffer_moves(px, lo, hi, 7),
        "by_year": by_year, "monthly_net": monthly_net, "months": months,
    }


def kraken_year():
    out = {}
    for sym, asset in (("PF_XBTUSD", "BTC"), ("PF_ETHUSD", "ETH")):
        rows = load(f"kraken_funding_{sym}.json")
        rel = [float(r["relativeFundingRate"]) for r in rows]          # per hour, relative to index
        years = len(rel) / (24 * 365)
        gross_a = sum(rel) / years
        net_a = (gross_a - ROUND_TRIP) / CAPITAL
        out[asset] = {"hours": len(rel), "from": rows[0]["timestamp"], "to": rows[-1]["timestamp"],
                      "gross_annualised": gross_a,
                      "net_annualised_yearly_entry": net_a * (1 - TAX) if net_a > 0 else net_a,
                      "share_negative": sum(1 for x in rel if x < 0) / len(rel)}
    return out


def pct(x):
    return f"{x * 100:+.2f}%"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    split = sys.argv[1] if len(sys.argv) > 1 else ""
    if split not in ("exploration", "holdout"):
        sys.exit("usage: python analysis.py exploration | holdout --one-look")
    outdir = os.path.join(OUT, split)
    os.makedirs(outdir, exist_ok=True)
    if split == "holdout":
        lock = os.path.join(outdir, "LOCK")
        if "--one-look" not in sys.argv:
            sys.exit("The holdout is looked at once. Run with --one-look when the exploration write-up is complete.")
        if os.path.exists(lock):
            sys.exit(f"The holdout has already been opened ({open(lock, encoding='utf-8').read().strip()}). Re-running is not allowed.")
        with open(lock, "w", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat(timespec="seconds"))
    lo, hi = EXPLORATION if split == "exploration" else HOLDOUT

    results = {}
    for asset in ("BTC", "ETH"):
        r = analyse(asset, lo, hi)
        results[asset] = r
        print(f"\n== {asset} (Binance perp funding), {r['from']} – {r['to']}, {r['years']} years")
        print(f"  gross carry annualised           {pct(r['gross_annualised'])}")
        print(f"  net per € capital, 1 entry/year  {pct(r['net_annualised_yearly_entry'])}")
        print(f"  net per € capital, monthly entry {pct(r['net_annualised_monthly_entry'])}")
        print(f"  negative funding periods         {r['share_negative'] * 100:.1f}%  (longest run {r['longest_negative_run_periods']} periods)")
        print(f"  worst 30-day funding             {pct(r['worst_30d_funding'])}")
        print(f"  max drawdown of carry curve      {pct(r['max_drawdown_gross'])}")
        print(f"  collateral stress 1d/3d/7d       {pct(r['buffer_1d'])} / {pct(r['buffer_3d'])} / {pct(r['buffer_7d'])}")
        print("  by year: " + ", ".join(f"{y}: {pct(v['gross_annualised'])} ({v['share_negative'] * 100:.0f}% neg)"
                                        for y, v in r["by_year"].items()))
        if split == "holdout":
            p1 = block_bootstrap_p(r["monthly_net"], H1)
            p2 = block_bootstrap_p(r["monthly_net"], H2)
            mean_net = statistics.fmean(r["monthly_net"]) * 12
            print(f"  H1 net > 1.5%/yr: mean {pct(mean_net)}, p = {p1:.4f} -> {'confirmed' if p1 < ALPHA else 'not confirmed'}")
            print(f"  H2 net > 4.0%/yr: p = {p2:.4f} -> {'confirmed' if p2 < ALPHA else 'not confirmed'}")
            results[asset]["tests"] = {"mean_net_annual": mean_net, "p_h1": p1, "p_h2": p2}

    if split == "holdout":
        kr = kraken_year()
        print("\n== Kraken Futures (the EEA venue), last year")
        for asset, v in kr.items():
            print(f"  {asset}: {v['from'][:10]} – {v['to'][:10]}  gross {pct(v['gross_annualised'])}  "
                  f"net per € capital {pct(v['net_annualised_yearly_entry'])}  negative hours {v['share_negative'] * 100:.1f}%")
        results["kraken"] = kr

    for a in ("BTC", "ETH"):
        results[a].pop("monthly_net", None)
        results[a].pop("months", None)
    with open(os.path.join(outdir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nresults: {os.path.join(outdir, 'results.json')}")


if __name__ == "__main__":
    main()
