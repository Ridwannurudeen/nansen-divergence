# v5.0 Web App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FastAPI + Next.js web app replacing the Streamlit dashboard, deployed on VPS via Docker Compose with nginx.

**Architecture:** FastAPI wraps the existing Python engine with REST endpoints + a scheduler for auto-scans. Next.js frontend (Tailwind, react-plotly.js, SWR) fetches cached data and renders a terminal-themed trading dashboard. Docker Compose runs both services, nginx proxies traffic.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, APScheduler, Next.js 14, Tailwind CSS, react-plotly.js, SWR, Docker, nginx

---

### Task 1: Create API directory and FastAPI app skeleton

**Files:**
- Create: `api/main.py`
- Create: `api/requirements.txt`
- Create: `api/__init__.py`

**Step 1: Create api/requirements.txt**

```
fastapi>=0.109.0
uvicorn>=0.27.0
apscheduler>=3.10.4
```

**Step 2: Create api/__init__.py**

Empty file.

**Step 3: Create api/main.py**

```python
"""Nansen Divergence Scanner — FastAPI Backend."""

import sys
from pathlib import Path

# Add src/ to path so we can import nansen_divergence
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Nansen Divergence API",
    version="5.0.0",
    description="Multi-chain smart money divergence scanner",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "5.0.0"}
```

**Step 4: Verify it runs**

Run: `cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence" && pip install fastapi uvicorn && python -m uvicorn api.main:app --host 0.0.0.0 --port 8010`
Expected: Server starts, `curl http://localhost:8010/api/health` returns `{"status":"ok","version":"5.0.0"}`

**Step 5: Commit**

```bash
git add api/
git commit -m "feat: FastAPI skeleton with health endpoint"
```

---

### Task 2: Add cached scan storage and /api/scan/latest endpoint

**Files:**
- Create: `api/cache.py`
- Modify: `api/main.py`
- Create: `api/tests/test_cache.py`

**Step 1: Write failing test**

Create `api/tests/__init__.py` (empty) and `api/tests/test_cache.py`:

```python
"""Tests for scan cache layer."""

import json
import os
import tempfile

import pytest

from api.cache import get_latest_scan, save_cached_scan


@pytest.fixture
def cache_dir(tmp_path):
    return str(tmp_path)


def test_save_and_retrieve(cache_dir):
    data = {
        "results": [{"token_symbol": "ETH", "phase": "ACCUMULATION", "divergence_strength": 0.7}],
        "radar": [],
        "summary": {"total_tokens": 1},
        "chains": ["ethereum"],
    }
    save_cached_scan(data, cache_dir=cache_dir)
    retrieved = get_latest_scan(cache_dir=cache_dir)
    assert retrieved is not None
    assert retrieved["results"][0]["token_symbol"] == "ETH"
    assert "timestamp" in retrieved


def test_no_cache_returns_none(cache_dir):
    assert get_latest_scan(cache_dir=cache_dir) is None
```

**Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence" && python -m pytest api/tests/test_cache.py -v`
Expected: FAIL — ImportError

**Step 3: Implement api/cache.py**

```python
"""Scan result caching — stores latest scan as JSON file."""

import json
import os
from datetime import datetime, timezone

DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".nansen-divergence", "cache")


def save_cached_scan(data: dict, cache_dir: str | None = None) -> str:
    """Save scan results to cache. Returns path to cached file."""
    d = cache_dir or DEFAULT_CACHE_DIR
    os.makedirs(d, exist_ok=True)
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    path = os.path.join(d, "latest.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def get_latest_scan(cache_dir: str | None = None) -> dict | None:
    """Read the latest cached scan. Returns None if no cache exists."""
    d = cache_dir or DEFAULT_CACHE_DIR
    path = os.path.join(d, "latest.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)
```

**Step 4: Add endpoint to api/main.py**

Add imports and endpoint:

```python
from api.cache import get_latest_scan

@app.get("/api/scan/latest")
def scan_latest(chain: str | None = None):
    data = get_latest_scan()
    if data is None:
        return {"error": "No scan data available yet", "results": [], "summary": {}}
    if chain:
        data["results"] = [r for r in data.get("results", []) if r.get("chain") == chain]
    return data
```

**Step 5: Run tests**

Run: `cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence" && python -m pytest api/tests/test_cache.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/
git commit -m "feat: scan cache layer and /api/scan/latest endpoint"
```

---

### Task 3: Add scheduler for automatic scans

**Files:**
- Create: `api/scheduler.py`
- Modify: `api/main.py`

**Step 1: Create api/scheduler.py**

```python
"""Background scheduler — runs scans at fixed intervals and caches results."""

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger("nansen.scheduler")

DEFAULT_CHAINS = ["ethereum", "bnb", "solana", "base", "arbitrum"]
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))


def _run_scan():
    """Execute a multi-chain scan and cache the results."""
    from nansen_divergence.divergence import alpha_score
    from nansen_divergence.history import (
        backtest_stats,
        detect_new_tokens,
        init_db,
        save_scan,
        validate_signals,
    )
    from nansen_divergence.scanner import (
        flatten_and_rank,
        flatten_radar,
        scan_multi_chain,
        summarize,
    )

    from api.cache import save_cached_scan

    chains = os.getenv("SCAN_CHAINS", ",".join(DEFAULT_CHAINS)).split(",")
    limit = int(os.getenv("SCAN_LIMIT", "20"))

    logger.info(f"Starting scheduled scan: {chains} (limit={limit})")

    try:
        chain_results, chain_radar = scan_multi_chain(chains, timeframe="24h", limit=limit)
        flat = flatten_and_rank(chain_results)
        radar = flatten_radar(chain_radar)

        # History + new token detection
        try:
            db_conn = init_db()
            new_addrs = detect_new_tokens(flat, conn=db_conn)
            for token in flat:
                if token.get("token_address", "").lower() in new_addrs:
                    token["is_new"] = True
            save_scan(flat, chains, "24h", conn=db_conn)
            validations = validate_signals(flat, lookback_days=7, conn=db_conn)
            bstats = backtest_stats(validations)
            db_conn.close()
        except Exception as e:
            logger.warning(f"History error: {e}")
            validations = []
            bstats = backtest_stats([])

        summary = summarize(flat, radar)

        # Add alpha scores to each result
        for r in flat:
            r["alpha_score"] = alpha_score(r.get("divergence_strength", 0))

        save_cached_scan({
            "results": flat,
            "radar": radar,
            "summary": summary,
            "chains": chains,
            "validations": validations,
            "backtest": bstats,
        })
        logger.info(f"Scan complete: {summary.get('total_tokens', 0)} tokens, {summary.get('divergence_signals', 0)} signals")

    except Exception as e:
        logger.error(f"Scan failed: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(_run_scan, "interval", minutes=SCAN_INTERVAL_MINUTES, id="auto_scan")
    # Run first scan immediately
    scheduler.add_job(_run_scan, "date", id="initial_scan")
    scheduler.start()
    logger.info(f"Scheduler started: scanning every {SCAN_INTERVAL_MINUTES} minutes")
    return scheduler
```

**Step 2: Wire scheduler into api/main.py**

Add to main.py:

```python
from contextlib import asynccontextmanager
from api.scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()

# Update FastAPI app to use lifespan
app = FastAPI(
    title="Nansen Divergence API",
    version="5.0.0",
    description="Multi-chain smart money divergence scanner",
    lifespan=lifespan,
)
```

**Step 3: Add remaining endpoints to api/main.py**

```python
from fastapi import Header, HTTPException
from nansen_divergence.history import get_scan_history, get_recent_signals, backtest_stats, validate_signals, init_db

@app.get("/api/history/signals")
def history_signals(days: int = 7):
    signals = get_recent_signals(days=days)
    return {"signals": signals}

@app.get("/api/history/performance")
def history_performance():
    data = get_latest_scan()
    if data and "backtest" in data:
        return data["backtest"]
    return {"total_signals": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "avg_return": 0.0, "best_return": 0.0, "worst_return": 0.0}

@app.post("/api/scan/run")
def scan_on_demand(
    chains: list[str] = ["ethereum"],
    limit: int = 20,
    x_nansen_key: str = Header(None),
):
    if not x_nansen_key:
        raise HTTPException(status_code=401, detail="Nansen API key required. Pass X-Nansen-Key header.")

    import os
    os.environ["NANSEN_API_KEY"] = x_nansen_key

    from nansen_divergence.scanner import scan_multi_chain, flatten_and_rank, flatten_radar, summarize
    from nansen_divergence.divergence import alpha_score

    chain_results, chain_radar = scan_multi_chain(chains, timeframe="24h", limit=limit)
    flat = flatten_and_rank(chain_results)
    radar = flatten_radar(chain_radar)
    summary = summarize(flat, radar)

    for r in flat:
        r["alpha_score"] = alpha_score(r.get("divergence_strength", 0))

    return {"results": flat, "radar": radar, "summary": summary, "chains": chains}

@app.get("/api/deep-dive/{chain}/{token}")
def deep_dive(chain: str, token: str, x_nansen_key: str = Header(None)):
    if not x_nansen_key:
        raise HTTPException(status_code=401, detail="Nansen API key required.")

    import os
    os.environ["NANSEN_API_KEY"] = x_nansen_key

    from nansen_divergence.deep_dive import deep_dive_token
    data = deep_dive_token(chain, token, days=7, profile_count=3)
    return data
```

**Step 4: Test endpoints manually**

Run: `python -m uvicorn api.main:app --host 0.0.0.0 --port 8010`
Verify:
- `curl http://localhost:8010/api/health` → 200
- `curl http://localhost:8010/api/scan/latest` → results or empty
- `curl http://localhost:8010/api/history/performance` → backtest stats

**Step 5: Commit**

```bash
git add api/
git commit -m "feat: scheduler + all API endpoints (cached scan, on-demand, deep-dive, history)"
```

---

### Task 4: Create Next.js project with Tailwind and terminal theme

**Files:**
- Create: `web/` directory with Next.js 14 project

**Step 1: Scaffold Next.js project**

```bash
cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence"
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

**Step 2: Configure Tailwind theme in web/tailwind.config.ts**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0d0d0d",
        surface: "#1a1a1a",
        border: "#2a2a2a",
        accent: "#f97316",
        secondary: "#fb923c",
        bullish: "#4ade80",
        bearish: "#f43f5e",
        warning: "#facc15",
        neutral: "#6366f1",
        muted: "#737373",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
```

**Step 3: Set up global styles in web/src/app/globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

body {
  background-color: #0d0d0d;
  color: #d4d4d4;
  font-family: system-ui, -apple-system, sans-serif;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'JetBrains Mono', monospace;
}
```

**Step 4: Set up layout in web/src/app/layout.tsx**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SM Divergence — Smart Money vs Price",
  description: "Multi-chain smart money divergence scanner with Wyckoff phase classification",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg min-h-screen">{children}</body>
    </html>
  );
}
```

**Step 5: Create placeholder page in web/src/app/page.tsx**

```tsx
export default function Home() {
  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-mono font-bold text-accent">SM DIVERGENCE</h1>
      <p className="text-muted mt-2">Smart Money vs Price — Who's Right?</p>
    </main>
  );
}
```

**Step 6: Test**

```bash
cd web && npm run dev
```
Expected: Page loads at http://localhost:3000 with orange title on black background.

**Step 7: Commit**

```bash
cd .. && git add web/
git commit -m "feat: Next.js project with Tailwind terminal theme"
```

---

### Task 5: Create API client and TypeScript types

**Files:**
- Create: `web/src/lib/types.ts`
- Create: `web/src/lib/api.ts`

**Step 1: Create web/src/lib/types.ts**

```typescript
export interface Token {
  chain: string;
  token_address: string;
  token_symbol: string;
  price_usd: number;
  price_change: number;
  market_cap: number;
  volume_24h: number;
  market_netflow: number;
  sm_net_flow: number;
  sm_buy_volume: number;
  sm_sell_volume: number;
  sm_trader_count: number;
  sm_wallet_labels: string[];
  sm_holdings_value: number;
  sm_holdings_change: number;
  divergence_strength: number;
  alpha_score: number;
  phase: "ACCUMULATION" | "DISTRIBUTION" | "MARKUP" | "MARKDOWN";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  narrative: string;
  has_sm_data: boolean;
  is_new?: boolean;
}

export interface RadarToken {
  chain: string;
  token_address: string;
  token_symbol: string;
  sm_net_flow_24h: number;
  sm_net_flow_7d: number;
  sm_trader_count: number;
  sm_sectors: string[];
  market_cap: number;
}

export interface ScanSummary {
  total_tokens: number;
  with_sm_data: number;
  sm_data_pct: number;
  divergence_signals: number;
  accumulation: number;
  distribution: number;
  confidence_high: number;
  confidence_medium: number;
  confidence_low: number;
}

export interface BacktestStats {
  total_signals: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_return: number;
  best_return: number;
  worst_return: number;
}

export interface ScanData {
  results: Token[];
  radar: RadarToken[];
  summary: ScanSummary;
  chains: string[];
  timestamp: string;
  backtest: BacktestStats;
}
```

**Step 2: Install SWR**

```bash
cd web && npm install swr
```

**Step 3: Create web/src/lib/api.ts**

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export { fetcher, API_BASE };
```

**Step 4: Commit**

```bash
cd .. && git add web/
git commit -m "feat: TypeScript types and SWR API client"
```

---

### Task 6: Build dashboard components

**Files:**
- Create: `web/src/components/Header.tsx`
- Create: `web/src/components/ChainPulse.tsx`
- Create: `web/src/components/MetricCards.tsx`
- Create: `web/src/components/SignalFeed.tsx`
- Create: `web/src/components/TokenTable.tsx`

**Step 1: Header.tsx**

```tsx
interface HeaderProps {
  timestamp?: string;
}

export function Header({ timestamp }: HeaderProps) {
  const time = timestamp ? new Date(timestamp).toLocaleTimeString() : "—";
  return (
    <header className="flex items-center justify-between py-4 border-b border-border">
      <div>
        <h1 className="text-2xl font-mono font-bold text-accent">SM DIVERGENCE</h1>
        <p className="text-sm text-muted">Smart Money vs Price — Who's Right?</p>
      </div>
      <div className="text-right text-sm text-muted font-mono">
        <div>Last scan: {time}</div>
      </div>
    </header>
  );
}
```

**Step 2: ChainPulse.tsx**

```tsx
import { Token } from "@/lib/types";

const CHAINS = [
  { id: "ethereum", label: "ETH" },
  { id: "bnb", label: "BNB" },
  { id: "solana", label: "SOL" },
  { id: "base", label: "BASE" },
  { id: "arbitrum", label: "ARB" },
  { id: "polygon", label: "POL" },
  { id: "optimism", label: "OP" },
  { id: "avalanche", label: "AVAX" },
  { id: "linea", label: "LNA" },
];

interface ChainPulseProps {
  results: Token[];
  scannedChains: string[];
  activeChain: string | null;
  onChainClick: (chain: string | null) => void;
}

export function ChainPulse({ results, scannedChains, activeChain, onChainClick }: ChainPulseProps) {
  const chainPhases: Record<string, { acc: number; dis: number }> = {};
  for (const r of results) {
    if (!chainPhases[r.chain]) chainPhases[r.chain] = { acc: 0, dis: 0 };
    if (r.phase === "ACCUMULATION") chainPhases[r.chain].acc++;
    else if (r.phase === "DISTRIBUTION") chainPhases[r.chain].dis++;
  }

  return (
    <div className="flex flex-wrap gap-3 py-3">
      <button
        onClick={() => onChainClick(null)}
        className={`px-3 py-1 rounded text-sm font-mono transition ${
          activeChain === null ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white"
        }`}
      >
        ALL
      </button>
      {CHAINS.map(({ id, label }) => {
        const scanned = scannedChains.includes(id);
        const p = chainPhases[id];
        const dotColor = !scanned
          ? "bg-muted"
          : p && p.acc > p.dis
          ? "bg-bullish"
          : p && p.dis > p.acc
          ? "bg-bearish"
          : "bg-muted";
        const isActive = activeChain === id;

        return (
          <button
            key={id}
            onClick={() => onChainClick(isActive ? null : id)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-sm font-mono transition ${
              isActive ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white"
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${dotColor}`} />
            {label}
          </button>
        );
      })}
    </div>
  );
}
```

**Step 3: MetricCards.tsx**

```tsx
import { ScanSummary, BacktestStats } from "@/lib/types";

interface MetricCardsProps {
  summary: ScanSummary;
  backtest: BacktestStats;
  avgAlpha: number;
}

function Card({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="text-xs font-mono text-muted uppercase tracking-wider">{label}</div>
      <div className={`text-2xl font-mono font-bold mt-1 ${color || "text-accent"}`}>{value}</div>
    </div>
  );
}

export function MetricCards({ summary, backtest, avgAlpha }: MetricCardsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 py-4">
      <Card label="Tokens" value={summary.total_tokens} />
      <Card label="Divergence" value={summary.divergence_signals} />
      <Card label="Win Rate" value={backtest.total_signals > 0 ? `${backtest.win_rate}%` : "N/A"} color="text-bullish" />
      <Card label="HIGH" value={summary.confidence_high} color="text-bullish" />
      <Card label="MEDIUM" value={summary.confidence_medium} color="text-secondary" />
      <Card label="Avg Alpha" value={avgAlpha} />
    </div>
  );
}
```

**Step 4: SignalFeed.tsx**

```tsx
import { Token } from "@/lib/types";

const PHASE_COLORS: Record<string, string> = {
  ACCUMULATION: "border-bullish",
  DISTRIBUTION: "border-bearish",
  MARKUP: "border-neutral",
  MARKDOWN: "border-warning",
};

const CONF_STYLES: Record<string, string> = {
  HIGH: "bg-bullish text-bg",
  MEDIUM: "bg-accent text-bg",
  LOW: "bg-surface text-muted",
};

function fmtUsd(val: number): string {
  const sign = val > 0 ? "+" : val < 0 ? "-" : "";
  const abs = Math.abs(val);
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

interface SignalFeedProps {
  results: Token[];
}

export function SignalFeed({ results }: SignalFeedProps) {
  const signals = results
    .filter((r) => ["ACCUMULATION", "DISTRIBUTION"].includes(r.phase) && ["HIGH", "MEDIUM"].includes(r.confidence))
    .sort((a, b) => b.divergence_strength - a.divergence_strength)
    .slice(0, 15);

  if (signals.length === 0) {
    return <div className="text-muted text-sm font-mono py-4">No divergence signals detected.</div>;
  }

  return (
    <div className="space-y-2 max-h-[420px] overflow-y-auto pr-2">
      {signals.map((t, i) => (
        <div key={`${t.chain}-${t.token_address}-${i}`} className={`border-l-4 ${PHASE_COLORS[t.phase]} bg-surface rounded-r px-3 py-2`}>
          <div className="flex items-center gap-2 text-sm font-mono">
            <span className="font-bold text-white">{t.token_symbol}</span>
            <span className="text-muted text-xs">{t.chain.slice(0, 3).toUpperCase()}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${CONF_STYLES[t.confidence]}`}>
              {t.phase === "ACCUMULATION" ? "ACC" : "DIS"}
            </span>
            <span className="text-accent font-bold">a{t.alpha_score}</span>
            <span className={t.price_change > 0 ? "text-bullish" : "text-bearish"}>
              {t.price_change > 0 ? "+" : ""}{(t.price_change * 100).toFixed(1)}%
            </span>
          </div>
          {t.narrative && <div className="text-xs text-muted mt-1 italic">{t.narrative}</div>}
        </div>
      ))}
    </div>
  );
}
```

**Step 5: TokenTable.tsx**

```tsx
"use client";

import { useState } from "react";
import { Token } from "@/lib/types";

const PHASE_ORDER = ["ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN"] as const;
const PHASE_LABELS: Record<string, { label: string; color: string; desc: string }> = {
  ACCUMULATION: { label: "ACCUMULATION", color: "text-bullish", desc: "SM buying into price weakness" },
  DISTRIBUTION: { label: "DISTRIBUTION", color: "text-bearish", desc: "SM exiting into price strength" },
  MARKUP: { label: "MARKUP", color: "text-neutral", desc: "Trend confirmed" },
  MARKDOWN: { label: "MARKDOWN", color: "text-warning", desc: "Capitulation" },
};

const DEXSCREENER_SLUGS: Record<string, string> = {
  ethereum: "ethereum", bnb: "bsc", solana: "solana", base: "base",
  arbitrum: "arbitrum", polygon: "polygon", optimism: "optimism", avalanche: "avalanche", linea: "linea",
};

function fmtUsd(val: number): string {
  const sign = val > 0 ? "+" : val < 0 ? "-" : "";
  const abs = Math.abs(val);
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  if (abs >= 1) return `${sign}$${abs.toFixed(0)}`;
  return `${sign}$${abs.toFixed(2)}`;
}

function AlphaBar({ score }: { score: number }) {
  const color = score >= 70 ? "#f43f5e" : score >= 40 ? "#f97316" : "#6366f1";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono font-bold" style={{ color }}>{score}</span>
    </div>
  );
}

function ConfPill({ confidence }: { confidence: string }) {
  const cls = confidence === "HIGH" ? "bg-bullish text-bg" : confidence === "MEDIUM" ? "bg-accent text-bg" : "bg-border text-muted";
  return <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${cls}`}>{confidence}</span>;
}

interface TokenTableProps {
  results: Token[];
}

export function TokenTable({ results }: TokenTableProps) {
  const [activePhase, setActivePhase] = useState<string | null>(null);

  const grouped: Record<string, Token[]> = {};
  for (const p of PHASE_ORDER) grouped[p] = [];
  for (const r of results) {
    if (grouped[r.phase]) grouped[r.phase].push(r);
  }
  for (const p of PHASE_ORDER) {
    grouped[p].sort((a, b) => b.divergence_strength - a.divergence_strength);
  }

  const phases = activePhase ? [activePhase] : [...PHASE_ORDER];

  return (
    <div>
      {/* Phase filter tabs */}
      <div className="flex gap-2 py-3 border-b border-border mb-4">
        <button
          onClick={() => setActivePhase(null)}
          className={`px-3 py-1 rounded text-sm font-mono ${!activePhase ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white"}`}
        >
          ALL
        </button>
        {PHASE_ORDER.map((p) => {
          const info = PHASE_LABELS[p];
          const count = grouped[p].length;
          if (count === 0) return null;
          return (
            <button
              key={p}
              onClick={() => setActivePhase(activePhase === p ? null : p)}
              className={`px-3 py-1 rounded text-sm font-mono ${activePhase === p ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white"}`}
            >
              <span className={info.color}>{info.label}</span> ({count})
            </button>
          );
        })}
      </div>

      {/* Token tables per phase */}
      {phases.map((phase) => {
        const tokens = grouped[phase];
        if (!tokens || tokens.length === 0) return null;
        const info = PHASE_LABELS[phase];

        return (
          <div key={phase} className="mb-6">
            <h3 className={`font-mono font-bold text-sm mb-2 ${info.color}`}>
              {info.label} — <span className="text-muted font-normal">{info.desc}</span> ({tokens.length})
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-muted text-xs border-b border-border">
                    <th className="text-left py-2 px-2">Token</th>
                    <th className="text-left py-2 px-2">Chain</th>
                    <th className="text-right py-2 px-2">Price</th>
                    <th className="text-right py-2 px-2">Flow</th>
                    <th className="text-left py-2 px-2 w-32">Alpha</th>
                    <th className="text-center py-2 px-2">Conf</th>
                    <th className="text-center py-2 px-2">Chart</th>
                  </tr>
                </thead>
                <tbody>
                  {tokens.map((t, i) => {
                    const flow = t.sm_net_flow !== 0 ? t.sm_net_flow : t.market_netflow;
                    const slug = DEXSCREENER_SLUGS[t.chain] || t.chain;
                    const dexUrl = `https://dexscreener.com/${slug}/${t.token_address}`;
                    return (
                      <tr key={`${t.chain}-${t.token_address}-${i}`} className="border-b border-border/50 hover:bg-surface/50">
                        <td className="py-2 px-2">
                          <span className="text-white font-bold">{t.token_symbol}</span>
                          {t.is_new && <span className="ml-1 text-xs bg-bearish text-white px-1 rounded">NEW</span>}
                        </td>
                        <td className="py-2 px-2 text-muted">{t.chain}</td>
                        <td className={`py-2 px-2 text-right ${t.price_change > 0 ? "text-bullish" : "text-bearish"}`}>
                          {t.price_change > 0 ? "+" : ""}{(t.price_change * 100).toFixed(1)}%
                        </td>
                        <td className={`py-2 px-2 text-right ${flow > 0 ? "text-bullish" : "text-bearish"}`}>
                          {fmtUsd(flow)}
                        </td>
                        <td className="py-2 px-2"><AlphaBar score={t.alpha_score} /></td>
                        <td className="py-2 px-2 text-center"><ConfPill confidence={t.confidence} /></td>
                        <td className="py-2 px-2 text-center">
                          <a href={dexUrl} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-secondary">
                            View
                          </a>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

**Step 6: Commit**

```bash
git add web/src/
git commit -m "feat: dashboard components — Header, ChainPulse, MetricCards, SignalFeed, TokenTable"
```

---

### Task 7: Assemble dashboard page

**Files:**
- Modify: `web/src/app/page.tsx`

**Step 1: Wire everything together**

```tsx
"use client";

import useSWR from "swr";
import { useState } from "react";
import { ScanData } from "@/lib/types";
import { fetcher } from "@/lib/api";
import { Header } from "@/components/Header";
import { ChainPulse } from "@/components/ChainPulse";
import { MetricCards } from "@/components/MetricCards";
import { SignalFeed } from "@/components/SignalFeed";
import { TokenTable } from "@/components/TokenTable";

export default function Home() {
  const { data, error, isLoading } = useSWR<ScanData>("/api/scan/latest", fetcher, {
    refreshInterval: 60000,
  });
  const [activeChain, setActiveChain] = useState<string | null>(null);

  const filteredResults = data?.results
    ? activeChain
      ? data.results.filter((r) => r.chain === activeChain)
      : data.results
    : [];

  const avgAlpha = filteredResults.length > 0
    ? Math.round(filteredResults.reduce((sum, r) => sum + (r.alpha_score || 0), 0) / filteredResults.length)
    : 0;

  return (
    <main className="max-w-7xl mx-auto px-4 py-4">
      <Header timestamp={data?.timestamp} />

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-accent font-mono animate-pulse">Loading scan data...</div>
        </div>
      )}

      {error && (
        <div className="bg-surface border border-bearish rounded-lg p-4 my-4 font-mono text-sm text-bearish">
          Failed to load scan data. The API may still be running its first scan.
        </div>
      )}

      {data && (
        <>
          <ChainPulse
            results={data.results}
            scannedChains={data.chains}
            activeChain={activeChain}
            onChainClick={setActiveChain}
          />

          <MetricCards
            summary={data.summary}
            backtest={data.backtest || { total_signals: 0, wins: 0, losses: 0, win_rate: 0, avg_return: 0, best_return: 0, worst_return: 0 }}
            avgAlpha={avgAlpha}
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 py-4">
            <div className="lg:col-span-2">
              <h2 className="font-mono font-bold text-sm text-muted mb-2">SIGNAL FEED</h2>
              <SignalFeed results={filteredResults} />
            </div>
            <div>
              <h2 className="font-mono font-bold text-sm text-muted mb-2">SM RADAR</h2>
              <div className="bg-surface border border-border rounded-lg p-3 max-h-[420px] overflow-y-auto">
                {data.radar && data.radar.length > 0 ? (
                  <div className="space-y-1 text-xs font-mono">
                    {data.radar.slice(0, 15).map((r, i) => (
                      <div key={i} className="flex justify-between py-1 border-b border-border/50">
                        <span className="text-white">{r.token_symbol}</span>
                        <span className="text-muted">{r.chain.slice(0, 3).toUpperCase()}</span>
                        <span className={r.sm_net_flow_24h > 0 ? "text-bullish" : "text-bearish"}>
                          {r.sm_net_flow_24h > 0 ? "+" : ""}{(r.sm_net_flow_24h / 1e6).toFixed(1)}M
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted text-sm">No radar data yet.</div>
                )}
              </div>
            </div>
          </div>

          <TokenTable results={filteredResults} />
        </>
      )}

      {!isLoading && !error && !data && (
        <div className="text-center py-20">
          <h2 className="text-2xl font-mono font-bold text-accent mb-4">SM DIVERGENCE</h2>
          <p className="text-muted">Waiting for first scan to complete...</p>
          <p className="text-muted text-sm mt-2">The scanner runs automatically every 30 minutes.</p>
        </div>
      )}
    </main>
  );
}
```

**Step 2: Create about page at web/src/app/about/page.tsx**

```tsx
export default function About() {
  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-mono font-bold text-accent mb-6">How It Works</h1>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Wyckoff Phases</h2>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm font-mono">
            <thead><tr className="border-b border-border text-muted">
              <th className="text-left p-3">Phase</th><th className="p-3">SM Flow</th><th className="p-3">Price</th><th className="text-left p-3">Signal</th>
            </tr></thead>
            <tbody>
              <tr className="border-b border-border/50"><td className="p-3 text-bullish font-bold">ACCUMULATION</td><td className="p-3 text-center">Buying</td><td className="p-3 text-center">Falling</td><td className="p-3">Bullish divergence</td></tr>
              <tr className="border-b border-border/50"><td className="p-3 text-bearish font-bold">DISTRIBUTION</td><td className="p-3 text-center">Selling</td><td className="p-3 text-center">Rising</td><td className="p-3">Bearish divergence</td></tr>
              <tr className="border-b border-border/50"><td className="p-3 text-neutral font-bold">MARKUP</td><td className="p-3 text-center">Buying</td><td className="p-3 text-center">Rising</td><td className="p-3">Trend confirmed</td></tr>
              <tr><td className="p-3 text-warning font-bold">MARKDOWN</td><td className="p-3 text-center">Selling</td><td className="p-3 text-center">Falling</td><td className="p-3">Capitulation</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Alpha Score</h2>
        <p className="text-muted leading-relaxed">
          Each token gets an Alpha Score (0-100) based on four weighted factors:
          flow magnitude (40%), price movement (25%), wallet diversity (20%), and holdings conviction (15%).
          Scores use log-scaled normalization to prevent large-cap tokens from dominating.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-mono font-bold text-white mb-3">Data Sources</h2>
        <p className="text-muted leading-relaxed">
          Scans 9 blockchains using Nansen's smart money data: token screener, SM dex-trades,
          SM holdings, and SM netflow. Results are cached and auto-refreshed every 30 minutes.
        </p>
      </section>
    </main>
  );
}
```

**Step 3: Test locally**

Run API: `python -m uvicorn api.main:app --port 8010`
Run Web: `cd web && npm run dev`
Verify dashboard loads and fetches data.

**Step 4: Commit**

```bash
git add web/
git commit -m "feat: assemble dashboard page + about page"
```

---

### Task 8: Dockerize and create docker-compose.yml

**Files:**
- Create: `api/Dockerfile`
- Create: `web/Dockerfile`
- Create: `docker-compose.yml`
- Create: `nginx.conf`
- Create: `.env.example`

**Step 1: Create api/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/
COPY api/ /app/api/

ENV PYTHONPATH=/app/src:/app

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8010"]
```

**Step 2: Create web/Dockerfile**

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY web/package*.json ./
RUN npm ci
COPY web/ ./

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3010
ENV PORT=3010
CMD ["node", "server.js"]
```

**Step 3: Add standalone output to web/next.config.ts**

Add `output: "standalone"` to the Next.js config.

**Step 4: Create docker-compose.yml**

```yaml
services:
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    container_name: nansen-api
    ports:
      - "127.0.0.1:8010:8010"
    env_file: .env
    restart: unless-stopped

  web:
    build:
      context: .
      dockerfile: web/Dockerfile
      args:
        NEXT_PUBLIC_API_URL: ""
    container_name: nansen-web
    ports:
      - "127.0.0.1:3010:3010"
    depends_on:
      - api
    restart: unless-stopped
```

**Step 5: Create nginx.conf**

```nginx
server {
    listen 80;
    server_name _;

    location /api/ {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        proxy_pass http://127.0.0.1:3010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Step 6: Create .env.example**

```
NANSEN_API_KEY=your_nansen_api_key_here
SCAN_INTERVAL_MINUTES=30
SCAN_CHAINS=ethereum,bnb,solana,base,arbitrum
SCAN_LIMIT=20
```

**Step 7: Commit**

```bash
git add api/Dockerfile web/Dockerfile docker-compose.yml nginx.conf .env.example
git commit -m "feat: Docker setup — api + web containers, nginx config, compose"
```

---

### Task 9: Deploy to VPS

**Step 1: Push code to GitHub**

```bash
git push origin main
```

**Step 2: Clone on VPS**

```bash
ssh root@75.119.153.252
cd /opt
git clone https://github.com/Ridwannurudeen/nansen-divergence.git
cd nansen-divergence
```

**Step 3: Create .env with Nansen API key**

```bash
cp .env.example .env
nano .env  # Set NANSEN_API_KEY
```

**Step 4: Build and start containers**

```bash
docker compose up -d --build
```

**Step 5: Set up nginx**

```bash
cp nginx.conf /etc/nginx/sites-available/nansen-divergence
ln -s /etc/nginx/sites-available/nansen-divergence /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

**Step 6: Open firewall**

```bash
ufw allow 80
```

**Step 7: Verify**

```bash
curl http://localhost:8010/api/health
curl http://localhost:3010
curl http://75.119.153.252/api/health
```

**Step 8: Commit any deployment fixes**

---

### Task 10: Final testing and cleanup

**Step 1: Run Python tests**

```bash
cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence"
python -m pytest tests/ -v
```
Expected: All 138+ tests pass

**Step 2: Run Next.js build**

```bash
cd web && npm run build
```
Expected: Build succeeds

**Step 3: Verify live site**

- `http://75.119.153.252/` → Dashboard loads
- `http://75.119.153.252/api/health` → Health check
- `http://75.119.153.252/api/scan/latest` → Cached scan data
- `http://75.119.153.252/about` → About page

**Step 4: Commit final state**

```bash
git add -A
git commit -m "v5.0.0: FastAPI + Next.js web app — deployed"
git push
```
