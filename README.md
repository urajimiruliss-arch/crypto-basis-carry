# What does the crypto basis trade actually pay a European retail investor?

A pre-registered measurement of the delta-neutral basis trade — long spot, short perpetual future — using public
funding-rate history, with realistic costs, margin, Lithuanian tax and a holdout opened exactly once.

**Headline:** the trade paid ~14% a year gross in 2019–2024 and **4.2% in 2025–2026**. After fees, the capital tied up
as margin and 15% tax, that is **+2.6% a year** — and **+1.9% on Kraken**, the venue an EEA retail client can actually
use, where funding is negative 30% of the time. A euro deposit pays about 1.5% with none of the venue, liquidation or
tax complexity. Pre-registered hypothesis H1 (net > 1.5%) was **not confirmed** (p = 0.053); H2 (net > 4%) was rejected.

No investment advice follows from this work.

---

## Why this question

A perpetual future has no expiry, so an 8-hourly funding payment keeps its price near spot. When traders want leveraged
long exposure, longs pay shorts. Holding spot and shorting the perp is therefore a way to harvest that payment without
taking price risk — in principle. The question is what survives costs.

**Who pays:** leveraged longs. That is a real mechanism, not a chart pattern, which is why the idea deserved a measurement
rather than an opinion.

## Regulatory starting point (EEA, 2026)

- MiCA covers spot and custody, **not** derivatives; perpetuals fall under MiFID II.
- MiCA-only venues (e.g. Bybit EU) therefore offer spot and margin but no perps.
- Retail perps in the EEA are available on venues holding both licences — Kraken (MiFID entity), OKX X-Perps, Robinhood
  Europe — with leverage capped around 3–10x.

This is why the study treats **Kraken as the venue that matters** and Binance only as the long history.

## Data

| Series | Source (public endpoint, no account) | Coverage |
|---|---|---|
| Perp funding BTC/ETH, 8-hourly | Binance Futures `fundingRate` | 2019-09-10 – 2026-09-20 |
| Mark price, 8 h candles | Binance Futures `klines` | same |
| Perp funding BTC/ETH, hourly | Kraken Futures `historicalfundingrates` | 2025-09-17 – 2026-09-20 |
| Perp funding BTC/ETH | OKX `funding-rate-history` | last ~95 days (API limit) |

`download.py` fetches them and records a SHA-256 manifest. Raw files are not republished.

## Method

1. **Pre-registration before any return was computed:** [`PREREGISTRATION.md`](PREREGISTRATION.md) — costs, margin, tax,
   samples, hypotheses and the test.
2. **Cost model:** 0.55% of notional per entry+exit (perp 0.10%, spot 0.40%, spread 0.05%); short perp margined at 20%,
   so €1.20 of capital per €1 of notional; 15% Lithuanian tax on the positive result.
3. **Split:** exploration 2019-09 – 2024-12, holdout 2025-01 – 2026-09 opened once (lock file).
4. **Inference:** monthly net carry, circular block bootstrap (3-month blocks, 10,000 resamples), one-sided p < 0.01.

## Results

### Gross carry, annualised

| Period | BTC | ETH |
|---|---|---|
| Exploration 2019–2024 | +13.95% | +17.24% |
| 2021 (peak leverage demand) | +30.61% | +37.54% |
| 2022 (after the crash) | +4.16% | +0.79% |
| **Holdout 2025–2026** | **+4.20%** | **+3.60%** |

### Net per euro of capital, after costs, margin and tax

| | BTC | ETH |
|---|---|---|
| Exploration, one entry a year | +9.49% | +11.82% |
| Holdout, one entry a year | **+2.59%** | **+2.16%** |
| Holdout, re-entering monthly | −2.00% | −2.50% |
| **Kraken (EEA venue), last year** | **+1.93%** | **+1.77%** |

| Hypothesis (holdout) | Result |
|---|---|
| **H1** net > 1.5% a year | **not confirmed** — BTC +2.53%, p = 0.053; ETH +2.12%, p = 0.16 |
| **H2** net > 4% a year | **rejected** — p ≈ 1 |

### Risk the headline yield hides

| Stress | BTC | ETH |
|---|---|---|
| Largest 1-day move against the short leg | +27% (2019–24) / +12% (2025–26) | +31% / +23% |
| Largest 3-day move | +29% / +21% | +43% / +43% |
| Largest 7-day move | +40% / +24% | +70% / +47% |
| Share of funding periods negative (holdout) | 18.6% | 22.5% |
| Share of negative funding hours on Kraken | 30.2% | 31.9% |

If the spot and perp legs sit at different venues and cannot collateralise each other, the short leg must survive those
moves on its own margin — which roughly halves the return on capital actually committed.

## What this means

- **The carry is a payment for taking venue and liquidation risk, not an edge.** It scales with leverage demand: 30%+ in
  a hot market, ~2% in a quiet one.
- **At 1.9% on the venue you can actually use, a deposit is the better trade.** Same money, no counterparty, no margin
  calls at 3 a.m., no tax ambiguity.
- **Monthly re-entry destroys it.** The only viable form is enter once and sit — which maximises exposure to the venue.

## Limitations

- Funding is realised history; a live trade would face fills, latency and occasional funding-rate caps.
- The cost model is a fixed assumption, not the user's actual fee tier.
- Kraken's public history covers one year only; OKX publishes 95 days.
- Tax treatment is simplified to a flat 15% on the net result.

## Reproduce

```bash
python download.py
python analysis.py exploration
python analysis.py holdout --one-look
```

Python 3.14, standard library only (no third-party packages). The bootstrap is written directly in `analysis.py`.
