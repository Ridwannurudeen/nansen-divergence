"""Wrapper around the Nansen CLI binary (or REST API / MCP API).

Priority order: MCP API > REST API > CLI binary.
Each function maps to one CLI command / API endpoint / MCP tool.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

from .mcp_client import (
    _get_mcp_key,
    mcp_sm_token_screener,
    mcp_smart_money_dex_trades,
    mcp_smart_money_holdings,
    mcp_smart_money_netflow,
    mcp_token_screener,
)

# ---------------------------------------------------------------------------
# REST API helpers
# ---------------------------------------------------------------------------

_API_BASE = "https://api.nansen.ai/api/v1"


def _get_api_key() -> str | None:
    """Return the Nansen REST API key from env, or None."""
    return os.environ.get("NANSEN_API_KEY", "").strip() or None


def _api_post(endpoint: str, payload: dict) -> dict:
    """POST to the Nansen REST API and return parsed JSON."""
    key = _get_api_key()
    if not key:
        raise RuntimeError("NANSEN_API_KEY not set")

    url = f"{_API_BASE}{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"apikey": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace") if exc.fp else ""
        print(f"Nansen API error {exc.code} on {endpoint}: {body}", file=sys.stderr)
        return {}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Nansen API request failed for {endpoint}: {exc}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def _find_nansen() -> str:
    """Find the nansen binary, handling Windows .cmd wrappers."""
    # shutil.which handles .cmd/.bat on Windows automatically
    path = shutil.which("nansen")
    if path:
        return path
    # Fallback: common npm global location on Windows
    npm_path = os.path.join(os.environ.get("APPDATA", ""), "npm", "nansen.cmd")
    if os.path.isfile(npm_path):
        return npm_path
    return "nansen"


_NANSEN_BIN = _find_nansen()


def _run(args: list[str]) -> dict:
    """Execute a nansen CLI command and return parsed JSON."""
    cmd = [_NANSEN_BIN] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, shell=(os.name == "nt"), encoding="utf-8", errors="replace"
        )
    except FileNotFoundError:
        print("Error: 'nansen' CLI not found. Install it: npm i -g @anthropic-ai/nansen", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"Error: command timed out: {' '.join(cmd)}", file=sys.stderr)
        return {"success": False, "data": {"data": []}}

    if result.returncode != 0:
        print(f"Error running: {' '.join(cmd)}\n{result.stderr}", file=sys.stderr)
        return {"success": False, "data": {"data": []}}

    if not result.stdout:
        print(f"Error: empty output from: {' '.join(cmd)}", file=sys.stderr)
        return {"success": False, "data": {"data": []}}

    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        print(f"Error: non-JSON output from: {' '.join(cmd)}", file=sys.stderr)
        return {"success": False, "data": {"data": []}}


def token_screener(chain: str, timeframe: str = "24h", pages: int = 2) -> list[dict]:
    """Fetch top tokens from the screener. Returns list of token dicts.

    Priority: MCP API > REST API > CLI binary.
    """
    # --- MCP path (first priority) ---
    if _get_mcp_key():
        all_tokens: list[dict] = []
        try:
            for page in range(1, pages + 1):
                all_tokens.extend(mcp_token_screener(chain, page=page))
        except RuntimeError as exc:
            print(f"MCP token_screener failed, falling back: {exc}", file=sys.stderr)
            all_tokens = []

        # Merge SM-active tokens so the scanner has targets for SM trade matching.
        # SM traders often trade different tokens than what appears in the
        # market-wide screener; including them ensures divergence scoring works.
        if all_tokens:
            try:
                sm_tokens = mcp_sm_token_screener(chain, pages=1)
                existing = {(t.get("token_address") or "").lower() for t in all_tokens}
                for st in sm_tokens:
                    if (st.get("token_address") or "").lower() not in existing:
                        all_tokens.append(st)
            except RuntimeError:
                pass  # SM screener is optional enrichment
            return all_tokens

    # --- REST API path ---
    if _get_api_key():
        all_tokens = []
        for page in range(1, pages + 1):
            resp = _api_post("/token-screener", {"chain": chain, "timeframe": timeframe, "page": page})
            data = resp.get("data", resp)
            if isinstance(data, dict):
                all_tokens.extend(data.get("data", []))
                if data.get("pagination", {}).get("is_last_page", True):
                    break
            elif isinstance(data, list):
                all_tokens.extend(data)
                break
            else:
                break
        return all_tokens

    # --- CLI fallback ---
    all_tokens = []
    for page in range(1, pages + 1):
        resp = _run(["research", "token", "screener", "--chain", chain, "--timeframe", timeframe, "--page", str(page)])
        if resp.get("success"):
            all_tokens.extend(resp["data"]["data"])
            if resp["data"].get("pagination", {}).get("is_last_page", True):
                break
        else:
            break
    return all_tokens


def smart_money_netflow(chain: str) -> list[dict]:
    """Fetch smart money net flows per token.

    Priority: MCP API > REST API > CLI binary.
    """
    # --- MCP path (first priority) ---
    if _get_mcp_key():
        try:
            flows = mcp_smart_money_netflow(chain)
        except RuntimeError as exc:
            print(f"MCP smart_money_netflow failed, falling back: {exc}", file=sys.stderr)
            flows = []
        if flows:
            return flows

    # --- REST API path ---
    if _get_api_key():
        all_flows = []
        for page in range(1, 3):
            resp = _api_post("/smart-money/netflow", {"chain": chain, "page": page})
            data = resp.get("data", resp)
            if isinstance(data, dict):
                all_flows.extend(data.get("data", []))
                if data.get("pagination", {}).get("is_last_page", True):
                    break
            elif isinstance(data, list):
                all_flows.extend(data)
                break
            else:
                break
        return all_flows

    all_flows = []
    for page in range(1, 3):
        resp = _run(["research", "smart-money", "netflow", "--chain", chain, "--page", str(page)])
        if resp.get("success"):
            all_flows.extend(resp["data"]["data"])
            if resp["data"].get("pagination", {}).get("is_last_page", True):
                break
        else:
            break
    return all_flows


def flow_intelligence(chain: str, token: str, days: int = 30) -> dict:
    """Get flow intelligence breakdown by label for a token."""
    if _get_api_key():
        resp = _api_post("/tgm/flow-intelligence", {"chain": chain, "token": token, "days": days})
        return resp.get("data", resp) if resp else {}

    resp = _run(["research", "token", "flow-intelligence", "--chain", chain, "--token", token, "--days", str(days)])
    if resp.get("success"):
        return resp["data"]
    return {}


def who_bought_sold(chain: str, token: str, days: int = 30) -> dict:
    """Get recent buyers and sellers for a token."""
    if _get_api_key():
        resp = _api_post("/tgm/who-bought-sold", {"chain": chain, "token": token, "days": days})
        return resp.get("data", resp) if resp else {}

    resp = _run(["research", "token", "who-bought-sold", "--chain", chain, "--token", token, "--days", str(days)])
    if resp.get("success"):
        return resp["data"]
    return {}


def profiler_labels(address: str, chain: str = "ethereum") -> dict:
    """Get behavioral and entity labels for a wallet."""
    if _get_api_key():
        resp = _api_post("/profiler/address/labels", {"address": address, "chain": chain})
        return resp.get("data", resp) if resp else {}

    resp = _run(["research", "profiler", "labels", "--address", address, "--chain", chain])
    if resp.get("success"):
        return resp["data"]
    return {}


def profiler_pnl_summary(address: str, chain: str = "ethereum", days: int = 30) -> dict:
    """Get PnL summary for a wallet."""
    if _get_api_key():
        resp = _api_post("/profiler/address/pnl-summary", {"address": address, "chain": chain, "days": days})
        return resp.get("data", resp) if resp else {}

    resp = _run(["research", "profiler", "pnl-summary", "--address", address, "--chain", chain, "--days", str(days)])
    if resp.get("success"):
        return resp["data"]
    return {}


def smart_money_dex_trades(chain: str, pages: int = 3) -> list[dict]:
    """Fetch individual smart money DEX trades with wallet labels.

    Priority: MCP API > REST API > CLI binary.
    """
    # --- MCP path (first priority) ---
    if _get_mcp_key():
        try:
            trades = mcp_smart_money_dex_trades(chain)
        except RuntimeError as exc:
            print(f"MCP smart_money_dex_trades failed, falling back: {exc}", file=sys.stderr)
            trades = []
        if trades:
            return trades

    # --- REST API path ---
    if _get_api_key():
        all_trades = []
        for page in range(1, pages + 1):
            resp = _api_post("/smart-money/dex-trades", {"chain": chain, "page": page})
            data = resp.get("data", resp)
            if isinstance(data, dict):
                all_trades.extend(data.get("data", []))
                if data.get("pagination", {}).get("is_last_page", True):
                    break
            elif isinstance(data, list):
                all_trades.extend(data)
                break
            else:
                break
        return all_trades

    all_trades = []
    for page in range(1, pages + 1):
        resp = _run(["research", "smart-money", "dex-trades", "--chain", chain, "--page", str(page)])
        if resp.get("success"):
            all_trades.extend(resp["data"]["data"])
            if resp["data"].get("pagination", {}).get("is_last_page", True):
                break
        else:
            break
    return all_trades


def smart_money_holdings(chain: str) -> list[dict]:
    """Fetch smart money holdings with 24h balance changes.

    Priority: MCP API > REST API > CLI binary.
    """
    # --- MCP path (first priority) ---
    if _get_mcp_key():
        try:
            holdings = mcp_smart_money_holdings(chain)
        except RuntimeError as exc:
            print(f"MCP smart_money_holdings failed, falling back: {exc}", file=sys.stderr)
            holdings = []
        if holdings:
            return holdings

    # --- REST API path ---
    if _get_api_key():
        resp = _api_post("/smart-money/holdings", {"chain": chain})
        data = resp.get("data", resp)
        if isinstance(data, dict):
            return data.get("data", [])
        if isinstance(data, list):
            return data
        return []

    # --- CLI fallback ---
    resp = _run(["research", "smart-money", "holdings", "--chain", chain])
    if resp.get("success"):
        return resp["data"].get("data", [])
    return []


def token_indicators(chain: str, token: str) -> dict:
    """Fetch Nansen Score (risk/reward indicators) for a token."""
    if _get_api_key():
        resp = _api_post("/tgm/indicators", {"chain": chain, "token": token})
        return resp.get("data", resp) if resp else {}

    resp = _run(["research", "token", "indicators", "--chain", chain, "--token", token])
    if resp.get("success"):
        return resp["data"]
    return {}
