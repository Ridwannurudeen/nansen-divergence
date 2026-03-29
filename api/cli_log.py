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
    for chain in ("ethereum", "bnb", "solana", "base", "arbitrum", "polygon", "optimism", "avalanche"):
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
