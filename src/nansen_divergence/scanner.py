"""Core scan logic: fetch data from Nansen, aggregate SM trades, score, and classify tokens."""

import time

from rich.console import Console

from . import nansen
from .divergence import generate_narrative, is_divergent, is_stablecoin, score_divergence
from .nansen import InsufficientCreditsError

console = Console(stderr=True, force_terminal=True)


def _ensure_agg_entry(agg: dict, addr: str) -> dict:
    """Create or return an aggregation entry for a token address."""
    if addr not in agg:
        agg[addr] = {
            "buy_volume": 0.0,
            "sell_volume": 0.0,
            "net_flow": 0.0,
            "trader_count": 0,
            "_wallets": set(),
            "wallet_labels": [],
        }
    return agg[addr]


def aggregate_sm_trades(dex_trades: list[dict], target_addrs: set[str]) -> dict[str, dict]:
    """Group individual SM dex trades by token address, computing buy/sell/net/trader_count.

    Handles two API response formats:
    - Swap-pair format: token_bought_address / token_sold_address + trade_value_usd
    - Simple format: token_address + side + amount_usd (fallback)

    Returns {token_address_lower: {buy_volume, sell_volume, net_flow, trader_count, wallet_labels}}
    """
    agg: dict[str, dict] = {}

    for trade in dex_trades:
        trade_value = abs(trade.get("trade_value_usd") or trade.get("amount_usd") or trade.get("usd_amount") or 0)
        wallet = trade.get("trader_address") or trade.get("wallet_address") or trade.get("address") or ""
        label = trade.get("trader_address_label") or trade.get("label") or trade.get("wallet_label") or ""

        # Swap-pair format: each trade has a bought token and a sold token
        bought_addr = (trade.get("token_bought_address") or "").lower()
        sold_addr = (trade.get("token_sold_address") or "").lower()

        if bought_addr or sold_addr:
            # If the bought token is in our targets, it's a buy for that token
            if bought_addr and bought_addr in target_addrs:
                entry = _ensure_agg_entry(agg, bought_addr)
                entry["buy_volume"] += trade_value
                entry["net_flow"] += trade_value
                if wallet and wallet not in entry["_wallets"]:
                    entry["_wallets"].add(wallet)
                    entry["trader_count"] += 1
                    if label:
                        entry["wallet_labels"].append(label)

            # If the sold token is in our targets, it's a sell for that token
            if sold_addr and sold_addr in target_addrs:
                entry = _ensure_agg_entry(agg, sold_addr)
                entry["sell_volume"] += trade_value
                entry["net_flow"] -= trade_value
                if wallet and wallet not in entry["_wallets"]:
                    entry["_wallets"].add(wallet)
                    entry["trader_count"] += 1
                    if label:
                        entry["wallet_labels"].append(label)
        else:
            # Simple format fallback: token_address + side
            token_addr = (trade.get("token_address") or "").lower()
            if not token_addr or token_addr not in target_addrs:
                continue

            side = (trade.get("side") or trade.get("trade_type") or "").lower()
            entry = _ensure_agg_entry(agg, token_addr)

            if side in ("buy", "bought", "swap_buy"):
                entry["buy_volume"] += trade_value
                entry["net_flow"] += trade_value
            elif side in ("sell", "sold", "swap_sell"):
                entry["sell_volume"] += trade_value
                entry["net_flow"] -= trade_value

            if wallet and wallet not in entry["_wallets"]:
                entry["_wallets"].add(wallet)
                entry["trader_count"] += 1
                if label:
                    entry["wallet_labels"].append(label)

    # Clean up internal sets (not JSON-serializable)
    for data in agg.values():
        del data["_wallets"]

    return agg


def match_holdings(holdings: list[dict], target_addrs: set[str]) -> dict[str, dict]:
    """Match SM holdings to screener token addresses.

    Returns {token_address_lower: {holdings_value, holdings_change}}

    Handles real API fields:
    - value_usd: total holding value
    - balance_24h_percent_change: percentage change (0.27 = 0.27%)
    - Computes USD change as value_usd * (pct_change / 100)
    """
    result = {}
    for h in holdings:
        addr = (h.get("token_address") or "").lower()
        if not addr or addr not in target_addrs:
            continue

        value = h.get("value_usd") or h.get("balance_usd") or 0
        pct_change = h.get("balance_24h_percent_change") or 0

        # Convert percentage change to USD change
        if value and pct_change:
            usd_change = value * (pct_change / 100)
        else:
            usd_change = h.get("balance_change_24h_usd") or h.get("change_24h_usd") or 0

        result[addr] = {
            "holdings_value": value,
            "holdings_change": usd_change,
        }

    return result


def scan_chain(
    chain: str,
    timeframe: str = "24h",
    limit: int = 20,
    include_stables: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Scan a single chain with 4 data sources.

    Returns (screener_results, sm_radar_tokens).

    Data sources:
    1. Token screener: price, market cap, market netflow
    2. SM dex-trades: individual SM wallet trades -> aggregated per token
    3. SM holdings: SM positions + 24h balance change
    4. SM netflow: legacy flow data for radar section
    """
    pages = max(1, (limit + 9) // 10)

    console.print(f"  [dim]Fetching token screener for [bold]{chain}[/bold]...[/dim]")
    tokens = nansen.token_screener(chain, timeframe=timeframe, pages=pages)

    if not tokens:
        console.print(f"  [yellow]⚠ {chain.upper()}: screener returned 0 tokens — skipping SM endpoints[/yellow]")
        return [], []

    import os

    dex_pages = int(os.getenv("SCAN_DEX_PAGES", "1"))
    netflow_pages = int(os.getenv("SCAN_NETFLOW_PAGES", "1"))
    console.print(f"  [dim]Fetching SM dex-trades for [bold]{chain}[/bold] ({dex_pages}p)...[/dim]")
    try:
        dex_trades = nansen.smart_money_dex_trades(chain, pages=dex_pages)
    except InsufficientCreditsError:
        console.print("  [yellow]⚠ Credits exhausted on dex-trades — using screener data only[/yellow]")
        dex_trades = []

    console.print(f"  [dim]Fetching SM holdings for [bold]{chain}[/bold]...[/dim]")
    try:
        holdings = nansen.smart_money_holdings(chain)
    except InsufficientCreditsError:
        console.print("  [yellow]⚠ Credits exhausted on holdings — skipping[/yellow]")
        holdings = []

    console.print(f"  [dim]Fetching SM netflow for [bold]{chain}[/bold] ({netflow_pages}p)...[/dim]")
    try:
        netflow = nansen.smart_money_netflow(chain, pages=netflow_pages)
    except InsufficientCreditsError:
        console.print("  [yellow]⚠ Credits exhausted on netflow — skipping[/yellow]")
        netflow = []

    # Deduplicate tokens (MCP pagination can return duplicates)
    seen_addrs: set[str] = set()
    unique_tokens: list[dict] = []
    for t in tokens:
        addr = (t.get("token_address") or "").lower()
        if addr and addr not in seen_addrs:
            seen_addrs.add(addr)
            unique_tokens.append(t)

    # Build target address set from ALL screener tokens (including
    # SM-active tokens merged in by the MCP path) so that SM trade
    # records can match against them.
    target_addrs = set()
    for t in unique_tokens:
        addr = (t.get("token_address") or "").lower()
        if addr:
            target_addrs.add(addr)

    # Aggregate SM data per screener token
    sm_trades = aggregate_sm_trades(dex_trades, target_addrs)
    sm_holdings = match_holdings(holdings, target_addrs)

    # Build screener results
    screener_addrs = set()
    results = []

    for token in unique_tokens:
        addr = (token.get("token_address") or "").lower()
        symbol = token.get("token_symbol") or "???"
        screener_addrs.add(addr)

        # Filter stablecoins unless explicitly included
        if not include_stables and is_stablecoin(symbol):
            continue

        mcap = token.get("market_cap_usd") or 0
        if mcap <= 0:
            continue

        price_change = token.get("price_change") or 0
        market_netflow = token.get("netflow") or 0

        # SM trade data
        sm = sm_trades.get(addr, {})
        sm_flow = sm.get("net_flow", 0)
        sm_buy = sm.get("buy_volume", 0)
        sm_sell = sm.get("sell_volume", 0)
        sm_count = sm.get("trader_count", 0)
        sm_labels = sm.get("wallet_labels", [])

        # SM holdings data
        hold = sm_holdings.get(addr, {})
        hold_value = hold.get("holdings_value", 0)
        hold_change = hold.get("holdings_change", 0)

        # Use SM flow if available, fall back to market netflow
        scoring_flow = sm_flow if sm_flow != 0 else market_netflow

        strength, phase, confidence = score_divergence(
            sm_net_flow=scoring_flow,
            price_change_pct=price_change,
            market_cap=mcap,
            trader_count=sm_count,
            holdings_change=hold_change,
        )

        token_data = {
            "chain": chain,
            "token_address": token.get("token_address", ""),
            "token_symbol": symbol,
            "price_usd": token.get("price_usd", 0),
            "price_change": price_change,
            "market_cap": mcap,
            "volume_24h": token.get("volume", 0),
            "market_netflow": market_netflow,
            "sm_net_flow": sm_flow,
            "sm_buy_volume": sm_buy,
            "sm_sell_volume": sm_sell,
            "sm_trader_count": sm_count,
            "sm_wallet_labels": sm_labels,
            "sm_holdings_value": hold_value,
            "sm_holdings_change": hold_change,
            "divergence_strength": strength,
            "phase": phase,
            "confidence": confidence,
            "narrative": "",
            "has_sm_data": sm_flow != 0 or hold_value != 0,
        }

        token_data["narrative"] = generate_narrative(token_data)
        results.append(token_data)

    # Sort by divergence strength descending, then limit output
    results.sort(key=lambda x: x["divergence_strength"], reverse=True)
    results = results[:limit]

    # SM Radar: tokens in netflow but NOT in final results
    result_addrs = {(r.get("token_address") or "").lower() for r in results}
    sm_netflow_map = {}
    for f in netflow:
        nf_addr = (f.get("token_address") or "").lower()
        if nf_addr:
            sm_netflow_map[nf_addr] = f

    sm_radar = []
    for nf_addr, f in sm_netflow_map.items():
        if nf_addr not in result_addrs:
            symbol = f.get("token_symbol") or "???"
            if not include_stables and is_stablecoin(symbol):
                continue
            sm_radar.append(
                {
                    "chain": chain,
                    "token_address": f.get("token_address", ""),
                    "token_symbol": symbol,
                    "sm_net_flow_24h": f.get("net_flow_24h_usd", 0),
                    "sm_net_flow_7d": f.get("net_flow_7d_usd", 0),
                    "sm_trader_count": f.get("trader_count", 0),
                    "sm_sectors": f.get("token_sectors", []),
                    "market_cap": f.get("market_cap_usd", 0),
                }
            )

    sm_radar.sort(key=lambda x: abs(x.get("sm_net_flow_24h", 0)), reverse=True)
    return results, sm_radar


def scan_multi_chain(
    chains: list[str],
    timeframe: str = "24h",
    limit: int = 20,
    include_stables: bool = False,
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Scan multiple chains. Returns (chain_results, chain_sm_radar)."""
    all_results = {}
    all_radar = {}
    total = len(chains)
    for idx, chain in enumerate(chains, 1):
        console.print(f"\n[bold cyan][{idx}/{total}] Scanning {chain.upper()}...[/bold cyan]")
        try:
            results, radar = scan_chain(chain, timeframe, limit, include_stables=include_stables)
            all_results[chain] = results
            all_radar[chain] = radar
            console.print(f"  [green]✓ {chain.upper()}: {len(results)} tokens, {len(radar)} radar[/green]")
        except InsufficientCreditsError:
            console.print(f"  [red]✗ Credits exhausted at {chain.upper()} — stopping[/red]")
            all_results[chain] = []
            all_radar[chain] = []
            break  # Stop scanning further chains
        except Exception as e:
            console.print(f"  [red]✗ {chain.upper()} failed: {e}[/red]")
            all_results[chain] = []
            all_radar[chain] = []
        if idx < total:
            time.sleep(2)
    return all_results, all_radar


def flatten_and_rank(chain_results: dict[str, list[dict]]) -> list[dict]:
    """Flatten multi-chain results into a single list, sorted by divergence strength."""
    flat = []
    for tokens in chain_results.values():
        flat.extend(tokens)
    flat.sort(key=lambda x: x["divergence_strength"], reverse=True)
    return flat


def flatten_radar(chain_radar: dict[str, list[dict]]) -> list[dict]:
    """Flatten SM radar across chains."""
    flat = []
    for tokens in chain_radar.values():
        flat.extend(tokens)
    flat.sort(key=lambda x: abs(x.get("sm_net_flow_24h", 0)), reverse=True)
    return flat


def count_api_credits(chains: list[str], limit: int = 20) -> int:
    """Estimate the number of API credits for a scan.

    Credit costs (Pro plan): screener=1/call, SM endpoints=5/call.
    Per chain: screener_pages*1 + dex_pages*5 + 1*5 holdings + netflow_pages*5
    """
    import os

    screener_pages = max(1, (limit + 9) // 10)
    dex_pages = int(os.getenv("SCAN_DEX_PAGES", "1"))
    netflow_pages = int(os.getenv("SCAN_NETFLOW_PAGES", "1"))
    per_chain = screener_pages * 1 + dex_pages * 5 + 1 * 5 + netflow_pages * 5
    return len(chains) * per_chain


def summarize(results: list[dict], radar: list[dict]) -> dict:
    """Generate summary statistics."""
    divergent = [r for r in results if is_divergent(r["phase"])]
    accumulation = [r for r in results if r["phase"] == "ACCUMULATION"]
    distribution = [r for r in results if r["phase"] == "DISTRIBUTION"]
    with_sm = [r for r in results if r.get("has_sm_data")]
    high_conf = [r for r in results if r.get("confidence") == "HIGH"]
    med_conf = [r for r in results if r.get("confidence") == "MEDIUM"]
    low_conf = [r for r in results if r.get("confidence") == "LOW"]

    cli_enriched = [r for r in results if r.get("signal_source") == "nansen_cli"]

    return {
        "total_tokens": len(results),
        "with_sm_data": len(with_sm),
        "sm_data_pct": round(len(with_sm) / len(results) * 100, 1) if results else 0,
        "sm_radar_tokens": len(radar),
        "divergence_signals": len(divergent),
        "accumulation": len(accumulation),
        "distribution": len(distribution),
        "confidence_high": len(high_conf),
        "confidence_medium": len(med_conf),
        "confidence_low": len(low_conf),
        "cli_enriched_count": len(cli_enriched),
    }
