# CLI Showcase Design — v5.3

## Goal
Make CLI usage impossible for judges to miss. Live activity feed, usage stats, pre-built deep dives, and try-it-yourself section.

## Components

### 1. CLI Activity Log (`api/cli_log.py`)
- In-memory deque (max 100 entries)
- Wraps nansen._run() and nansen._api_post() to log every call
- Entry: {command, chain, endpoint, credits, status, timestamp, token_count}
- API: GET /api/cli/activity, GET /api/cli/stats

### 2. Pre-built Deep Dives (scheduler.py)
- After CLI enrichment, pick top 3 divergent ETH/BNB tokens
- Call flow_intelligence + who_bought_sold + token_indicators
- Store in cache as prefetched_dives
- Active production endpoints: screener, netflow, flow-intelligence, who-bought-sold, indicators = 5

### 3. Dashboard CLI Activity Panel (CLIActivity.tsx)
- Terminal-style feed on main dashboard
- Shows command, chain, status, credits, timestamp
- Green/red status indicators
- SWR auto-refresh

### 4. MetricCards CLI Stats
- CLI Calls count, Credits Used, Endpoints Active

### 5. About Page: Try It Yourself
- Copyable CLI commands with descriptions

## Credit Cost
- Enrichment: ~12 credits/cycle (existing)
- Deep dives: ~3 tokens × 3 endpoints × varies = ~33 credits/cycle
- Total: ~45 credits per 30min cycle = ~2,160/day
- With 100 credits: 2 full cycles

## Files Changed
- NEW: api/cli_log.py
- EDIT: src/nansen_divergence/nansen.py (add logging hooks)
- EDIT: api/scheduler.py (add pre-built deep dives)
- EDIT: api/main.py (add /api/cli/* endpoints)
- NEW: web/src/components/CLIActivity.tsx
- EDIT: web/src/components/MetricCards.tsx
- EDIT: web/src/app/about/page.tsx
- EDIT: web/src/app/page.tsx (add CLIActivity panel)
