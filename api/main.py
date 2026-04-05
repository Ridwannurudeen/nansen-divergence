"""Nansen Divergence Scanner — FastAPI Backend."""

import sys
import threading
import time as _time
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from api.cache import get_latest_scan
from api.scheduler import start_scheduler

# Simple in-memory rate limiter for expensive endpoints
_rate_lock = threading.Lock()
_rate_tracker: dict[str, float] = {}
RATE_LIMIT_SECONDS = 60  # min seconds between expensive calls per IP


def _check_rate_limit(key: str) -> bool:
    """Return True if rate limit exceeded."""
    now = _time.time()
    with _rate_lock:
        last = _rate_tracker.get(key, 0)
        if now - last < RATE_LIMIT_SECONDS:
            return True
        _rate_tracker[key] = now
        return False


# Thread lock for API key env mutation
_key_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wire CLI activity logging before scheduler starts
    from api.cli_log import log_call
    from nansen_divergence.nansen import set_log_hook
    set_log_hook(log_call)

    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Nansen Divergence API",
    version="5.3.0",
    description="Multi-chain smart money divergence scanner",
    lifespan=lifespan,
)

from api.routers import signals_v1, performance_v1, webhooks_v1, mcp_v1
app.include_router(signals_v1.router)
app.include_router(performance_v1.router)
app.include_router(webhooks_v1.router)
app.include_router(mcp_v1.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nansen.gudman.xyz",
        "http://localhost:3000",
        "http://localhost:3010",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    data = get_latest_scan()
    return {
        "status": "ok",
        "version": "5.3.0",
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
def scan_on_demand(chains: str = "ethereum", limit: int = 20, x_nansen_key: str = Header(None)):
    if not x_nansen_key:
        raise HTTPException(status_code=401, detail="Nansen API key required. Pass X-Nansen-Key header.")

    import os

    from api.cache import save_cached_scan
    from nansen_divergence.divergence import alpha_score
    from nansen_divergence.history import backtest_stats, init_db, save_scan, validate_signals
    from nansen_divergence.scanner import flatten_and_rank, flatten_radar, scan_multi_chain, summarize

    chain_list = [c.strip() for c in chains.split(",") if c.strip()]
    limit = min(limit, 50)  # clamp to prevent unbounded work

    with _key_lock:
        old_key = os.environ.get("NANSEN_API_KEY", "")
        os.environ["NANSEN_API_KEY"] = x_nansen_key
        try:
            chain_results, chain_radar = scan_multi_chain(chain_list, timeframe="24h", limit=limit)
        finally:
            os.environ["NANSEN_API_KEY"] = old_key

    flat = flatten_and_rank(chain_results)
    radar = flatten_radar(chain_radar)
    summary = summarize(flat, radar)

    for r in flat:
        r["alpha_score"] = alpha_score(r.get("divergence_strength", 0))

    init_db()
    save_scan(flat, chain_list, "24h")
    validations = validate_signals(flat, lookback_days=30)
    bstats = backtest_stats(validations)

    if not flat:
        old = get_latest_scan()
        if old and old.get("results"):
            return old

    scan_data = {
        "results": flat,
        "radar": radar,
        "summary": summary,
        "chains": chain_list,
        "validations": validations,
        "backtest": bstats,
    }
    save_cached_scan(scan_data)

    return scan_data


@app.post("/api/scan/mcp-refresh")
def scan_mcp_refresh(request: Request, max_tokens: int = 150):
    """Run a zero-credit scan using MCP general_search. Rate-limited."""
    client_ip = request.client.host if request.client else "unknown"
    if _check_rate_limit(f"mcp-refresh:{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limited. Try again in 60s.")
    max_tokens = min(max_tokens, 200)

    from api.cache import save_cached_scan
    from nansen_divergence.mcp_search import run_mcp_search_scan

    scan_data = run_mcp_search_scan(max_tokens=max_tokens)
    if scan_data.get("results"):
        save_cached_scan(scan_data)
    return scan_data


@app.get("/api/deep-dive/{chain}/{token}")
def deep_dive(chain: str, token: str, x_nansen_key: str = Header(None)):
    if not x_nansen_key:
        raise HTTPException(status_code=401, detail="Nansen API key required.")

    import os

    from nansen_divergence.deep_dive import deep_dive_token

    with _key_lock:
        old_key = os.environ.get("NANSEN_API_KEY", "")
        os.environ["NANSEN_API_KEY"] = x_nansen_key
        try:
            data = deep_dive_token(chain, token, days=7, profile_count=3)
        finally:
            os.environ["NANSEN_API_KEY"] = old_key
    return data


@app.get("/api/token/{chain}/{address}/history")
def token_history(chain: str, address: str, days: int = 30):
    """Time-series of divergence strength, phase, price for a token."""
    from nansen_divergence.history import get_token_history
    history = get_token_history(chain, address, days=days)
    return {"history": history}


@app.get("/api/token/{chain}/{address}")
def token_deep_dive(chain: str, address: str, request: Request):
    """Deep-dive using server-side Nansen API key. Rate-limited to prevent credit abuse."""
    client_ip = request.client.host if request.client else "unknown"
    if _check_rate_limit(f"deep-dive:{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limited. Try again in 60s.")
    import os
    if not os.getenv("NANSEN_API_KEY"):
        raise HTTPException(status_code=503, detail="Server Nansen API key not configured.")
    from nansen_divergence.deep_dive import deep_dive_token
    try:
        data = deep_dive_token(chain, address, days=7, profile_count=3)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Deep dive failed: {e}")
    return data


@app.get("/api/token/{chain}/{address}/summary")
def token_summary(chain: str, address: str):
    """Return cached scan data for a specific token (instant, no API call)."""
    data = get_latest_scan()
    if not data:
        raise HTTPException(status_code=404, detail="No scan data available.")
    addr_lower = address.lower()
    for r in data.get("results", []):
        if r.get("token_address", "").lower() == addr_lower and r.get("chain") == chain:
            return {"token": r, "timestamp": data.get("timestamp")}
    for r in data.get("radar", []):
        if r.get("token_address", "").lower() == addr_lower and r.get("chain") == chain:
            return {"token": r, "source": "radar", "timestamp": data.get("timestamp")}
    raise HTTPException(status_code=404, detail="Token not found in latest scan.")


@app.get("/api/flows")
def cross_chain_flows():
    """Aggregate cached scan data by chain and sector. Zero additional API calls."""
    data = get_latest_scan()
    if not data:
        return {"chains": {}, "sectors": {}, "timestamp": None}

    chains: dict[str, dict] = {}
    sectors: dict[str, dict] = {}

    for r in data.get("results", []):
        c = r.get("chain", "unknown")
        if c not in chains:
            chains[c] = {
                "token_count": 0, "sm_flow_total": 0, "sm_buy_total": 0,
                "sm_sell_total": 0, "accumulation": 0, "distribution": 0,
                "high_confidence": 0, "trader_count": 0, "momentum_score": 0,
            }
        ch = chains[c]
        ch["token_count"] += 1
        ch["sm_flow_total"] += r.get("sm_net_flow", 0)
        ch["sm_buy_total"] += r.get("sm_buy_volume", 0)
        ch["sm_sell_total"] += r.get("sm_sell_volume", 0)
        ch["trader_count"] += r.get("sm_trader_count", 0)
        if r.get("phase") == "ACCUMULATION":
            ch["accumulation"] += 1
        elif r.get("phase") == "DISTRIBUTION":
            ch["distribution"] += 1
        if r.get("confidence") == "HIGH":
            ch["high_confidence"] += 1

    for ch in chains.values():
        tc = ch["token_count"] or 1
        ch["momentum_score"] = round(
            (ch["accumulation"] - ch["distribution"]) / tc * 100, 1
        )

    for r in data.get("radar", []):
        for sector in r.get("sm_sectors", []):
            if sector not in sectors:
                sectors[sector] = {"token_count": 0, "net_flow": 0, "tokens": []}
            sectors[sector]["token_count"] += 1
            sectors[sector]["net_flow"] += r.get("sm_net_flow_24h", 0)
            sectors[sector]["tokens"].append(r.get("token_symbol", "???"))

    return {"chains": chains, "sectors": sectors, "timestamp": data.get("timestamp")}


@app.get("/api/history/sparklines")
def history_sparklines(days: int = 7, points: int = 10):
    """Sparkline data for token table mini-charts."""
    from nansen_divergence.history import get_sparkline_data
    sparklines = get_sparkline_data(days=days, points=points)
    return {"sparklines": sparklines}


@app.get("/api/history/streaks")
def history_streaks(days: int = 14):
    """Signal streak data for consecutive same-phase detections."""
    from nansen_divergence.history import get_signal_streaks
    streaks = get_signal_streaks(days=days)
    return {"streaks": streaks}


@app.get("/api/cli/activity")
def cli_activity(limit: int = 50):
    """Return recent CLI/API call activity log."""
    from api.cli_log import get_activity
    return {"activity": get_activity(limit)}


@app.get("/api/cli/stats")
def cli_stats():
    """Return aggregate CLI usage stats."""
    from api.cli_log import get_stats
    return get_stats()


@app.get("/api/history/outcomes")
def history_outcomes(days: int = 30):
    """Individual signal validations with price outcomes + aggregate stats."""
    data = get_latest_scan()
    if not data or not data.get("results"):
        return {"outcomes": [], "stats": {"total_signals": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "avg_return": 0.0, "best_return": 0.0, "worst_return": 0.0}}
    from nansen_divergence.history import backtest_stats, validate_signals
    validations = validate_signals(data["results"], lookback_days=days)
    stats = backtest_stats(validations)
    return {"outcomes": validations, "stats": stats}
