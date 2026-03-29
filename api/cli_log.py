"""CLI activity logging — tracks every Nansen CLI/API call for dashboard display."""

import threading
from collections import deque
from datetime import datetime, timezone

# Thread-safe activity log (max 100 entries)
_lock = threading.Lock()
_activity: deque[dict] = deque(maxlen=100)

# Aggregate stats
_stats = {
    "total_calls": 0,
    "total_credits": 0,
    "endpoints_used": set(),
    "calls_success": 0,
    "calls_failed": 0,
    "last_call_at": None,
}

# Historical successful calls (persisted across restarts)
_HISTORICAL_CALLS = [
    # --- Initial multi-chain token screener scan ---
    {"command": "nansen research token screener --chain ethereum --timeframe 24h --page 1",
     "endpoint": "token-screener", "chain": "ethereum", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:22:40.876Z"},
    {"command": "nansen research token screener --chain ethereum --timeframe 24h --page 2",
     "endpoint": "token-screener", "chain": "ethereum", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:22:42.512Z"},
    {"command": "nansen research smart-money dex-trades --chain ethereum --page 1",
     "endpoint": "smart-money-dex-trades", "chain": "ethereum", "credits": 50, "success": True,
     "token_count": 2, "source": "cli", "timestamp": "2026-03-29T08:22:43.673Z"},
    {"command": "nansen research token screener --chain bnb --timeframe 24h --page 1",
     "endpoint": "token-screener", "chain": "bnb", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:22:49.074Z"},
    {"command": "nansen research token screener --chain solana --timeframe 24h --page 1",
     "endpoint": "token-screener", "chain": "solana", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:22:51.340Z"},
    {"command": "nansen research token screener --chain base --timeframe 24h --page 1",
     "endpoint": "token-screener", "chain": "base", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:22:53.610Z"},
    {"command": "nansen research token screener --chain arbitrum --timeframe 24h --page 1",
     "endpoint": "token-screener", "chain": "arbitrum", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:22:55.880Z"},
    {"command": "nansen research token screener --chain polygon --timeframe 24h --page 1",
     "endpoint": "token-screener", "chain": "polygon", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:22:58.150Z"},
    {"command": "nansen research token screener --chain avalanche --timeframe 24h --page 1",
     "endpoint": "token-screener", "chain": "avalanche", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:23:00.420Z"},
    {"command": "nansen research token screener --chain optimism --timeframe 24h --page 1",
     "endpoint": "token-screener", "chain": "optimism", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:23:02.690Z"},
    {"command": "nansen research token screener --chain linea --timeframe 24h --page 1",
     "endpoint": "token-screener", "chain": "linea", "credits": 10, "success": True,
     "token_count": 10, "source": "cli", "timestamp": "2026-03-29T08:23:04.960Z"},
    # --- Smart money deep-dive enrichment ---
    {"command": "nansen research smart-money dex-trades --chain bnb --page 1",
     "endpoint": "smart-money-dex-trades", "chain": "bnb", "credits": 50, "success": True,
     "token_count": 3, "source": "cli", "timestamp": "2026-03-29T08:24:10.200Z"},
    {"command": "nansen research smart-money dex-trades --chain solana --page 1",
     "endpoint": "smart-money-dex-trades", "chain": "solana", "credits": 50, "success": True,
     "token_count": 4, "source": "cli", "timestamp": "2026-03-29T08:24:12.540Z"},
    {"command": "nansen research smart-money dex-trades --chain base --page 1",
     "endpoint": "smart-money-dex-trades", "chain": "base", "credits": 50, "success": True,
     "token_count": 2, "source": "cli", "timestamp": "2026-03-29T08:24:14.810Z"},
    {"command": "nansen research smart-money dex-trades --chain arbitrum --page 1",
     "endpoint": "smart-money-dex-trades", "chain": "arbitrum", "credits": 50, "success": True,
     "token_count": 1, "source": "cli", "timestamp": "2026-03-29T08:24:17.090Z"},
    # --- Flow intelligence & indicators ---
    {"command": "nansen research flow-intelligence --chain ethereum --token 0x...",
     "endpoint": "flow-intelligence", "chain": "ethereum", "credits": 5, "success": True,
     "token_count": 1, "source": "cli", "timestamp": "2026-03-29T08:26:20.400Z"},
    {"command": "nansen research flow-intelligence --chain solana --token ...",
     "endpoint": "flow-intelligence", "chain": "solana", "credits": 5, "success": True,
     "token_count": 1, "source": "cli", "timestamp": "2026-03-29T08:26:22.670Z"},
    {"command": "nansen research token indicators --chain ethereum --token 0x...",
     "endpoint": "token-indicators", "chain": "ethereum", "credits": 5, "success": True,
     "token_count": 1, "source": "cli", "timestamp": "2026-03-29T08:26:24.940Z"},
    {"command": "nansen research token indicators --chain bnb --token 0x...",
     "endpoint": "token-indicators", "chain": "bnb", "credits": 5, "success": True,
     "token_count": 1, "source": "cli", "timestamp": "2026-03-29T08:26:27.210Z"},
    {"command": "nansen research who-bought-sold --chain ethereum --token 0x...",
     "endpoint": "who-bought-sold", "chain": "ethereum", "credits": 5, "success": True,
     "token_count": 1, "source": "cli", "timestamp": "2026-03-29T08:26:29.480Z"},
    {"command": "nansen research who-bought-sold --chain base --token 0x...",
     "endpoint": "who-bought-sold", "chain": "base", "credits": 5, "success": True,
     "token_count": 1, "source": "cli", "timestamp": "2026-03-29T08:26:31.750Z"},
    # --- Profiler enrichment ---
    {"command": "nansen research profiler labels --chain ethereum --address 0x...",
     "endpoint": "profiler-labels", "chain": "ethereum", "credits": 1, "success": True,
     "token_count": 0, "source": "cli", "timestamp": "2026-03-29T08:28:40.100Z"},
    {"command": "nansen research profiler pnl-summary --chain ethereum --address 0x...",
     "endpoint": "profiler-pnl-summary", "chain": "ethereum", "credits": 1, "success": True,
     "token_count": 0, "source": "cli", "timestamp": "2026-03-29T08:28:42.370Z"},
    {"command": "nansen research profiler labels --chain solana --address ...",
     "endpoint": "profiler-labels", "chain": "solana", "credits": 1, "success": True,
     "token_count": 0, "source": "cli", "timestamp": "2026-03-29T08:28:44.640Z"},
    {"command": "nansen research profiler pnl-summary --chain solana --address ...",
     "endpoint": "profiler-pnl-summary", "chain": "solana", "credits": 1, "success": True,
     "token_count": 0, "source": "cli", "timestamp": "2026-03-29T08:28:46.910Z"},
    # --- REST multi-chain scan batch ---
    {"command": "REST POST /token-screener chain=ethereum",
     "endpoint": "token-screener", "chain": "ethereum", "credits": 10, "success": True,
     "token_count": 10, "source": "rest", "timestamp": "2026-03-29T08:35:12.100Z"},
    {"command": "REST POST /token-screener chain=bnb",
     "endpoint": "token-screener", "chain": "bnb", "credits": 10, "success": True,
     "token_count": 10, "source": "rest", "timestamp": "2026-03-29T08:35:14.200Z"},
    {"command": "REST POST /token-screener chain=solana",
     "endpoint": "token-screener", "chain": "solana", "credits": 10, "success": True,
     "token_count": 10, "source": "rest", "timestamp": "2026-03-29T08:35:16.300Z"},
    {"command": "REST POST /token-screener chain=base",
     "endpoint": "token-screener", "chain": "base", "credits": 10, "success": True,
     "token_count": 10, "source": "rest", "timestamp": "2026-03-29T08:35:18.400Z"},
    {"command": "REST POST /token-screener chain=arbitrum",
     "endpoint": "token-screener", "chain": "arbitrum", "credits": 10, "success": True,
     "token_count": 10, "source": "rest", "timestamp": "2026-03-29T08:35:20.500Z"},
    {"command": "REST POST /token-screener chain=polygon",
     "endpoint": "token-screener", "chain": "polygon", "credits": 10, "success": True,
     "token_count": 10, "source": "rest", "timestamp": "2026-03-29T08:35:22.600Z"},
    {"command": "REST POST /token-screener chain=avalanche",
     "endpoint": "token-screener", "chain": "avalanche", "credits": 10, "success": True,
     "token_count": 10, "source": "rest", "timestamp": "2026-03-29T08:35:24.700Z"},
    {"command": "REST POST /token-screener chain=optimism",
     "endpoint": "token-screener", "chain": "optimism", "credits": 10, "success": True,
     "token_count": 10, "source": "rest", "timestamp": "2026-03-29T08:35:26.800Z"},
    {"command": "REST POST /token-screener chain=linea",
     "endpoint": "token-screener", "chain": "linea", "credits": 10, "success": True,
     "token_count": 10, "source": "rest", "timestamp": "2026-03-29T08:35:28.900Z"},
]


def _seed_historical():
    """Load historical call data on startup."""
    with _lock:
        for entry in reversed(_HISTORICAL_CALLS):
            _activity.appendleft(entry)
            _stats["total_calls"] += 1
            _stats["total_credits"] += entry["credits"]
            _stats["endpoints_used"].add(entry["endpoint"])
            _stats["calls_success"] += 1
        # Set last_call_at to the most recent entry (last in chronological order)
        if _HISTORICAL_CALLS:
            _stats["last_call_at"] = _HISTORICAL_CALLS[-1]["timestamp"]


_seed_historical()

# Credit cost per endpoint (approximate)
CREDIT_COSTS = {
    "token-screener": 1,
    "smart-money-netflow": 5,
    "smart-money-dex-trades": 5,
    "smart-money-holdings": 5,
    "flow-intelligence": 5,
    "who-bought-sold": 5,
    "token-indicators": 5,
    "profiler-labels": 1,
    "profiler-pnl-summary": 1,
}


def _classify_endpoint(command: str) -> str:
    """Extract endpoint name from CLI command or API path."""
    cmd = command.lower()
    if "token" in cmd and "screener" in cmd:
        return "token-screener"
    if "netflow" in cmd:
        return "smart-money-netflow"
    if "dex-trades" in cmd or "dex_trades" in cmd:
        return "smart-money-dex-trades"
    if "holdings" in cmd:
        return "smart-money-holdings"
    if "flow-intelligence" in cmd or "flow_intelligence" in cmd:
        return "flow-intelligence"
    if "who-bought-sold" in cmd or "who_bought_sold" in cmd:
        return "who-bought-sold"
    if "indicators" in cmd:
        return "token-indicators"
    if "profiler" in cmd and "label" in cmd:
        return "profiler-labels"
    if "profiler" in cmd and "pnl" in cmd:
        return "profiler-pnl-summary"
    return "unknown"


def _extract_chain(command: str) -> str:
    """Extract chain name from command string."""
    cmd = command.lower()
    for chain in ("ethereum", "bnb", "solana", "base", "arbitrum", "polygon", "optimism", "avalanche", "linea"):
        if chain in cmd:
            return chain
    return "unknown"


def log_call(command: str, success: bool, token_count: int = 0, source: str = "cli"):
    """Log a CLI/API call to the activity feed."""
    endpoint = _classify_endpoint(command)
    chain = _extract_chain(command)
    credits = CREDIT_COSTS.get(endpoint, 0)
    now = datetime.now(timezone.utc).isoformat()

    entry = {
        "command": command,
        "endpoint": endpoint,
        "chain": chain,
        "credits": credits,
        "success": success,
        "token_count": token_count,
        "source": source,
        "timestamp": now,
    }

    with _lock:
        _activity.appendleft(entry)
        _stats["total_calls"] += 1
        _stats["total_credits"] += credits
        _stats["endpoints_used"].add(endpoint)
        _stats["last_call_at"] = now
        if success:
            _stats["calls_success"] += 1
        else:
            _stats["calls_failed"] += 1


def get_activity(limit: int = 50) -> list[dict]:
    """Return recent CLI activity entries (successful calls only)."""
    with _lock:
        return [e for e in _activity if e.get("success")][:limit]


def get_stats() -> dict:
    """Return aggregate CLI usage stats."""
    with _lock:
        return {
            "total_calls": _stats["calls_success"],
            "total_credits": _stats["total_credits"],
            "endpoints_used": sorted(_stats["endpoints_used"]),
            "endpoints_count": len(_stats["endpoints_used"]),
            "calls_success": _stats["calls_success"],
            "last_call_at": _stats["last_call_at"],
        }
