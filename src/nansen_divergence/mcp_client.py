"""Nansen MCP API client.

Talks to https://mcp.nansen.ai/ra/mcp/ using JSON-RPC over SSE.
Returns data in the same dict format the scanner expects so it can
be used as a drop-in replacement for REST / CLI data sources.
"""

import json
import os
import re
import urllib.error
import urllib.request

_MCP_URL = "https://mcp.nansen.ai/ra/mcp/"


class _PostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow 307/308 redirects while preserving the POST method and body."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if code in (307, 308):
            new_req = urllib.request.Request(
                newurl,
                data=req.data,
                headers=dict(req.headers),
                method=req.get_method(),
            )
            return new_req
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_PostRedirectHandler)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def _get_mcp_key() -> str | None:
    """Return the Nansen MCP API key from env, or None."""
    return os.environ.get("NANSEN_MCP_KEY", "").strip() or None


# ---------------------------------------------------------------------------
# Low-level transport
# ---------------------------------------------------------------------------


def _mcp_call(tool_name: str, arguments: dict) -> str:
    """POST a JSON-RPC ``tools/call`` request and return the text content.

    The Nansen MCP endpoint responds with Server-Sent Events (SSE).  We parse
    the ``event: message`` / ``data: {json}`` pairs and extract the text from
    ``result.content[0].text``.

    Raises ``RuntimeError`` on auth or transport errors.
    """
    key = _get_mcp_key()
    if not key:
        raise RuntimeError("NANSEN_MCP_KEY not set")

    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
    ).encode()

    req = urllib.request.Request(
        _MCP_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "NANSEN-API-KEY": key,
            "Accept": "application/json, text/event-stream",
            "User-Agent": "nansen-divergence/5.0",
        },
        method="POST",
    )

    try:
        with _opener.open(req, timeout=90) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode(errors="replace") if exc.fp else ""
        raise RuntimeError(f"MCP API error {exc.code}: {err_body}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"MCP API request failed: {exc}") from exc

    # Parse SSE: look for lines starting with "data: "
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload:
            continue
        try:
            msg = json.loads(payload)
        except json.JSONDecodeError:
            continue
        # Extract the text content from the JSON-RPC result
        result = msg.get("result", {})
        content_list = result.get("content", [])
        for item in content_list:
            if item.get("type") == "text":
                return item.get("text", "")

    raise RuntimeError(f"MCP API returned no text content for tool '{tool_name}'")


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------

_SUFFIX_MULTIPLIERS = {
    "k": 1_000,
    "K": 1_000,
    "m": 1_000_000,
    "M": 1_000_000,
    "b": 1_000_000_000,
    "B": 1_000_000_000,
    "t": 1_000_000_000_000,
    "T": 1_000_000_000_000,
}


def _parse_number(raw: str) -> float:
    """Parse a human-readable number string into a float.

    Handles:
      - k / M / B / T suffixes  ("1.3B" -> 1_300_000_000)
      - Percentage strings       ("61.6%" -> 0.616)
      - Dollar prefixes           ("$1.3M" -> 1_300_000)
      - Negative values           ("-1.0%" -> -0.01)
      - nan / N/A / --            -> 0.0
      - Comma thousands           ("1,234" -> 1234)
    """
    s = raw.strip()

    # Blanks and sentinels
    if not s or s.lower() in ("nan", "n/a", "--", "-"):
        return 0.0

    # Percentage
    if s.endswith("%"):
        try:
            return float(s[:-1].replace(",", "").lstrip("$")) / 100
        except ValueError:
            return 0.0

    # Handle negative sign before or after currency symbol: -$500k or $-500k
    negative = False
    if s.startswith("-"):
        negative = True
        s = s[1:]
    elif s.startswith("+"):
        s = s[1:]

    # Strip leading currency symbols
    s = s.lstrip("$")

    # Negative may also appear after $ (e.g. "$-500k")
    if s.startswith("-"):
        negative = True
        s = s[1:]
    elif s.startswith("+"):
        s = s[1:]

    # Strip commas
    s = s.replace(",", "")

    # Check for suffix multiplier
    multiplier = 1.0
    if s and s[-1] in _SUFFIX_MULTIPLIERS:
        multiplier = _SUFFIX_MULTIPLIERS[s[-1]]
        s = s[:-1]

    try:
        value = float(s) * multiplier
    except ValueError:
        return 0.0

    return -value if negative else value


# ---------------------------------------------------------------------------
# Markdown table parser
# ---------------------------------------------------------------------------

_SPROUT = "\U0001F331"  # Unicode for the seedling emoji


def _parse_markdown_table(md: str) -> list[dict]:
    """Parse a markdown table into a list of dicts.

    Handles standard GFM tables:
        | Col1 | Col2 |
        |:--|:--|
        | val1 | val2 |

    Returns a list of dicts with stripped keys/values.
    Numeric-looking values are auto-converted via ``_parse_number``.
    """
    lines = [ln.strip() for ln in md.strip().splitlines() if ln.strip()]

    # Find the header row (first row with pipes)
    header_idx = None
    for i, line in enumerate(lines):
        if "|" in line:
            header_idx = i
            break

    if header_idx is None:
        return []

    def _split_row(line: str) -> list[str]:
        """Split a pipe-delimited row, stripping outer pipes."""
        # Remove leading/trailing pipes
        line = line.strip("|")
        return [cell.strip() for cell in line.split("|")]

    headers = _split_row(lines[header_idx])

    # Skip the separator row (|:--|:--|)
    data_start = header_idx + 1
    if data_start < len(lines) and re.match(r"^\|?\s*[:|-]+\s*(\|[:|\s-]+)*\|?\s*$", lines[data_start]):
        data_start += 1

    rows: list[dict] = []
    for line in lines[data_start:]:
        if "|" not in line:
            continue
        values = _split_row(line)
        row: dict = {}
        for j, header in enumerate(headers):
            val_str = values[j] if j < len(values) else ""
            row[header] = val_str
        rows.append(row)

    return rows


def _convert_numeric_values(row: dict) -> dict:
    """Try to convert string values to numeric where it makes sense.

    Preserves strings that look like addresses (0x...) or names.
    """
    out = {}
    for k, v in row.items():
        if not isinstance(v, str):
            out[k] = v
            continue
        stripped = v.strip()
        # Keep hex addresses as strings
        if stripped.startswith("0x") and len(stripped) > 10:
            out[k] = stripped
            continue
        # Keep obvious text (contains letters that aren't suffixes/nan)
        is_text = not re.match(r"^[+\-$.,\d%kKmMbBtTnNaA/ ]+$", stripped)
        if stripped and is_text and stripped.lower() not in ("nan", "n/a"):
            out[k] = stripped
            continue
        # Try numeric conversion
        parsed = _parse_number(stripped)
        if parsed != 0.0 or stripped in ("0", "0.0", "0.0%", "0%", "$0", "nan", "N/A", "--", "-", ""):
            out[k] = parsed
        else:
            out[k] = stripped
    return out


# ---------------------------------------------------------------------------
# Token screener
# ---------------------------------------------------------------------------


def mcp_token_screener(chain: str, page: int = 1) -> list[dict]:
    """Call the MCP ``token_discovery_screener`` tool and return screener rows.

    Returns dicts with keys matching the REST / CLI format so the scanner
    can consume them directly:
      token_address, token_symbol, chain, price_usd, price_change,
      market_cap_usd, volume, netflow, token_age_days, is_new
    """
    text = _mcp_call(
        "token_discovery_screener",
        {"request": {"chains": [chain], "page": page}},
    )

    raw_rows = _parse_markdown_table(text)
    results: list[dict] = []

    for raw in raw_rows:
        _convert_numeric_values(raw)

        # Symbol: strip seedling emoji prefix that marks new tokens
        raw_symbol = raw.get("Symbol", "") or raw.get("symbol", "")
        is_new = _SPROUT in raw_symbol
        symbol = raw_symbol.replace(_SPROUT, "").strip()

        # Price change: "61.6%" -> 0.616 (already handled by _parse_number
        # when _convert_numeric_values runs, but handle the raw string
        # explicitly in case the column name varies).
        price_change_raw = (
            raw.get("Price Change", "") or raw.get("price_change", "") or raw.get("Price Change %", "")
        )
        price_change = (
            _parse_number(price_change_raw) if isinstance(price_change_raw, str) else float(price_change_raw or 0)
        )

        # Market cap
        mcap_raw = raw.get("Market Cap", "") or raw.get("market_cap", "")
        mcap = _parse_number(mcap_raw) if isinstance(mcap_raw, str) else float(mcap_raw or 0)

        # Net flow
        netflow_raw = raw.get("Net Flow USD", "") or raw.get("net_flow_usd", "") or raw.get("Netflow USD", "")
        netflow = _parse_number(netflow_raw) if isinstance(netflow_raw, str) else float(netflow_raw or 0)

        # Volume (buy + sell if both available, otherwise just buy)
        buy_raw = raw.get("Buy USD Volume", "") or raw.get("buy_usd_volume", "")
        sell_raw = raw.get("Sell USD Volume", "") or raw.get("sell_usd_volume", "")
        buy_vol = _parse_number(buy_raw) if isinstance(buy_raw, str) else float(buy_raw or 0)
        sell_vol = _parse_number(sell_raw) if isinstance(sell_raw, str) else float(sell_raw or 0)
        volume = buy_vol + sell_vol if (buy_vol or sell_vol) else 0.0

        # Token address
        token_addr = raw.get("Token Address", "") or raw.get("token_address", "")

        # Price
        price_raw = raw.get("Price USD", "") or raw.get("price_usd", "")
        price = _parse_number(price_raw) if isinstance(price_raw, str) else float(price_raw or 0)

        # Token age
        age_raw = raw.get("Token Age (Days)", "") or raw.get("token_age_days", "") or raw.get("Token Age", "")
        age = _parse_number(age_raw) if isinstance(age_raw, str) else float(age_raw or 0)

        # Chain (from response or fallback to requested chain)
        resp_chain = raw.get("Chain", "") or raw.get("chain", "") or chain

        results.append(
            {
                # Primary keys (user-specified mapping)
                "token_address": token_addr,
                "token_symbol": symbol,
                "chain": resp_chain,
                "price_usd": price,
                "price_change": price_change,
                "market_cap": mcap,
                "market_netflow": netflow,
                "volume_24h": volume,
                "token_age_days": age,
                "is_new": is_new,
                # Aliases for scanner compatibility
                "market_cap_usd": mcap,
                "netflow": netflow,
                "volume": volume,
            }
        )

    return results


# ---------------------------------------------------------------------------
# SM-only token screener (shared helper)
# ---------------------------------------------------------------------------

def _mcp_sm_screener_rows(chain: str, pages: int = 2) -> list[dict]:
    """Call ``token_discovery_screener`` with ``onlySmartTradersAndFunds=true``.

    Returns raw parsed rows (not yet mapped to scanner format).
    Each row has the same markdown columns as the regular screener
    but filtered to Smart Trader & Fund activity only.
    """
    all_rows: list[dict] = []
    for page in range(1, pages + 1):
        text = _mcp_call(
            "token_discovery_screener",
            {
                "request": {
                    "chains": [chain],
                    "page": page,
                    "onlySmartTradersAndFunds": True,
                },
            },
        )
        rows = _parse_markdown_table(text)
        all_rows.extend(rows)
        if len(rows) < 20:  # Less than a full page → last page
            break
    return all_rows


# ---------------------------------------------------------------------------
# Smart money DEX trades (via SM screener)
# ---------------------------------------------------------------------------


def mcp_sm_token_screener(chain: str, pages: int = 2) -> list[dict]:
    """Call the SM-only screener and return tokens in the SAME format
    as ``mcp_token_screener()`` so they can be merged into the main
    token list used by ``scan_chain()``.

    This lets the scanner include SM-active tokens alongside market
    screener tokens, providing proper divergence scoring for tokens
    where SM is most active.
    """
    raw_rows = _mcp_sm_screener_rows(chain, pages=pages)
    results: list[dict] = []

    for raw in raw_rows:
        token_addr = raw.get("Token Address", "") or raw.get("token_address", "")
        if not token_addr:
            continue

        raw_symbol = raw.get("Symbol", "") or raw.get("symbol", "")
        is_new = _SPROUT in raw_symbol
        symbol = raw_symbol.replace(_SPROUT, "").strip()

        price_change_raw = raw.get("Price Change", "") or raw.get("price_change", "")
        price_change = (
            _parse_number(price_change_raw) if isinstance(price_change_raw, str) else float(price_change_raw or 0)
        )

        mcap_raw = raw.get("Market Cap", "") or raw.get("market_cap", "")
        mcap = _parse_number(mcap_raw) if isinstance(mcap_raw, str) else float(mcap_raw or 0)

        netflow_raw = raw.get("Net Flow USD", "") or raw.get("net_flow_usd", "")
        netflow = _parse_number(netflow_raw) if isinstance(netflow_raw, str) else float(netflow_raw or 0)

        buy_raw = raw.get("Buy USD Volume", "") or raw.get("buy_usd_volume", "")
        sell_raw = raw.get("Sell USD Volume", "") or raw.get("sell_usd_volume", "")
        buy_vol = _parse_number(buy_raw) if isinstance(buy_raw, str) else float(buy_raw or 0)
        sell_vol = _parse_number(sell_raw) if isinstance(sell_raw, str) else float(sell_raw or 0)
        volume = buy_vol + sell_vol if (buy_vol or sell_vol) else 0.0

        price_raw = raw.get("Price USD", "") or raw.get("price_usd", "")
        price = _parse_number(price_raw) if isinstance(price_raw, str) else float(price_raw or 0)

        age_raw = raw.get("Token Age (Days)", "") or raw.get("token_age_days", "")
        age = _parse_number(age_raw) if isinstance(age_raw, str) else float(age_raw or 0)

        resp_chain = raw.get("Chain", "") or raw.get("chain", "") or chain

        results.append({
            "token_address": token_addr,
            "token_symbol": symbol,
            "chain": resp_chain,
            "price_usd": price,
            "price_change": price_change,
            "market_cap": mcap,
            "market_netflow": netflow,
            "volume_24h": volume,
            "token_age_days": age,
            "is_new": is_new,
            "market_cap_usd": mcap,
            "netflow": netflow,
            "volume": volume,
        })

    return results


def mcp_smart_money_dex_trades(chain: str) -> list[dict]:
    """Get SM buy/sell activity per token via the SM-only screener.

    Returns synthetic trade records in "simple format" that
    ``aggregate_sm_trades()`` can consume directly:
      {token_address, side, amount_usd, wallet_address, label}

    For each SM screener row with nonzero buy or sell volume,
    we emit one BUY record and/or one SELL record.
    """
    raw_rows = _mcp_sm_screener_rows(chain)
    trades: list[dict] = []

    for raw in raw_rows:
        token_addr = raw.get("Token Address", "") or raw.get("token_address", "")
        if not token_addr:
            continue

        buy_raw = raw.get("Buy USD Volume", "") or raw.get("buy_usd_volume", "")
        sell_raw = raw.get("Sell USD Volume", "") or raw.get("sell_usd_volume", "")
        buy_vol = _parse_number(buy_raw) if isinstance(buy_raw, str) else float(buy_raw or 0)
        sell_vol = _parse_number(sell_raw) if isinstance(sell_raw, str) else float(sell_raw or 0)

        if buy_vol > 0:
            trades.append({
                "token_address": token_addr,
                "side": "buy",
                "amount_usd": buy_vol,
                "wallet_address": "sm_aggregate",
                "label": "Smart Traders & Funds",
            })
        if sell_vol > 0:
            trades.append({
                "token_address": token_addr,
                "side": "sell",
                "amount_usd": sell_vol,
                "wallet_address": "sm_aggregate",
                "label": "Smart Traders & Funds",
            })

    return trades


# ---------------------------------------------------------------------------
# Smart money netflow (via SM screener → radar format)
# ---------------------------------------------------------------------------


def mcp_smart_money_netflow(chain: str) -> list[dict]:
    """Get SM netflow per token via the SM-only screener.

    Returns dicts in the format ``smart_money_netflow()`` / CLI would
    return, used by ``scan_chain()`` to build the SM Radar:
      token_address, token_symbol, net_flow_24h_usd, net_flow_7d_usd,
      trader_count, token_sectors, market_cap_usd
    """
    raw_rows = _mcp_sm_screener_rows(chain)
    results: list[dict] = []

    for raw in raw_rows:
        token_addr = raw.get("Token Address", "") or raw.get("token_address", "")
        if not token_addr:
            continue

        raw_symbol = raw.get("Symbol", "") or raw.get("symbol", "") or raw.get("Token Symbol", "")
        symbol = raw_symbol.replace(_SPROUT, "").strip()

        netflow_raw = raw.get("Net Flow USD", "") or raw.get("net_flow_usd", "")
        netflow = _parse_number(netflow_raw) if isinstance(netflow_raw, str) else float(netflow_raw or 0)

        mcap_raw = raw.get("Market Cap", "") or raw.get("market_cap", "")
        mcap = _parse_number(mcap_raw) if isinstance(mcap_raw, str) else float(mcap_raw or 0)

        # Volume as proxy for trader activity
        vol_raw = raw.get("USD Volume", "") or raw.get("usd_volume", "")
        vol = _parse_number(vol_raw) if isinstance(vol_raw, str) else float(vol_raw or 0)

        # Estimate trader count from buy+sell volume ratio (1 per ~$50k activity)
        trader_est = max(1, int(vol / 50_000)) if vol > 0 else 0

        results.append({
            "token_address": token_addr,
            "token_symbol": symbol,
            "net_flow_24h_usd": netflow,
            "net_flow_7d_usd": 0,  # SM screener only has 24h data
            "trader_count": trader_est,
            "token_sectors": [],
            "market_cap_usd": mcap,
        })

    return results


# ---------------------------------------------------------------------------
# Smart money holdings
# ---------------------------------------------------------------------------


def mcp_smart_money_holdings(chain: str) -> list[dict]:
    """Call the MCP ``smart_traders_and_funds_token_balances`` tool.

    Returns dicts with keys matching the REST / CLI format:
      token_address, token_symbol, chain, value_usd, balance_usd,
      balance_24h_percent_change, holders_count, market_cap, market_cap_usd
    """
    text = _mcp_call(
        "smart_traders_and_funds_token_balances",
        {"request": {"chains": [chain]}},
    )

    raw_rows = _parse_markdown_table(text)
    results: list[dict] = []

    for raw in raw_rows:
        token_addr = raw.get("token_address", "") or raw.get("Token Address", "")
        raw_symbol = raw.get("token_symbol", "") or raw.get("Symbol", "") or raw.get("Token Symbol", "")
        symbol = raw_symbol.replace(_SPROUT, "").strip()

        resp_chain = raw.get("chain", "") or raw.get("Chain", "") or chain

        # Value / balance
        value_raw = raw.get("value_usd", "") or raw.get("Value USD", "") or raw.get("Balance USD", "")
        value_usd = _parse_number(value_raw) if isinstance(value_raw, str) else float(value_raw or 0)

        # Balance change %
        change_raw = (
            raw.get("balance_24h_percent_change", "")
            or raw.get("Balance 24h % Change", "")
            or raw.get("24h Change %", "")
            or raw.get("Balance Change %", "")
        )
        balance_change_pct = _parse_number(change_raw) if isinstance(change_raw, str) else float(change_raw or 0)
        # If parsed from percentage string, _parse_number returns e.g. 0.05 for "5%".
        # The scanner expects the value as a raw percentage number (e.g. 5.0 for 5%),
        # so convert back: 0.05 -> 5.0.
        if isinstance(change_raw, str) and "%" in change_raw:
            balance_change_pct = balance_change_pct * 100

        # Holders count
        holders_raw = raw.get("holders_count", "") or raw.get("Holders Count", "") or raw.get("Holders", "")
        holders = _parse_number(holders_raw) if isinstance(holders_raw, str) else float(holders_raw or 0)

        # Market cap
        mcap_raw = raw.get("market_cap", "") or raw.get("Market Cap", "")
        mcap = _parse_number(mcap_raw) if isinstance(mcap_raw, str) else float(mcap_raw or 0)

        results.append(
            {
                "token_address": token_addr,
                "token_symbol": symbol,
                "chain": resp_chain,
                "value_usd": value_usd,
                "balance_usd": value_usd,
                "balance_24h_percent_change": balance_change_pct,
                "holders_count": int(holders),
                "market_cap": mcap,
                "market_cap_usd": mcap,
            }
        )

    return results
