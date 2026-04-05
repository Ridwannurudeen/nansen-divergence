"""API v1 — signals endpoints."""
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get("/signals")
def get_signals(
    chain: str | None = None,
    phase: str | None = None,
    resolved_only: bool = False,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    from nansen_divergence.history import DB_PATH, init_db

    conn = init_db(db_path=DB_PATH)
    where_parts: list[str] = []
    params: list = []

    if chain:
        where_parts.append("chain = ?")
        params.append(chain)
    if phase:
        where_parts.append("phase = ?")
        params.append(phase.upper())
    if resolved_only:
        where_parts.append("outcome_correct IS NOT NULL")

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    rows = conn.execute(
        f"""SELECT id, scan_timestamp, chain, token_address, token_symbol,
                   phase, confidence, divergence_strength,
                   price_at_emission, price_24h, price_72h, price_7d,
                   return_24h, return_72h, return_7d, outcome_correct, narrative
            FROM signals {where}
            ORDER BY scan_timestamp DESC
            LIMIT ? OFFSET ?""",
        [*params, limit, offset],
    ).fetchall()

    total = conn.execute(f"SELECT COUNT(*) FROM signals {where}", params).fetchone()[0]
    conn.close()

    return {
        "signals": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/signals/{signal_id}")
def get_signal(signal_id: int):
    from nansen_divergence.history import DB_PATH, init_db

    conn = init_db(db_path=DB_PATH)
    row = conn.execute("SELECT * FROM signals WHERE id=?", (signal_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")
    return dict(row)
