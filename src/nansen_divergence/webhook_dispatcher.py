"""Webhook dispatcher — fires HMAC-signed payloads to registered URLs."""
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger("nansen.webhooks")


def sign_payload(secret: str, payload: bytes) -> str:
    """Return HMAC-SHA256 signature string."""
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _post_webhook(url: str, secret: str, signal: dict) -> bool:
    """POST signal payload to webhook URL. Returns True on HTTP 2xx."""
    payload = json.dumps(signal).encode()
    sig = sign_payload(secret, payload)
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Nansen-Signature": sig,
            "User-Agent": "nansen-divergence/6.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status < 400
    except Exception as e:
        logger.warning(f"Webhook delivery failed to {url}: {e}")
        return False


def dispatch_signal(signal: dict, db_path: str | None = None) -> int:
    """Fire signal to all matching registered webhooks. Returns count delivered."""
    from .history import DB_PATH, init_db

    conn = init_db(db_path=db_path or DB_PATH)
    webhooks = conn.execute("SELECT id, url, secret, filters FROM webhooks").fetchall()
    fired = 0
    now = datetime.now(timezone.utc).isoformat()

    for wh in webhooks:
        try:
            filters = json.loads(wh["filters"] or "{}")
        except Exception:
            filters = {}

        if filters.get("chain") and signal.get("chain") != filters["chain"]:
            continue
        if filters.get("phase") and signal.get("phase") != filters["phase"]:
            continue
        if filters.get("min_strength") and signal.get("strength", 0) < filters["min_strength"]:
            continue

        success = _post_webhook(wh["url"], wh["secret"], signal)
        if success:
            conn.execute(
                "UPDATE webhooks SET last_fired=?, fire_count=fire_count+1 WHERE id=?",
                (now, wh["id"])
            )
            fired += 1

    conn.commit()
    conn.close()
    return fired


def dispatch_scan_signals(results: list[dict], db_path: str | None = None) -> int:
    """Dispatch all divergent signals from a scan result to webhooks."""
    from .history import get_performance_stats

    stats = get_performance_stats(db_path=db_path)
    win_rate = stats.get("win_rate", 0.0)
    now = datetime.now(timezone.utc)

    divergent = [r for r in results if r.get("phase") in ("ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN")]
    total = 0
    for r in divergent:
        signal = {
            "signal_id": f"{r.get('chain', '')}-{(r.get('token_address') or '')[:8]}-{now.strftime('%Y%m%d%H%M')}",
            "emitted_at": now.isoformat(),
            "token": {
                "symbol": r.get("token_symbol", ""),
                "chain": r.get("chain", ""),
                "address": r.get("token_address", ""),
            },
            "phase": r.get("phase", ""),
            "strength": int((r.get("divergence_strength") or 0) * 100),
            "price_usd": r.get("price_usd"),
            "divergence_score": r.get("divergence_strength"),
            "narrative": r.get("narrative", ""),
            "historical_win_rate": win_rate,
        }
        total += dispatch_signal(signal, db_path=db_path)
    return total
