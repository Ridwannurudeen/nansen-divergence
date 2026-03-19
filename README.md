# nansen-divergence v2.0

Multi-chain smart money divergence scanner with Wyckoff phase classification. Built on the [Nansen CLI](https://docs.nansen.ai/nansen-cli/overview).

## What It Does

Scans 5 blockchains and classifies every token into a **Wyckoff market phase** based on the divergence between **real smart money activity** and price movement:

| Phase | SM Flow | Price | Signal |
|-------|---------|-------|--------|
| **ACCUMULATION** | Buying | Falling | Bullish divergence — SM loading while price drops |
| **DISTRIBUTION** | Selling | Rising | Bearish divergence — SM exiting into strength |
| **MARKUP** | Buying | Rising | Trend confirmed |
| **MARKDOWN** | Selling | Falling | Capitulation |

### What Changed in v2.0

**v1.0 problem:** The `smart-money netflow` endpoint returns completely different tokens than the `token screener`, so ~95% of tokens showed `--` for SM data. The "smart money divergence" thesis was barely visible.

**v2.0 fix:** Replaced the broken merge with `smart-money dex-trades` aggregation. This endpoint returns individual SM wallet trades — by grouping them per token, we compute REAL SM flow for every screener token. Combined with `smart-money holdings` for conviction data, every row gets rich multi-signal intelligence.

## Features

- **4-source data pipeline** — Token screener + SM dex-trades + SM holdings + SM netflow (radar)
- **Multi-factor scoring** — Log-scaled flow, price magnitude, wallet diversity, holdings conviction
- **Confidence tiers** — HIGH / MEDIUM / LOW based on signal count and strength
- **Narrative generation** — One-line explanations: "5 SM wallets bought $500K of AAVE while price dropped 8.0% -- stealth loading"
- **Stablecoin filter** — USDT, USDC, DAI, etc. filtered by default (override with `--include-stables`)
- **Auto-dive** — Automatically deep-dive top N divergence signals inline
- **JSON output** — `--json` for structured output
- **Nansen Score** — Token risk/reward indicators in deep dive
- **Smart Money Radar** — Surfaces SM-active tokens outside the screener

## Install

```bash
# Prerequisites
npm i -g @anthropic-ai/nansen   # Nansen CLI
nansen login                     # Authenticate

# Install
git clone https://github.com/Ridwannurudeen/nansen-divergence.git
cd nansen-divergence
pip install -e .
```

## Usage

### Scan Mode

```bash
# Full 5-chain scan (default)
nansen-divergence scan

# Specific chains
nansen-divergence scan --chains ethereum,bnb,solana

# Only divergence signals
nansen-divergence scan --divergence-only

# Auto deep-dive top 3 signals
nansen-divergence scan --chains bnb --limit 10 --auto-dive 3

# JSON output
nansen-divergence scan --json --chains bnb --limit 5

# Include stablecoins (filtered by default)
nansen-divergence scan --include-stables
```

### Deep Dive Mode

```bash
# Full deep dive (flow intelligence + who bought/sold + Nansen Score + wallet profiles)
nansen-divergence deep --chain ethereum --token 0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9

# Customize
nansen-divergence deep --chain bnb --token 0x... --days 7 --wallets 5
```

## How It Works

### Scan Pipeline (per chain)

1. **Token Screener** — Top tokens with price, market cap, netflow
2. **SM Dex-Trades** — Individual SM wallet trades, aggregated per screener token (buy/sell/net/trader count)
3. **SM Holdings** — SM positions + 24h balance change per token
4. **SM Netflow** — Legacy flow data for SM Radar (tokens not in screener)
5. **Score** — Multi-factor divergence scoring with log-scaled flow normalization
6. **Classify** — Wyckoff phase assignment
7. **Narrate** — One-line signal explanation per token
8. **Confidence** — HIGH/MEDIUM/LOW based on signal convergence

### Deep Dive (per token)

9. **Flow Intelligence** — Flow breakdown by wallet label (whales, smart traders, exchanges)
10. **Who Bought/Sold** — Named entities with trade amounts
11. **Token Indicators** — Nansen Score (risk/reward)
12. **Profiler** — Wallet labels + PnL history for top movers

### Nansen CLI Commands Used (9 total)

| Command | Purpose |
|---------|---------|
| `research token screener` | Token list + price + netflow |
| `research smart-money dex-trades` | Individual SM wallet trades |
| `research smart-money holdings` | SM positions + 24h change |
| `research smart-money netflow` | SM net flow (radar) |
| `research token flow-intelligence` | Flow by label (deep dive) |
| `research token who-bought-sold` | Named buyers/sellers (deep dive) |
| `research token indicators` | Nansen Score (deep dive) |
| `research profiler labels` | Wallet labels (deep dive) |
| `research profiler pnl-summary` | Wallet PnL (deep dive) |

## Scoring Algorithm

```
flow_score     = log10(|flow| + 1) / log10(market_cap)     # 0-1, smooth
price_score    = min(|price_change| * 5, 1.0)               # 10% = 0.5
diversity_score = min(trader_count / 10, 1.0)               # more wallets = stronger
conviction_score = holdings change agreeing with flow        # 0-1

strength = 0.40 * flow + 0.25 * price + 0.20 * diversity + 0.15 * conviction

Confidence:
  HIGH   = 3+ signals active, strength >= 0.4
  MEDIUM = 2+ signals active, strength >= 0.2
  LOW    = everything else
```

## API Credit Budget

| Run | ~Credits |
|-----|----------|
| 1 chain scan (no dive) | ~8 |
| 5 chain scan (no dive) | ~35 |
| 5 chain + auto-dive 3 | ~56 |
| Deep dive (3 wallets) | ~9 |

## Testing

```bash
pip install -e ".[test]"
pytest tests/ -v
```

## License

MIT
