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


@app.get("/api/token/{chain}/{address}")
def token_deep_dive(chain: str, address: str):
    """Deep-dive using server-side Nansen API key (no client key needed)."""
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


@app.get("/api/history/outcomes")
def history_outcomes(days: int = 30):
    """Individual signal validations with price outcomes + aggregate stats."""
    data = get_latest_scan()
    if not data or not data.get("results"):
        return {"outcomes": [], "stats": {"total_signals": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "avg_return": 0.0, "best_return": 0.0, "worst_return": 0.0}}
    from nansen_divergence.history import validate_signals, backtest_stats
    validations = validate_signals(data["results"], lookback_days=days)
    stats = backtest_stats(validations)
    return {"outcomes": validations, "stats": stats}
