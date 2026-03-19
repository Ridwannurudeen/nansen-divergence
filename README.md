# nansen-divergence v3.0

Multi-chain smart money divergence scanner with Wyckoff phase classification, HTML dashboards, Streamlit web UI, signal validation, Telegram alerts, and watch mode. Built on the [Nansen CLI](https://docs.nansen.ai/nansen-cli/overview) + optional REST API.

## What It Does

Scans **9 blockchains** and classifies every token into a **Wyckoff market phase** based on the divergence between **real smart money activity** and price movement:

| Phase | SM Flow | Price | Signal |
|-------|---------|-------|--------|
| **ACCUMULATION** | Buying | Falling | Bullish divergence — SM loading while price drops |
| **DISTRIBUTION** | Selling | Rising | Bearish divergence — SM exiting into strength |
| **MARKUP** | Buying | Rising | Trend confirmed |
| **MARKDOWN** | Selling | Falling | Capitulation |

## What's New in v3.0

- **9 Chains** — Ethereum, BNB, Solana, Base, Arbitrum, Polygon, Optimism, Avalanche, Linea
- **DexScreener Links** — Every token card includes a clickable DexScreener link for instant chart access
- **New Token Detection** — Tokens never seen before are flagged with a `[NEW]` badge in CLI and HTML reports
- **REST API Mode** — Set `NANSEN_API_KEY` env var to use the Nansen REST API instead of the CLI binary. Zero code changes needed — same functions, automatic dispatch.
- **Streamlit Web Dashboard** — Full web UI with dark theme, chain selector, token tables, DexScreener links, SM radar, signal validation, and scan history. Deploy to Streamlit Cloud or run locally.

## Features

- **4-source data pipeline** — Token screener + SM dex-trades + SM holdings + SM netflow (radar)
- **Multi-factor scoring** — Log-scaled flow, price magnitude, wallet diversity, holdings conviction
- **Confidence tiers** — HIGH / MEDIUM / LOW based on signal count and strength
- **Narrative generation** — One-line explanations: "5 SM wallets bought $500K of AAVE while price dropped 8.0% -- stealth loading"
- **Stablecoin filter** — 25+ stablecoins filtered by default (override with `--include-stables`)
- **Auto-dive** — Automatically deep-dive top N divergence signals inline
- **JSON output** — `--json` for structured output
- **HTML reports** — Dark crypto theme with DexScreener links, NEW badges, screenshot-ready
- **Signal validation** — Historical signal tracking with price delta proof
- **Telegram alerts** — Real-time notifications for divergence signals
- **Watch mode** — Continuous monitoring with diff detection
- **Nansen Score** — Token risk/reward indicators in deep dive
- **Smart Money Radar** — Surfaces SM-active tokens outside the screener
- **DexScreener integration** — Direct chart links for all 9 chains
- **New token detection** — First-seen tokens highlighted across CLI, HTML, and Streamlit

## Install

```bash
# Prerequisites
npm i -g @anthropic-ai/nansen   # Nansen CLI
nansen login                     # Authenticate

# Install
git clone https://github.com/Ridwannurudeen/nansen-divergence.git
cd nansen-divergence
pip install -e .

# For Streamlit dashboard
pip install -e ".[web]"
```

## Usage

### Scan Mode

```bash
# Full 9-chain scan (default)
nansen-divergence scan

# Specific chains
nansen-divergence scan --chains ethereum,bnb,solana

# Only divergence signals
nansen-divergence scan --divergence-only

# Auto deep-dive top 3 signals
nansen-divergence scan --chains bnb --limit 10 --auto-dive 3

# JSON output
nansen-divergence scan --json --chains bnb --limit 5

# HTML report with DexScreener links + NEW badges
nansen-divergence scan --chains bnb --limit 10 --html report.html

# Telegram alerts
nansen-divergence scan --chains bnb --limit 10 --telegram

# Watch mode (re-scan every 5 min)
nansen-divergence scan --chains bnb --limit 5 --watch 5

# Combo: watch + telegram + HTML
nansen-divergence scan --chains bnb --limit 5 --watch 10 --telegram
```

### Deep Dive Mode

```bash
# Full deep dive (flow intelligence + who bought/sold + Nansen Score + wallet profiles)
nansen-divergence deep --chain ethereum --token 0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9

# Customize
nansen-divergence deep --chain bnb --token 0x... --days 7 --wallets 5
```

### History

```bash
# View recent signals and scans (last 7 days)
nansen-divergence history

# Custom lookback
nansen-divergence history --days 30

# Clear all history
nansen-divergence history --clear
```

### REST API Mode

Set your Nansen API key to bypass the CLI binary entirely:

```bash
export NANSEN_API_KEY="your-api-key"
nansen-divergence scan --chains bnb --limit 5
```

All 9 functions automatically use the REST API when the key is set. No other changes needed.

### Streamlit Dashboard

```bash
# Local
streamlit run streamlit_app.py

# Or deploy to Streamlit Cloud — just push to GitHub and connect
```

The dashboard provides:
- Chain multiselect (9 chains)
- Timeframe and token limit controls
- Metric cards (tokens, signals, coverage, confidence)
- Phase-grouped token tables with DexScreener links
- SM Radar and Signal Validation sections
- Scan history

### Telegram Setup

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
nansen-divergence scan --chains bnb --limit 5 --telegram
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
9. **History** — Auto-save to SQLite + validate past signals + detect new tokens

### Deep Dive (per token)

10. **Flow Intelligence** — Flow breakdown by wallet label (whales, smart traders, exchanges)
11. **Who Bought/Sold** — Named entities with trade amounts
12. **Token Indicators** — Nansen Score (risk/reward)
13. **Profiler** — Wallet labels + PnL history for top movers

### Nansen CLI Commands / API Endpoints (9 total)

| Command / Endpoint | Purpose |
|---------|---------|
| `research token screener` / `POST /token-screener` | Token list + price + netflow |
| `research smart-money dex-trades` / `POST /smart-money/dex-trades` | Individual SM wallet trades |
| `research smart-money holdings` / `POST /smart-money/holdings` | SM positions + 24h change |
| `research smart-money netflow` / `POST /smart-money/netflow` | SM net flow (radar) |
| `research token flow-intelligence` / `POST /tgm/flow-intelligence` | Flow by label (deep dive) |
| `research token who-bought-sold` / `POST /tgm/who-bought-sold` | Named buyers/sellers (deep dive) |
| `research token indicators` / `POST /tgm/indicators` | Nansen Score (deep dive) |
| `research profiler labels` / `POST /profiler/address/labels` | Wallet labels (deep dive) |
| `research profiler pnl-summary` / `POST /profiler/address/pnl-summary` | Wallet PnL (deep dive) |

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
| 9 chain scan (no dive) | ~65 |
| 5 chain + auto-dive 3 | ~56 |
| Deep dive (3 wallets) | ~9 |
| Watch mode (per scan) | same as scan |

## Testing

```bash
pip install -e ".[test]"
pytest tests/ -v
```

## License

MIT
