# nansen-divergence v5.0

**[Live Dashboard](https://nansen.gudman.xyz)** | Multi-chain smart money divergence scanner with Wyckoff phase classification, Next.js trading terminal, signal backtesting, and Alpha Score ranking.

Built on the [Nansen CLI](https://docs.nansen.ai/nansen-cli/overview) + REST API. Submitted for the **Nansen CLI Hackathon**.

## What It Does

Scans **9 blockchains** every 30 minutes and classifies tokens into **Wyckoff market phases** based on the divergence between **real smart money activity** and price movement:

| Phase | SM Flow | Price | Signal |
|-------|---------|-------|--------|
| **ACCUMULATION** | Buying | Falling | Bullish divergence — SM loading while price drops |
| **DISTRIBUTION** | Selling | Rising | Bearish divergence — SM exiting into strength |
| **MARKUP** | Buying | Rising | Trend confirmed — momentum aligned |
| **MARKDOWN** | Selling | Falling | Capitulation |

## Architecture

```
                    Nansen CLI / REST API
                           |
              ┌────────────┼────────────┐
              v            v            v
         Token         SM Dex       SM Holdings
        Screener       Trades       + Netflow
              └────────────┼────────────┘
                           v
                  ┌─────────────────┐
                  │  Divergence     │
                  │  Engine         │
                  │  (Python)       │
                  │                 │
                  │  Score → Phase  │
                  │  → Confidence   │
                  │  → Narrative    │
                  └────────┬────────┘
                           │
              ┌────────────┼────────────┐
              v            v            v
           CLI          FastAPI       Next.js
          Output        (8010)        Dashboard
                           │          (3010)
                           └─────┬─────┘
                                 v
                          Docker Compose
                          + nginx reverse proxy
                                 │
                                 v
                        https://nansen.gudman.xyz
```

## Dashboard Pages

| Page | What It Shows |
|------|---------------|
| **Dashboard** | Heat map, signal feed, metric cards, full token table with Alpha Score bars |
| **Radar** | Pre-breakout tokens — SM-only activity not yet in mainstream screeners |
| **Performance** | Win/loss donut, signal timeline scatter, outcome tracking over 30 days |
| **Flows** | Chain momentum chart, per-chain breakdown cards, sector rotation table |
| **Token Deep Dive** | Per-token flow intelligence, top buyers/sellers, Nansen Score, wallet profiles |

## Features

**Data Pipeline (4 sources per chain)**
- Token screener (price, market cap, volume, netflow)
- SM dex-trades (individual wallet trades aggregated per token)
- SM holdings (positions + 24h balance changes)
- SM netflow (radar tokens outside the screener)

**Divergence Engine**
- Multi-factor Alpha Score (0-100): flow magnitude (40%), price movement (25%), wallet diversity (20%), holdings conviction (15%)
- Log-scaled normalization prevents large-cap dominance
- Confidence tiers: HIGH / MEDIUM / LOW
- Narrative generation: "5 SM wallets bought $500K of AAVE while price dropped 8.0% -- stealth loading"

**CLI**
- 9-chain scan with Wyckoff classification
- Deep dive per token (flow intelligence, buyers/sellers, wallet profiles)
- HTML reports, JSON output, Telegram alerts, watch mode
- Signal history with SQLite persistence and outcome validation

**Dashboard (Next.js)**
- Terminal-style dark UI (JetBrains Mono, orange accent)
- Recharts visualizations (treemap, bar charts, pie, scatter)
- Responsive mobile-first design with card layouts
- Accessible (ARIA labels, focus-visible, reduced-motion support)
- SWR auto-refresh every 60 seconds

## Quick Start

### CLI

```bash
# Prerequisites
npm i -g nansen-cli
nansen login

# Install
git clone https://github.com/Ridwannurudeen/nansen-divergence.git
cd nansen-divergence
pip install -e .

# Full 9-chain scan
nansen-divergence scan

# Specific chains + deep dive
nansen-divergence scan --chains ethereum,bnb,solana --auto-dive 3

# JSON output
nansen-divergence scan --json --chains bnb --limit 5

# HTML report
nansen-divergence scan --chains bnb --limit 10 --html report.html

# Watch mode + Telegram alerts
nansen-divergence scan --chains bnb --limit 5 --watch 10 --telegram
```

### Deep Dive

```bash
nansen-divergence deep --chain ethereum --token 0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9
```

### REST API Mode

```bash
export NANSEN_API_KEY="your-api-key"
nansen-divergence scan --chains bnb --limit 5
# All 9 Nansen functions auto-switch to REST API when key is set
```

### Self-Host (Docker)

```bash
cp .env.example .env
# Add NANSEN_MCP_KEY to .env

docker compose up -d
# API at :8010, Dashboard at :3010
# Add nginx reverse proxy for HTTPS
```

## Nansen CLI / API Usage (9 endpoints)

| Command | Purpose |
|---------|---------|
| `research token screener` | Token list + price + netflow |
| `research smart-money dex-trades` | Individual SM wallet trades |
| `research smart-money holdings` | SM positions + 24h change |
| `research smart-money netflow` | SM net flow (radar) |
| `research token flow-intelligence` | Flow by wallet label |
| `research token who-bought-sold` | Named buyers/sellers |
| `research token indicators` | Nansen Score |
| `research profiler labels` | Wallet labels |
| `research profiler pnl-summary` | Wallet PnL history |

## Scoring Algorithm

```
flow_score       = log10(|flow| + 1) / log10(market_cap)   # 0-1
price_score      = min(|price_change| * 5, 1.0)             # 10% = 0.5
diversity_score  = min(trader_count / 10, 1.0)               # more wallets = stronger
conviction_score = holdings change agreeing with flow         # 0-1

alpha_score = (0.40 * flow + 0.25 * price + 0.20 * diversity + 0.15 * conviction) * 100

Confidence:
  HIGH   = 3+ signals active, strength >= 0.4
  MEDIUM = 2+ signals active, strength >= 0.2
  LOW    = everything else
```

## Testing

```bash
pip install -e ".[test]"
pytest tests/ api/tests/ -v
# 165 tests across engine, API, scoring, alerts, history, and reports
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Engine | Python 3.12, Rich |
| API | FastAPI, Uvicorn |
| Dashboard | Next.js 16, React, Tailwind CSS v4, Recharts, SWR |
| Data | Nansen CLI + REST API, SQLite (history) |
| Deploy | Docker Compose, nginx, Let's Encrypt |
| CI | GitHub Actions (pytest + ruff) |

## Project Stats

- **9,300+** lines of code across Python engine, FastAPI API, and Next.js dashboard
- **165** automated tests
- **9** blockchain chains supported
- **9** Nansen API endpoints integrated
- **5** dashboard pages with responsive mobile layouts
- **4-source** data pipeline per chain

## License

MIT
