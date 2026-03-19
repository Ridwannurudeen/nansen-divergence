"""Telegram alert notifications for divergence signals."""

import json
import os
import urllib.error
import urllib.request


def _get_config() -> tuple[str, str] | None:
    """Get Telegram bot token and chat ID from environment variables.

    Returns (bot_token, chat_id) or None if not configured.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if token and chat_id:
        return token, chat_id
    return None


def _send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """Send a message via Telegram Bot API.

    Returns True on success, False on failure.
    """
    config = _get_config()
    if not config:
        return False

    token, chat_id = config
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return False


def _format_alert(token: dict) -> str:
    """Format a single token divergence alert for Telegram."""
    symbol = token.get("token_symbol", "???")
    chain = token.get("chain", "")
    phase = token.get("phase", "")
    strength = token.get("divergence_strength", 0)
    confidence = token.get("confidence", "LOW")

    sm_flow = token.get("sm_net_flow", 0)
    mkt_flow = token.get("market_netflow", 0)
    display_flow = sm_flow if sm_flow != 0 else mkt_flow

    price_chg = token.get("price_change", 0)
    price_pct = price_chg * 100
    narrative = token.get("narrative", "")

    flow_sign = "+" if display_flow > 0 else ""
    price_sign = "+" if price_pct > 0 else ""

    lines = [
        f"*{phase}* | `{symbol}` ({chain})",
        f"Strength: {strength:.2f} | Confidence: {confidence}",
        f"Flow: {flow_sign}${abs(display_flow):,.0f} | Price: {price_sign}{price_pct:.1f}%",
    ]
    if narrative:
        lines.append(f"_{narrative}_")

    return "\n".join(lines)


def send_divergence_alerts(results: list[dict]) -> int:
    """Send alerts for HIGH/MEDIUM divergent tokens.

    Returns the number of alerts sent. Capped at 5 to avoid spam.
    """
    divergent = [
        r for r in results
        if r.get("phase") in ("ACCUMULATION", "DISTRIBUTION")
        and r.get("confidence") in ("HIGH", "MEDIUM")
    ]

    if not divergent:
        return 0

    sent = 0
    for token in divergent[:5]:
        text = _format_alert(token)
        if _send_message(text):
            sent += 1

    return sent


def send_scan_summary(summary: dict, chains: list[str]) -> bool:
    """Send a scan summary message to Telegram."""
    chain_str = ", ".join(c.upper() for c in chains)
    total = summary.get("total_tokens", 0)
    div_count = summary.get("divergence_signals", 0)
    high = summary.get("confidence_high", 0)
    med = summary.get("confidence_medium", 0)

    text = (
        f"*Nansen Divergence Scan*\n"
        f"Chains: {chain_str}\n"
        f"Tokens: {total} | Divergence: {div_count}\n"
        f"Confidence: {high} HIGH, {med} MED"
    )

    return _send_message(text)
