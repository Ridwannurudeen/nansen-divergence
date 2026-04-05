"""MCP tool handlers — callable by AI agents via MCP protocol."""
import logging

logger = logging.getLogger("nansen.mcp_tools")

# Tool definitions for MCP protocol registration
TOOL_DEFINITIONS = [
    {
        "name": "get_divergence_signals",
        "description": "Get current price/volume divergence signals across chains. Returns tokens where price and volume are moving in opposite directions, classified by Wyckoff phase.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Filter by chain (ethereum, bnb, base, arbitrum, polygon, solana)"},
                "phase": {"type": "string", "description": "Filter by Wyckoff phase: ACCUMULATION, DISTRIBUTION, MARKUP, MARKDOWN"},
                "min_strength": {"type": "integer", "description": "Minimum signal strength 0-100", "default": 0},
                "limit": {"type": "integer", "description": "Max results (1-50)", "default": 10},
            },
        },
    },
    {
        "name": "get_signal_performance",
        "description": "Get historical signal performance stats — win rate, avg return, profit factor.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Look back N days (omit for all-time stats)"},
            },
        },
    },
]


def handle_get_divergence_signals(args: dict) -> list:
    """Return current divergence signals, optionally filtered."""
    from .history import DB_PATH, init_db

    chain = args.get("chain")
    phase = (args.get("phase") or "").upper() or None
    min_strength = float(args.get("min_strength", 0)) / 100.0
    limit = min(int(args.get("limit", 10)), 50)

    conn = init_db(db_path=DB_PATH)
    where_parts = ["1=1"]
    params: list = []

    if chain:
        where_parts.append("chain=?")
        params.append(chain)
    if phase:
        where_parts.append("phase=?")
        params.append(phase)
    if min_strength > 0:
        where_parts.append("divergence_strength >= ?")
        params.append(min_strength)

    where = " AND ".join(where_parts)
    rows = conn.execute(
        f"""SELECT chain, token_symbol, token_address, phase, confidence,
                   divergence_strength, price_usd, narrative, scan_timestamp
            FROM signals
            WHERE {where}
            ORDER BY scan_timestamp DESC, divergence_strength DESC
            LIMIT ?""",
        [*params, limit],
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def handle_get_signal_performance(args: dict) -> dict:
    """Return historical signal performance statistics."""
    from .history import get_performance_stats
    return get_performance_stats(days=args.get("days"))
