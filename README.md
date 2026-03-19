# nansen-divergence

Multi-chain smart money divergence scanner with Wyckoff phase classification. Built on top of the [Nansen CLI](https://docs.nansen.ai/nansen-cli/overview).

## What It Does

Scans 5 blockchains simultaneously and classifies every token into a **Wyckoff market phase** based on the divergence between capital flows and price movement:

| Phase | Flow | Price | Signal |
|-------|------|-------|--------|
| **ACCUMULATION** | Buying (+inflow) | Falling | Bullish divergence — capital loading while price drops |
| **DISTRIBUTION** | Selling (-outflow) | Rising | Bearish divergence — capital exiting into price strength |
| **MARKUP** | Buying | Rising | Trend confirmation |
| **MARKDOWN** | Selling | Falling | Capitulation |

Divergence signals (accumulation & distribution) are the alpha — they reveal what the market knows before price catches up.

## Features

- **Multi-chain scanning** — Ethereum, BNB, Solana, Base, Arbitrum in one command
- **Wyckoff phase classification** — Every token gets classified based on flow vs price divergence
- **Smart Money Radar** — Surfaces tokens where Nansen-labeled smart money wallets are active
- **Deep dive mode** — Flow intelligence breakdown by label (whales, smart traders, exchanges, fresh wallets) + wallet profiling
- **20+ API calls per scan** — Screener + smart money netflow across 5 chains, flow intelligence, who-bought-sold, profiler

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

### Scan Mode — Multi-chain divergence detection

```bash
# Full 5-chain scan (default)
nansen-divergence scan

# Specific chains
nansen-divergence scan --chains ethereum,bnb,solana

# Only show divergence signals (accumulation + distribution)
nansen-divergence scan --divergence-only

# More tokens per chain
nansen-divergence scan --limit 30
```

### Deep Dive Mode — Single token analysis

```bash
# Deep dive into a token (flow intelligence + who bought/sold + wallet profiles)
nansen-divergence deep --chain ethereum --token 0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9

# Customize lookback and wallet count
nansen-divergence deep --chain bnb --token 0x... --days 7 --wallets 5
```

## How It Works

1. **Token Screener** (`nansen research token screener`) — Fetches top tokens with price change, market cap, and market netflow per chain
2. **Smart Money Netflow** (`nansen research smart-money netflow`) — Fetches net capital flows from Nansen-labeled smart money wallets
3. **Merge & Score** — Matches tokens across both datasets. Computes divergence strength: how strongly flow direction and price direction disagree
4. **Classify** — Assigns each token a Wyckoff phase based on the divergence pattern
5. **Smart Money Radar** — Tokens with SM activity that aren't in the top screener get surfaced separately

### Deep Dive (per token)
6. **Flow Intelligence** (`nansen research token flow-intelligence`) — Breakdown by wallet label: whales, smart traders, exchanges, fresh wallets
7. **Who Bought/Sold** (`nansen research token who-bought-sold`) — Named entities with trade amounts
8. **Profiler** (`nansen research profiler labels` + `pnl-summary`) — Wallet labels and PnL track record for top movers

### Nansen CLI Commands Used

| Command | Purpose |
|---------|---------|
| `research token screener` | Token list + price change + netflow |
| `research smart-money netflow` | Smart money net USD flow per token |
| `research token flow-intelligence` | Flow breakdown by label (deep dive) |
| `research token who-bought-sold` | Named buyers/sellers (deep dive) |
| `research profiler labels` | Wallet labels (deep dive) |
| `research profiler pnl-summary` | Wallet PnL history (deep dive) |

**Total per full scan:** 5 chains x ~3 calls + deep dive calls = 15+ API calls minimum, 20+ with pagination.

## Divergence Scoring

```python
def score_divergence(netflow, price_change, market_cap):
    flow_signal = netflow / market_cap     # normalized by market cap
    price_signal = price_change            # fractional (-0.04 = -4%)

    if flow_signal > 0 and price_signal < 0:   phase = "ACCUMULATION"
    elif flow_signal < 0 and price_signal > 0:  phase = "DISTRIBUTION"
    elif flow_signal > 0:                       phase = "MARKUP"
    else:                                       phase = "MARKDOWN"

    strength = min(abs(flow_signal) * abs(price_signal) * 10000, 1.0)
    return strength, phase
```

## License

MIT
