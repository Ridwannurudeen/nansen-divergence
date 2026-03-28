#!/usr/bin/env python3
"""Refresh dashboard cache using MCP general_search (0 API credits).

Uses the general_search MCP tool to get fresh token prices,
computes price changes, re-scores divergence, and updates the cache.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nansen_divergence.divergence import (
    alpha_score,
    classify_phase,
    generate_narrative,
    is_stablecoin,
    score_divergence,
)

# ---------------------------------------------------------------------------
# MCP transport
# ---------------------------------------------------------------------------

_MCP_URL = "https://mcp.nansen.ai/ra/mcp"


class _PostRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if code in (307, 308):
            new_req = urllib.request.Request(
                newurl, data=req.data, headers=dict(req.headers), method=req.get_method()
            )
            return new_req
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_PostRedirectHandler)


def _mcp_search(query: str) -> str:
    """Call MCP general_search and return the text result."""
    key = os.environ.get("NANSEN_API_KEY", "") or os.environ.get("NANSEN_MCP_KEY", "")
    if not key:
        raise RuntimeError("No API key set")

    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "general_search",
            "arguments": {"query": query},
        },
    }).encode()

    req = urllib.request.Request(
        _MCP_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "NANSEN-API-KEY": key.strip(),
            "Accept": "application/json, text/event-stream",
            "User-Agent": "nansen-divergence/5.0",
        },
        method="POST",
    )

    with _opener.open(req, timeout=60) as resp:
        raw = resp.read().decode()

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
        result = msg.get("result", {})
        if result.get("isError"):
            raise RuntimeError(f"MCP error: {result}")
        content_list = result.get("content", [])
        for item in content_list:
            if item.get("type") == "text":
                return item.get("text", "")

    return ""


# ---------------------------------------------------------------------------
# Markdown table parser
# ---------------------------------------------------------------------------

_SUFFIX = {"k": 1e3, "K": 1e3, "m": 1e6, "M": 1e6, "b": 1e9, "B": 1e9, "t": 1e12, "T": 1e12}


def _parse_num(s: str) -> float:
    s = s.strip()
    if not s or s.lower() in ("nan", "n/a", "--", "-"):
        return 0.0
    if s.endswith("%"):
        try:
            return float(s[:-1].replace(",", "").lstrip("$")) / 100
        except ValueError:
            return 0.0
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    s = s.lstrip("$+").replace(",", "")
    if s.startswith("-"):
        neg = True
        s = s[1:]
    mult = 1.0
    if s and s[-1] in _SUFFIX:
        mult = _SUFFIX[s[-1]]
        s = s[:-1]
    try:
        v = float(s) * mult
    except ValueError:
        return 0.0
    return -v if neg else v


def _parse_table(md: str) -> list[dict]:
    lines = [ln.strip() for ln in md.strip().splitlines() if ln.strip()]
    header_idx = None
    for i, line in enumerate(lines):
        if "|" in line and not re.match(r"^\|?\s*[:|-]+\s*(\|[:|\s-]+)*\|?\s*$", line):
            header_idx = i
            break
    if header_idx is None:
        return []

    def split_row(line):
        return [c.strip() for c in line.strip("|").split("|")]

    headers = split_row(lines[header_idx])
    start = header_idx + 1
    if start < len(lines) and re.match(r"^\|?\s*[:|-]+", lines[start]):
        start += 1

    rows = []
    for line in lines[start:]:
        if "|" not in line:
            continue
        vals = split_row(line)
        row = {}
        for j, h in enumerate(headers):
            row[h] = vals[j] if j < len(vals) else ""
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Search & parse
# ---------------------------------------------------------------------------


def search_tokens(query: str) -> list[dict]:
    """Search for tokens and return parsed results."""
    text = _mcp_search(query)
    if not text:
        return []

    rows = _parse_table(text)
    results = []
    for row in rows:
        symbol = row.get("Symbol", "").replace("\U0001f331", "").strip()
        addr = row.get("Contract Address", "").strip()
        chain = row.get("Chain", "").strip()
        price = _parse_num(row.get("Price USD", ""))
        volume = _parse_num(row.get("Volume 24h USD", ""))
        name = row.get("Name", "").strip()

        if not symbol or not addr:
            continue

        results.append({
            "token_symbol": symbol,
            "token_address": addr,
            "chain": chain,
            "price_usd": price,
            "volume_24h": volume,
            "name": name,
        })
    return results


def discover_chain_tokens(chain: str, extra_queries: list[str] | None = None) -> list[dict]:
    """Discover tokens for a chain using multiple search queries."""
    all_tokens: dict[str, dict] = {}  # keyed by address

    # Search chain name
    for tok in search_tokens(chain):
        if tok["token_address"] not in all_tokens:
            all_tokens[tok["token_address"]] = tok

    # Search extra queries
    for q in (extra_queries or []):
        time.sleep(0.3)  # Be nice to the API
        for tok in search_tokens(q):
            if tok["token_address"] not in all_tokens:
                all_tokens[tok["token_address"]] = tok

    return list(all_tokens.values())


# ---------------------------------------------------------------------------
# Refresh logic
# ---------------------------------------------------------------------------

CACHE_PATH = Path(os.environ.get(
    "CACHE_DIR", str(Path.home() / ".nansen-divergence")
)) / "cache" / "latest.json"


def load_cache() -> dict:
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_cache(data: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def refresh_cache():
    """Main refresh: update prices via MCP search, recompute scores."""
    cache = load_cache()
    results = cache.get("results", [])
    print(f"Loaded {len(results)} tokens from cache")

    # Build price lookup from MCP search
    # Search for each unique symbol in the cache
    symbols = sorted(set(r.get("token_symbol", "") for r in results if r.get("token_symbol")))
    print(f"Searching for {len(symbols)} symbols via MCP general_search...")

    price_lookup: dict[str, float] = {}  # token_address -> price
    volume_lookup: dict[str, float] = {}

    for sym in symbols:
        if is_stablecoin(sym):
            continue
        try:
            found = search_tokens(sym)
            for t in found:
                addr = t["token_address"].lower()
                if t["price_usd"] > 0:
                    price_lookup[addr] = t["price_usd"]
                if t["volume_24h"] > 0:
                    volume_lookup[addr] = t["volume_24h"]
            time.sleep(0.2)
        except Exception as e:
            print(f"  Search failed for {sym}: {e}")

    print(f"Got prices for {len(price_lookup)} addresses")

    # Also discover Solana tokens if not in cache
    chains_in_cache = set(r.get("chain") for r in results)
    new_tokens = []

    if "solana" not in chains_in_cache:
        print("Discovering Solana tokens...")
        sol_tokens = discover_chain_tokens("solana", ["SOL", "JUP", "BONK", "WIF", "RENDER", "JTO", "PYTH"])
        for t in sol_tokens:
            if t["chain"] == "solana" and not is_stablecoin(t["token_symbol"]) and t["price_usd"] > 0:
                new_tokens.append(t)
        print(f"  Found {len(new_tokens)} Solana tokens")

    # Also add some popular tokens if missing
    missing_searches = []
    big_tokens = ["BTC", "ETH", "SOL", "PEPE", "ARB", "OP", "MATIC", "AVAX", "DOT", "ADA"]
    cached_syms = set(s.upper() for s in symbols)
    for bt in big_tokens:
        if bt not in cached_syms:
            missing_searches.append(bt)

    for q in missing_searches[:5]:  # Limit to 5 extra searches
        try:
            found = search_tokens(q)
            for t in found:
                if t["chain"] in ("ethereum", "bnb", "solana", "base", "arbitrum") and \
                   not is_stablecoin(t["token_symbol"]) and t["price_usd"] > 0:
                    addr = t["token_address"].lower()
                    if addr not in price_lookup:
                        new_tokens.append(t)
                        price_lookup[addr] = t["price_usd"]
            time.sleep(0.2)
        except Exception as e:
            print(f"  Search failed for {q}: {e}")

    # Update existing tokens with fresh prices
    updated = 0
    for r in results:
        addr = r.get("token_address", "").lower()
        old_price = r.get("price_usd", 0)

        if addr in price_lookup:
            new_price = price_lookup[addr]
            if old_price > 0 and new_price > 0:
                # Compute fresh price change
                r["price_change"] = (new_price - old_price) / old_price
            r["price_usd"] = new_price
            updated += 1

        if addr in volume_lookup:
            r["volume_24h"] = volume_lookup[addr]

        # Re-score divergence
        sm_flow = r.get("sm_net_flow", 0) or r.get("market_netflow", 0)
        price_chg = r.get("price_change", 0)
        mcap = r.get("market_cap", 0) or r.get("market_cap_usd", 0)

        if mcap > 0:
            strength, phase, confidence = score_divergence(
                sm_flow, price_chg, mcap,
                trader_count=r.get("sm_trader_count", 0),
                holdings_change=r.get("sm_holdings_change", 0),
            )
            r["divergence_strength"] = strength
            r["phase"] = phase
            r["confidence"] = confidence
            r["alpha_score"] = alpha_score(strength)

        # Regenerate narrative
        r["narrative"] = generate_narrative(r)

    print(f"Updated prices for {updated}/{len(results)} existing tokens")

    # Add new discovered tokens
    added = 0
    existing_addrs = set(r.get("token_address", "").lower() for r in results)
    for t in new_tokens:
        if t["token_address"].lower() in existing_addrs:
            continue
        if len(results) >= 60:  # Cap at 60 tokens
            break

        mcap = t.get("market_cap", 0) or t["volume_24h"] * 10  # Rough estimate
        price_chg = 0.0  # No historical reference

        strength, phase, confidence = score_divergence(0, price_chg, max(mcap, 1))

        token_result = {
            "token_symbol": t["token_symbol"],
            "token_address": t["token_address"],
            "chain": t["chain"],
            "price_usd": t["price_usd"],
            "price_change": price_chg,
            "market_cap": mcap,
            "market_cap_usd": mcap,
            "volume_24h": t.get("volume_24h", 0),
            "sm_net_flow": 0,
            "sm_trader_count": 0,
            "sm_buy_volume": 0,
            "sm_sell_volume": 0,
            "sm_holdings_change": 0,
            "market_netflow": 0,
            "divergence_strength": strength,
            "phase": phase,
            "confidence": confidence,
            "alpha_score": alpha_score(strength),
            "narrative": "",
        }
        token_result["narrative"] = generate_narrative(token_result)
        results.append(token_result)
        existing_addrs.add(t["token_address"].lower())
        added += 1

    print(f"Added {added} new tokens")

    # Sort by divergence strength descending
    results.sort(key=lambda r: r.get("divergence_strength", 0), reverse=True)

    # Rebuild summary
    total = len(results)
    divergent = [r for r in results if r.get("phase") in ("ACCUMULATION", "DISTRIBUTION")]
    high_conf = [r for r in results if r.get("confidence") == "HIGH"]
    accum = [r for r in results if r.get("phase") == "ACCUMULATION"]
    distrib = [r for r in results if r.get("phase") == "DISTRIBUTION"]
    chains_list = sorted(set(r.get("chain", "") for r in results))

    summary = {
        "total_tokens": total,
        "divergent_signals": len(divergent),
        "high_confidence": len(high_conf),
        "accumulation": len(accum),
        "distribution": len(distrib),
        "chains_scanned": len(chains_list),
        "data_source": "mcp_search_refresh",
    }

    cache["results"] = results
    cache["summary"] = summary
    cache["chains"] = chains_list

    save_cache(cache)
    print(f"\nCache updated: {total} tokens, {len(divergent)} divergent, {len(high_conf)} HIGH confidence")
    print(f"Chains: {chains_list}")
    print(f"Saved to {CACHE_PATH}")


if __name__ == "__main__":
    refresh_cache()
