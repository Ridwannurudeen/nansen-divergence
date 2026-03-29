# nansen-divergence — Web Dashboard

Next.js 16 real-time dashboard for the nansen-divergence scanner.

## Pages

| Route | Description |
|-------|-------------|
| `/` | Main dashboard — heat map, signal feed, metric cards, watchlist, token table |
| `/radar` | Pre-breakout radar — high volume-activity tokens with divergent signals |
| `/performance` | Signal backtesting — win/loss donut, scatter timeline, outcome tracking |
| `/flows` | Cross-chain flows — chain momentum, sector rotation, volume aggregation |
| `/token/[chain]/[address]` | Token deep dive — flow intelligence, buyers/sellers, wallet profiles |
| `/about` | Methodology — Wyckoff phases, scoring formula, data pipeline |

## Stack

- Next.js 16 (App Router)
- React + Tailwind CSS v4
- Recharts (treemap, bar, pie, scatter, area)
- SWR (auto-refresh every 60s)
- JetBrains Mono, terminal-style dark theme

## Development

```bash
npm install
npm run dev
# Dashboard at http://localhost:3010
```

Requires the FastAPI backend running on port 8010 (or set `NEXT_PUBLIC_API_URL`).

## Production

```bash
docker compose up -d
# Served behind nginx reverse proxy
```

See the [root README](../README.md) for full setup instructions.
