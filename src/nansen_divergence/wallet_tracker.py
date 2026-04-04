"""Wallet enrichment via block explorer free APIs — no credits needed.

Uses Etherscan-compatible APIs (same structure across ETH/BNB/Base/Arbitrum/Polygon/Avalanche)
to fetch recent token buyers and build a performance database over time.
"""
import json
import logging
import time
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger("nansen.wallet_tracker")

_CHAIN_APIS = {
    "ethereum": "https://api.etherscan.io/api",
    "bnb": "https://api.bscscan.com/api",
    "base": "https://api.basescan.org/api",
    "arbitrum": "https://api.arbiscan.io/api",
    "polygon": "https://api.polygonscan.com/api",
    "avalanche": "https://api.snowtrace.io/api",
}

_RATE_LIMIT_SEC = 0.25  # 4 req/sec per chain (free tier allows 5)


def build_tokentx_url(chain: str, token_address: str, limit: int = 50) -> str:
    """Build Etherscan-compatible token transfer query URL."""
    base = _CHAIN_APIS.get(chain.lower(), _CHAIN_APIS["ethereum"])
    return (
        f"{base}?module=account&action=tokentx"
        f"&contractaddress={token_address}"
        f"&sort=desc&offset={limit}&page=1"
    )


def fetch_recent_buyers(chain: str, token_address: str) -> list[dict]:
    """Fetch recent large buyers of a token. Returns list of wallet dicts.

    Uses Etherscan tokentx API — free, no key required for basic queries.
    Deduplicates by address, keeping largest transaction per wallet.
    """
    url = build_tokentx_url(chain, token_address)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "nansen-divergence/6.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())

        if data.get("status") != "1":
            return []

        buyers: dict[str, dict] = {}
        for tx in data.get("result", []):
            to_addr = tx.get("to", "").lower()
            if not to_addr:
                continue
            value = int(tx.get("value", 0))
            decimals = int(tx.get("tokenDecimal", 18))
            token_amount = value / (10 ** decimals) if decimals >= 0 else 0
            if token_amount < 1:
                continue
            # Keep entry for this wallet if it's the largest buy seen
            existing = buyers.get(to_addr)
            if existing is None or token_amount > existing["token_amount"]:
                buyers[to_addr] = {
                    "address": to_addr,
                    "chain": chain,
                    "token_address": token_address.lower(),
                    "token_amount": token_amount,
                    "tx_hash": tx.get("hash", ""),
                    "block_time": tx.get("timeStamp", ""),
                }

        time.sleep(_RATE_LIMIT_SEC)
        return list(buyers.values())[:20]

    except Exception as e:
        logger.debug(f"fetch_recent_buyers failed {chain}:{token_address}: {e}")
        return []


def score_wallet(trades: list[dict]) -> dict:
    """Compute performance score for a wallet from historical trade outcomes.

    Each trade dict must have: bought_at (float), price_72h (float).
    Returns: win_rate, avg_return, trade_count, label, score (0-100).
    """
    if not trades:
        return {
            "win_rate": 0.0, "avg_return": 0.0,
            "trade_count": 0, "label": "Unknown", "score": 0.0,
        }

    wins = [t for t in trades if t.get("price_72h", 0) > t.get("bought_at", 0)]
    win_rate = len(wins) / len(trades)

    returns = []
    for t in trades:
        p72 = t.get("price_72h")
        bought = t.get("bought_at")
        if p72 and bought and bought > 0:
            returns.append(((p72 - bought) / bought) * 100)
    avg_return = sum(returns) / len(returns) if returns else 0.0

    # Behavioural label
    n = len(trades)
    if win_rate >= 0.7 and n >= 5:
        label = "Accumulator"
    elif win_rate >= 0.6 and n >= 3:
        label = "Early Mover"
    elif avg_return > 20 and n >= 2:
        label = "Whale"
    elif n >= 1:
        label = "Trader"
    else:
        label = "Unknown"

    # Composite score 0-100
    score = min(100.0,
        win_rate * 60
        + min(avg_return, 50) / 50 * 30
        + min(n, 10) / 10 * 10
    )

    return {
        "win_rate": round(win_rate, 3),
        "avg_return": round(avg_return, 2),
        "trade_count": n,
        "label": label,
        "score": round(score, 1),
    }


def get_wallet_profile(address: str, chain: str, db_path: str | None = None) -> dict | None:
    """Look up a wallet's stored performance profile from the DB."""
    from .history import DB_PATH, init_db
    conn = init_db(db_path=db_path or DB_PATH)
    row = conn.execute(
        "SELECT * FROM wallet_scores WHERE address=? AND chain=?",
        (address.lower(), chain)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def enrich_token_with_wallets(
    chain: str, token_address: str, db_path: str | None = None
) -> list[dict]:
    """Fetch recent buyers and return their profiles (from DB if available, else New)."""
    if chain.lower() not in _CHAIN_APIS:
        return []

    buyers = fetch_recent_buyers(chain, token_address)
    if not buyers:
        return []

    from .history import DB_PATH, init_db
    conn = init_db(db_path=db_path or DB_PATH)
    result = []

    for buyer in buyers[:10]:
        addr = buyer["address"]
        row = conn.execute(
            "SELECT win_rate, avg_return, trade_count, score FROM wallet_scores WHERE address=? AND chain=?",
            (addr, chain)
        ).fetchone()
        entry = {"address": addr, "chain": chain}
        if row:
            entry.update({
                "win_rate": row["win_rate"],
                "avg_return": row["avg_return"],
                "trade_count": row["trade_count"],
                "score": row["score"],
                "label": (
                    "Accumulator" if (row["win_rate"] or 0) >= 0.7 and (row["trade_count"] or 0) >= 5
                    else "Early Mover" if (row["win_rate"] or 0) >= 0.6 and (row["trade_count"] or 0) >= 3
                    else "Trader"
                ),
            })
        else:
            entry.update({"win_rate": None, "avg_return": None, "trade_count": 0, "score": None, "label": "New"})
        result.append(entry)

    conn.close()
    return result
