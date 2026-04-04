"""Hourly job: fill outcome columns (price_24h/72h/7d) for resolved signals."""

import logging
import re
import sqlite3
from datetime import datetime, timezone, timedelta

from .history import DB_PATH, init_db

logger = logging.getLogger("nansen.outcome_tracker")

OUTCOME_WINDOWS = {"price_24h": 24, "price_72h": 72, "price_7d": 168}


def fetch_price(chain: str, token_address: str) -> float | None:
    """Fetch current price via MCP general_search (0 credits). Returns price_usd or None."""
    try:
        from .mcp_search import _mcp_search
        result = _mcp_search(f"{chain} {token_address}")
        match = re.search(r'"price_usd"\s*:\s*([\d.]+)', result)
        if match:
            return float(match.group(1))
        match = re.search(r'\$?([\d,]+\.[\d]{2,})', result)
        if match:
            return float(match.group(1).replace(",", ""))
    except Exception as e:
        logger.debug(f"fetch_price failed for {chain}:{token_address}: {e}")
    return None


def fill_outcomes(conn: sqlite3.Connection | None = None, db_path: str | None = None) -> int:
    """Fill unresolved outcome columns for signals past their window. Returns count filled."""
    own_conn = conn is None
    if own_conn:
        conn = init_db(db_path=db_path or DB_PATH)

    now = datetime.now(timezone.utc)
    filled = 0

    for col, hours in OUTCOME_WINDOWS.items():
        cutoff = (now - timedelta(hours=hours)).isoformat()
        rows = conn.execute(
            f"""SELECT id, chain, token_address, phase, price_at_emission, scan_timestamp
                FROM signals
                WHERE {col} IS NULL
                AND price_at_emission IS NOT NULL
                AND scan_timestamp < ?
                LIMIT 50""",
            (cutoff,)
        ).fetchall()

        for row in rows:
            price = fetch_price(row["chain"], row["token_address"])
            if price is None:
                continue

            emission = row["price_at_emission"]
            return_pct = ((price - emission) / emission) * 100 if emission and emission > 0 else None

            outcome = None
            if return_pct is not None and col == "price_72h":
                phase = row["phase"]
                if phase in ("ACCUMULATION", "MARKUP"):
                    outcome = 1 if return_pct > 0 else 0
                elif phase in ("DISTRIBUTION", "MARKDOWN"):
                    outcome = 1 if return_pct < 0 else 0

            return_col = col.replace("price_", "return_")
            update_sql = f"UPDATE signals SET {col}=?, {return_col}=?"
            params: list = [price, return_pct]

            if outcome is not None:
                update_sql += ", outcome_correct=?"
                params.append(outcome)

            params.append(row["id"])
            conn.execute(update_sql + " WHERE id=?", params)
            filled += 1

    conn.commit()
    if own_conn:
        conn.close()

    logger.info(f"Outcome tracker: filled {filled} outcomes")
    return filled
