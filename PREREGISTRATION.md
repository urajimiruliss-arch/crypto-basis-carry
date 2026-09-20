# Pre-registration: how much does the crypto basis trade actually pay in the EEA?

Written 2026-09-20, after downloading the data and inspecting its structure and date ranges, before computing any
return. Nothing below changes after the first run of `analysis.py`; later changes go into a dated addendum.

## Question

A delta-neutral basis trade (long spot, short perpetual) earns funding. Net of trading costs, capital tied up in
margin and Lithuanian tax, does it beat the benchmarks we already measured — a 1.5% deposit, and buy & hold of the
equity market (8% a year after tax, with drawdowns above 50%)?

## Data

| Series | Source (public endpoint, no account) | Coverage |
|---|---|---|
| Perp funding, BTCUSDT / ETHUSDT, every 8 h | Binance Futures `/fapi/v1/fundingRate` | 2019-09-10 – 2026-09-20 |
| Mark price, 8 h candles | Binance Futures `/fapi/v1/klines` | same |
| Perp funding, PF_XBTUSD / PF_ETHUSD, hourly | Kraken Futures `/derivatives/api/v4/historicalfundingrates` | 2025-09-17 – 2026-09-20 |
| Perp funding, BTC/ETH-USDT-SWAP | OKX `/api/v5/public/funding-rate-history` | last ~95 days only (API limit) |

Binance is the long history and is used for the test; it is *not* a venue an EEA retail client can use. Kraken is the
venue that matters in practice (MiFID entity, EEA retail) and is used as the venue check on the last year. OKX is a
spot check only.

## Cost model (fixed here, not tuned later)

- **Perp fees:** 0.05% taker per side → 0.10% per round trip of notional.
- **Spot fees:** 0.20% per side → 0.40% per round trip.
- **Spread and slippage:** 0.05% per round trip, both legs together.
- **Round trip total: 0.55% of notional.** Reported for one entry per year and, separately, for monthly re-entry.
- **Capital:** no leverage on the spot leg; the short perp is margined at 20% of notional, so 1.20 € of capital per
  1 € of notional. Yields are reported per euro of capital deployed.
- **Tax:** 15% on the positive net result (Lithuanian rate; the user checks the exact treatment with VMI).
- **Funding is credited to the short position:** positive funding = income, negative funding = cost.

## Samples

- **Exploration:** 2019-09-10 – 2024-12-31.
- **Holdout:** 2025-01-01 – 2026-09-20, opened once. `analysis.py holdout --one-look` writes a lock file and refuses
  to run again. The Kraken year is reported with the holdout.

## Metrics (per asset, per calendar year and overall)

1. Gross carry, annualised, from realised funding.
2. Net carry per euro of capital after fees, spread, margin drag and tax.
3. Share of funding periods that are negative; longest run of negative periods.
4. Worst 30-day window of cumulative funding.
5. Maximum drawdown of the cumulative net carry curve.
6. **Collateral buffer:** the largest adverse price move over 1, 3 and 7 days. If spot and perp sit at different
   venues, the short leg must survive this without the spot leg as collateral.

## Hypotheses (tested on the holdout)

- **H1:** net carry per euro of capital, after costs and tax, exceeds 1.5% a year (the deposit).
- **H2:** net carry exceeds 4% a year — roughly a euro money-market fund plus a risk premium worth the venue risk.

**Test:** monthly net carry values, circular block bootstrap with 3-month blocks, 10,000 resamples, seed 20260920,
one-sided p < 0.01. Exploration numbers are reported but claim nothing.

## What would change my mind

- H1 failing on the holdout closes the idea: a deposit pays the same with no venue, liquidation or tax complexity.
- H1 passing but H2 failing means the trade is a curiosity, not a product.
- Both passing justifies a small live pilot with a written risk limit, not a full allocation.
