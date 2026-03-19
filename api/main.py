"""Nansen Divergence Scanner — FastAPI Backend."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.cache import get_latest_scan
from api.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Nansen Divergence API",
    version="5.0.0",
    description="Multi-chain smart money divergence scanner",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    data = get_latest_scan()
    return {
        "status": "ok",
        "version": "5.0.0",
        "last_scan": data.get("timestamp") if data else None,
    }


@app.get("/api/scan/latest")
def scan_latest(chain: str | None = None):
    data = get_latest_scan()
    if data is None:
        return {"error": "No scan data available yet", "results": [], "radar": [], "summary": {}, "chains": [], "backtest": {}}
    if chain:
        data["results"] = [r for r in data.get("results", []) if r.get("chain") == chain]
    return data


@app.get("/api/history/signals")
def history_signals(days: int = 7):
    from nansen_divergence.history import get_recent_signals
    signals = get_recent_signals(days=days)
    return {"signals": signals}


@app.get("/api/history/performance")
def history_performance():
    data = get_latest_scan()
    if data and "backtest" in data:
        return data["backtest"]
    return {"total_signals": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "avg_return": 0.0, "best_return": 0.0, "worst_return": 0.0}


@app.post("/api/scan/run")
def scan_on_demand(chains: list[str] = ["ethereum"], limit: int = 20, x_nansen_key: str = Header(None)):
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
