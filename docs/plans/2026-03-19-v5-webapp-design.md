# v5.0 Web App Design — FastAPI + Next.js

## Goal
Replace the Streamlit dashboard with a proper web application. FastAPI backend serves cached scan data + on-demand endpoints. Next.js frontend delivers a fast, shareable, mobile-responsive trading terminal experience that looks nothing like a Streamlit app.

## Architecture

**Monorepo** with two services deployed via Docker Compose on VPS (75.119.153.252).

```
nansen-divergence/
├── api/                      # FastAPI backend
│   ├── main.py               # App + endpoints
│   ├── scheduler.py          # APScheduler auto-scans
│   ├── cache.py              # SQLite read layer for cached results
│   ├── requirements.txt      # fastapi, uvicorn, apscheduler
│   └── Dockerfile
├── web/                      # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx      # Dashboard (main page)
│   │   │   ├── about/page.tsx
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ChainPulse.tsx
│   │   │   ├── MetricCards.tsx
│   │   │   ├── PhaseHeatmap.tsx
│   │   │   ├── SignalFeed.tsx
│   │   │   ├── TokenTable.tsx
│   │   │   └── Header.tsx
│   │   └── lib/
│   │       ├── api.ts        # API client
│   │       └── types.ts      # TypeScript types
│   ├── tailwind.config.ts
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── .env                      # NANSEN_API_KEY for scheduled scans
└── src/                      # Existing Python engine (unchanged)
    └── nansen_divergence/
```

## Backend API

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/scan/latest` | None | Latest cached scan results (all chains) |
| GET | `/api/scan/latest/{chain}` | None | Latest results for one chain |
| POST | `/api/scan/run` | X-Nansen-Key | On-demand scan (BYO key) |
| GET | `/api/deep-dive/{chain}/{token}` | X-Nansen-Key | Token deep dive (BYO key) |
| GET | `/api/history/signals` | None | Recent divergent signals |
| GET | `/api/history/performance` | None | Backtest stats |
| GET | `/api/health` | None | Server status + last scan time |

### Scheduler

APScheduler runs `scan_multi_chain()` every 30 min on default chains (ethereum, bnb, solana, base, arbitrum). Results saved to SQLite via existing `history.py`. The `/api/scan/latest` endpoint reads the latest cached data.

### Auth Model (Hybrid)

- **Free tier:** Cached scan results, signal history, performance stats. No key needed.
- **BYO key:** On-demand scans and deep dives. User passes `X-Nansen-Key` header.

## Frontend

### Tech Stack
- Next.js 14 (App Router)
- Tailwind CSS
- react-plotly.js (heatmap, charts)
- SWR (data fetching with auto-refresh)
- TypeScript

### Color Palette (Orange/Amber)
```
--bg:        #0d0d0d
--surface:   #1a1a1a
--border:    #2a2a2a
--accent:    #f97316
--secondary: #fb923c
--bullish:   #4ade80
--bearish:   #f43f5e
--warning:   #facc15
--neutral:   #6366f1
--text:      #d4d4d4
--muted:     #737373
```

### Pages (Phase 1)

**`/` — Dashboard**
- Auto-loads cached scan data (no "Scan" button)
- Chain pulse bar (9 chains, clickable to filter)
- 4 metric cards (Tokens, Signals, Win Rate, Avg Alpha)
- Phase heatmap (Plotly treemap, clickable cells)
- Signal feed (auto-updating, animated)
- Token table (sortable, filterable, phase-tabbed)
- Auto-refreshes every 60s via SWR

**`/about` — How It Works**
- Wyckoff phase explanation
- Scoring algorithm breakdown
- Data sources
- Comparison vs competitors (what makes this different)

### Phase 2 (future)
- `/token/{chain}/{address}` — Token detail page with deep dive
- `/performance` — Historical signal accuracy

### UX Differentiators (vs Streamlit)
1. No sidebar — controls are inline filter chips
2. Clickable tokens → detail pages (Phase 2)
3. Shareable URLs
4. Mobile-responsive (stacks vertically)
5. Auto-refreshes cached data (no manual scan for free tier)
6. Animated signal feed
7. No "*.streamlit.app" in URL

## Deployment

**VPS:** 75.119.153.252 (Contabo)
**Path:** /opt/nansen-divergence/
**Ports:** API on 8010, Web on 3010 (internal), nginx on 80/443 (external)

**Docker Compose:** Two services
- `api`: Python 3.12, uvicorn, mounts existing src/ for engine access
- `web`: Node 20, Next.js standalone build

**Nginx:** Reverse proxy
- `/api/*` → http://localhost:8010
- `/*` → http://localhost:3010

**Domain:** TBD — deploy on IP first, add domain later.

## Existing Code Reuse

The Python engine (src/nansen_divergence/) stays 100% unchanged:
- `scanner.py` — scan_multi_chain(), flatten_and_rank(), summarize()
- `divergence.py` — score_divergence(), alpha_score(), classify_phase()
- `history.py` — save_scan(), validate_signals(), backtest_stats(), detect_new_tokens()
- `deep_dive.py` — deep_dive_token()
- `nansen.py` — Dual-mode CLI/REST API adapter
- `alerts.py` — Telegram notifications (triggered by scheduler)

The Streamlit app (streamlit_app.py) stays in the repo but is no longer the primary interface.
