"""Signal history storage and validation using SQLite."""

import os
import sqlite3
from datetime import datetime, timezone

DB_DIR = os.path.join(os.path.expanduser("~"), ".nansen-divergence")
DB_PATH = os.path.join(DB_DIR, "history.db")


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    """Create the database directory and tables if they don't exist.

    Returns a connection to the database.
    """
    path = db_path or DB_PATH
    db_dir = os.path.dirname(path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            chains TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            token_count INTEGER NOT NULL,
            divergence_count INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            scan_timestamp TEXT NOT NULL,
            chain TEXT NOT NULL,
            token_address TEXT NOT NULL,
            token_symbol TEXT NOT NULL,
            price_usd REAL,
            price_change REAL,
            market_cap REAL,
            sm_net_flow REAL,
            divergence_strength REAL,
            phase TEXT NOT NULL,
            confidence TEXT NOT NULL,
            narrative TEXT,
            has_sm_data INTEGER,
            FOREIGN KEY (scan_id) REFERENCES scans(id)
        )
    """)
    conn.commit()
    return conn


def save_scan(
    results: list[dict],
    chains: list[str],
    timeframe: str,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Save a scan and its signals to the database. Returns the scan_id."""
    own_conn = conn is None
    if own_conn:
        conn = init_db()

    now = datetime.now(timezone.utc).isoformat()
    divergent = [r for r in results if r.get("phase") in ("ACCUMULATION", "DISTRIBUTION")]

    cursor = conn.execute(
        "INSERT INTO scans (timestamp, chains, timeframe, token_count, divergence_count) VALUES (?, ?, ?, ?, ?)",
        (",".join(chains), now, timeframe, len(results), len(divergent)),
    )
    scan_id = cursor.lastrowid

    for r in results:
        conn.execute(
            """INSERT INTO signals
            (scan_id, scan_timestamp, chain, token_address, token_symbol, price_usd,
             price_change, market_cap, sm_net_flow, divergence_strength, phase,
             confidence, narrative, has_sm_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                scan_id,
                now,
                r.get("chain", ""),
                r.get("token_address", ""),
                r.get("token_symbol", ""),
                r.get("price_usd", 0),
                r.get("price_change", 0),
                r.get("market_cap", 0),
                r.get("sm_net_flow", 0),
                r.get("divergence_strength", 0),
                r.get("phase", "MARKUP"),
                r.get("confidence", "LOW"),
                r.get("narrative", ""),
                1 if r.get("has_sm_data") else 0,
            ),
        )

    conn.commit()
    if own_conn:
        conn.close()

    return scan_id


def validate_signals(
    current_results: list[dict],
    lookback_days: int = 7,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    """Compare past ACCUMULATION/DISTRIBUTION signals (HIGH/MED) against current prices.

    Uses zero extra API calls — just compares stored signal prices to current scan results.

    Returns list of dicts with signal_price, current_price, price_change_pct, days_ago, etc.
    """
    own_conn = conn is None
    if own_conn:
        conn = init_db()

    # Build lookup from current results: {token_address_lower: token_data}
    current_lookup: dict[str, dict] = {}
    for r in current_results:
        addr = r.get("token_address", "").lower()
        if addr:
            current_lookup[addr] = r

    # Get past divergent signals
    now = datetime.now(timezone.utc)
    rows = conn.execute(
        """SELECT * FROM signals
        WHERE phase IN ('ACCUMULATION', 'DISTRIBUTION')
        AND confidence IN ('HIGH', 'MEDIUM')
        AND scan_timestamp >= datetime('now', ?)
        ORDER BY scan_timestamp DESC""",
        (f"-{lookback_days} days",),
    ).fetchall()

    if own_conn:
        conn.close()

    # Deduplicate by token_address (keep most recent)
    seen: set[str] = set()
    validations = []

    for row in rows:
        addr = row["token_address"].lower()
        if addr in seen:
            continue
        seen.add(addr)

        current = current_lookup.get(addr)
        if not current:
            continue

        signal_price = row["price_usd"] or 0
        current_price = current.get("price_usd", 0)

        if signal_price <= 0:
            continue

        pct_change = (current_price - signal_price) / signal_price * 100

        scan_time = datetime.fromisoformat(row["scan_timestamp"].replace("Z", "+00:00"))
        if scan_time.tzinfo is None:
            scan_time = scan_time.replace(tzinfo=timezone.utc)
        days_ago = (now - scan_time).days

        validations.append({
            "token_address": row["token_address"],
            "token_symbol": row["token_symbol"],
            "chain": row["chain"],
            "phase": row["phase"],
            "confidence": row["confidence"],
            "signal_price": signal_price,
            "current_price": current_price,
            "price_change_pct": round(pct_change, 1),
            "days_ago": max(days_ago, 0),
            "divergence_strength": row["divergence_strength"],
        })

    return validations


def get_recent_signals(
    days: int = 7,
    phase: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    """Get recent signals from the database."""
    own_conn = conn is None
    if own_conn:
        conn = init_db()

    query = "SELECT * FROM signals WHERE scan_timestamp >= datetime('now', ?)"
    params: list = [f"-{days} days"]

    if phase:
        query += " AND phase = ?"
        params.append(phase)

    query += " ORDER BY scan_timestamp DESC"
    rows = conn.execute(query, params).fetchall()

    if own_conn:
        conn.close()

    return [dict(r) for r in rows]


def get_scan_history(
    limit: int = 20,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    """Get recent scan history."""
    own_conn = conn is None
    if own_conn:
        conn = init_db()

    rows = conn.execute(
        "SELECT * FROM scans ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()

    if own_conn:
        conn.close()

    return [dict(r) for r in rows]


def detect_new_tokens(
    current_results: list[dict],
    conn: sqlite3.Connection | None = None,
) -> set[str]:
    """Return set of token addresses (lowercased) that have never been seen before in history."""
    own_conn = conn is None
    if own_conn:
        conn = init_db()

    rows = conn.execute("SELECT DISTINCT LOWER(token_address) as addr FROM signals").fetchall()
    known = {r["addr"] for r in rows}

    if own_conn:
        conn.close()

    current_addrs = {r.get("token_address", "").lower() for r in current_results if r.get("token_address")}
    return current_addrs - known


def clear_history(conn: sqlite3.Connection | None = None):
    """Delete all history data."""
    own_conn = conn is None
    if own_conn:
        conn = init_db()

    conn.execute("DELETE FROM signals")
    conn.execute("DELETE FROM scans")
    conn.commit()

    if own_conn:
        conn.close()
