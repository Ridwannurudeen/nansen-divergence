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
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_chain_token_time
        ON signals (chain, token_address, scan_timestamp)
    """)

    # Outcome columns — added safely so existing DBs are migrated without error.
    _outcome_columns = [
        ("price_at_emission", "REAL"),
        ("price_24h", "REAL"),
        ("price_72h", "REAL"),
        ("price_7d", "REAL"),
        ("return_24h", "REAL"),
        ("return_72h", "REAL"),
        ("return_7d", "REAL"),
        ("outcome_correct", "INTEGER"),
    ]
    for col_name, col_type in _outcome_columns:
        try:
            conn.execute(f"ALTER TABLE signals ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            # Column already exists — safe to ignore.
            pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS wallet_scores (
            address      TEXT NOT NULL,
            chain        TEXT NOT NULL,
            win_rate     REAL DEFAULT 0.0,
            avg_return   REAL DEFAULT 0.0,
            trade_count  INTEGER DEFAULT 0,
            last_updated TEXT,
            score        REAL DEFAULT 0.0,
            PRIMARY KEY (address, chain)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS webhooks (
            id          TEXT PRIMARY KEY,
            url         TEXT NOT NULL,
            secret      TEXT NOT NULL,
            filters     TEXT DEFAULT '{}',
            created_at  TEXT NOT NULL,
            last_fired  TEXT,
            fire_count  INTEGER DEFAULT 0
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
        (now, ",".join(chains), timeframe, len(results), len(divergent)),
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

    # Get past divergent signals (HIGH/MEDIUM confidence only)
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

        # Skip unresolved signals — price hasn't moved enough to judge
        if abs(pct_change) < 1.0:
            continue

        scan_time = datetime.fromisoformat(row["scan_timestamp"].replace("Z", "+00:00"))
        if scan_time.tzinfo is None:
            scan_time = scan_time.replace(tzinfo=timezone.utc)
        days_ago = (now - scan_time).days

        validations.append(
            {
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
            }
        )

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


def backtest_stats(validations: list[dict]) -> dict:
    """Compute win/loss stats from signal validations.

    A 'win' is defined as:
    - ACCUMULATION signal where price went UP (positive change)
    - DISTRIBUTION signal where price went DOWN (negative change)
    """
    if not validations:
        return {
            "total_signals": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "best_return": 0.0,
            "worst_return": 0.0,
        }

    wins = 0
    returns = []

    for v in validations:
        pct = v.get("price_change_pct", 0)
        # Cap extreme outliers from micro-cap tokens (winsorize at ±500%)
        pct = max(-500, min(500, pct))
        phase = v.get("phase", "")
        returns.append(pct)

        if phase == "ACCUMULATION" and pct > 0:
            wins += 1
        elif phase == "DISTRIBUTION" and pct < 0:
            wins += 1

    total = len(validations)
    return {
        "total_signals": total,
        "wins": wins,
        "losses": total - wins,
        "win_rate": round(wins / total * 100, 1) if total else 0.0,
        "avg_return": round(sum(returns) / total, 1) if total else 0.0,
        "best_return": round(max(returns), 1) if returns else 0.0,
        "worst_return": round(min(returns), 1) if returns else 0.0,
    }


def get_token_history(
    chain: str,
    token_address: str,
    days: int = 30,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    """Return time-series of divergence_strength, phase, price, confidence for a token."""
    own_conn = conn is None
    if own_conn:
        conn = init_db()

    rows = conn.execute(
        """SELECT scan_timestamp, divergence_strength, phase, confidence,
                  price_usd, price_change, sm_net_flow
           FROM signals
           WHERE chain = ? AND LOWER(token_address) = LOWER(?)
             AND scan_timestamp >= datetime('now', ?)
           ORDER BY scan_timestamp ASC""",
        (chain, token_address, f"-{days} days"),
    ).fetchall()

    if own_conn:
        conn.close()

    return [dict(r) for r in rows]


def get_sparkline_data(
    days: int = 7,
    points: int = 10,
    conn: sqlite3.Connection | None = None,
) -> dict[str, list[float]]:
    """Return {token_address_lower: [strength1, strength2, ...]} for sparkline mini-charts.

    Returns the last `points` divergence_strength values per token within the window.
    """
    own_conn = conn is None
    if own_conn:
        conn = init_db()

    rows = conn.execute(
        """SELECT LOWER(token_address) as addr, divergence_strength, scan_timestamp
           FROM signals
           WHERE scan_timestamp >= datetime('now', ?)
           ORDER BY scan_timestamp ASC""",
        (f"-{days} days",),
    ).fetchall()

    if own_conn:
        conn.close()

    # Collect all points per token, then keep last N
    all_points: dict[str, list[float]] = {}
    for r in rows:
        addr = r["addr"]
        if addr not in all_points:
            all_points[addr] = []
        all_points[addr].append(r["divergence_strength"])

    return {addr: vals[-points:] for addr, vals in all_points.items()}


def get_signal_streaks(
    days: int = 14,
    conn: sqlite3.Connection | None = None,
) -> dict[str, dict]:
    """Return {addr: {phase, streak, since}} for tokens with consecutive same-phase scans.

    Only reports streaks >= 2.
    """
    own_conn = conn is None
    if own_conn:
        conn = init_db()

    rows = conn.execute(
        """SELECT LOWER(token_address) as addr, phase, scan_timestamp
           FROM signals
           WHERE scan_timestamp >= datetime('now', ?)
           ORDER BY scan_timestamp DESC""",
        (f"-{days} days",),
    ).fetchall()

    if own_conn:
        conn.close()

    # Track consecutive same-phase scans per token (most recent first)
    token_scans: dict[str, list[dict]] = {}
    for r in rows:
        addr = r["addr"]
        if addr not in token_scans:
            token_scans[addr] = []
        token_scans[addr].append({"phase": r["phase"], "ts": r["scan_timestamp"]})

    streaks: dict[str, dict] = {}
    for addr, scans in token_scans.items():
        if len(scans) < 2:
            continue
        phase = scans[0]["phase"]
        streak = 1
        since = scans[0]["ts"]
        for s in scans[1:]:
            if s["phase"] == phase:
                streak += 1
                since = s["ts"]
            else:
                break
        if streak >= 2:
            streaks[addr] = {"phase": phase, "streak": streak, "since": since}

    return streaks
