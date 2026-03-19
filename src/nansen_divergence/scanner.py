"""Core scan logic: fetch data from Nansen, merge, score, and classify tokens."""

from rich.console import Console

from . import nansen
from .divergence import is_divergent, score_divergence

console = Console(stderr=True, force_terminal=True)


def scan_chain(chain: str, timeframe: str = "24h", limit: int = 20) -> tuple[list[dict], list[dict]]:
    """Scan a single chain. Returns (screener_results, sm_radar_tokens).

    Uses two data sources:
    1. Token screener: price_change + market netflow → market divergence
    2. Smart money netflow: SM-specific flows → SM radar + enhanced signals
    """
    pages = max(1, (limit + 9) // 10)

    console.print(f"  [dim]Fetching token screener for [bold]{chain}[/bold]...[/dim]")
    tokens = nansen.token_screener(chain, timeframe=timeframe, pages=pages)

    console.print(f"  [dim]Fetching smart money netflow for [bold]{chain}[/bold]...[/dim]")
    flows = nansen.smart_money_netflow(chain)

    # Build SM flow lookup: token_address -> flow data
    sm_map = {}
    for f in flows:
        addr = f.get("token_address", "").lower()
        if addr:
            sm_map[addr] = {
                "sm_net_flow_24h": f.get("net_flow_24h_usd", 0),
                "sm_net_flow_7d": f.get("net_flow_7d_usd", 0),
                "sm_trader_count": f.get("trader_count", 0),
                "sm_sectors": f.get("token_sectors", []),
                "sm_market_cap": f.get("market_cap_usd", 0),
            }

    # Build screener token set for overlap detection
    screener_addrs = set()
    results = []

    for token in tokens[:limit]:
        addr = token.get("token_address", "").lower()
        screener_addrs.add(addr)
        mcap = token.get("market_cap_usd") or 0
        if mcap <= 0:
            continue

        price_change = token.get("price_change") or 0
        market_netflow = token.get("netflow") or 0

        # Primary signal: market netflow vs price direction
        strength, phase = score_divergence(market_netflow, price_change, mcap)

        # Check for SM data enhancement
        sm = sm_map.get(addr, {})
        sm_flow = sm.get("sm_net_flow_24h", 0)
        has_sm = bool(sm)

        # If SM data available, compute SM-specific divergence
        sm_strength = 0.0
        sm_phase = ""
        if has_sm and sm_flow != 0:
            sm_strength, sm_phase = score_divergence(sm_flow, price_change, mcap)

        results.append({
            "chain": chain,
            "token_address": token.get("token_address", ""),
            "token_symbol": token.get("token_symbol", "???"),
            "price_usd": token.get("price_usd", 0),
            "price_change": price_change,
            "market_cap": mcap,
            "volume_24h": token.get("volume", 0),
            "market_netflow": market_netflow,
            "sm_net_flow_24h": sm_flow,
            "sm_net_flow_7d": sm.get("sm_net_flow_7d", 0),
            "sm_trader_count": sm.get("sm_trader_count", 0),
            "divergence_strength": strength,
            "phase": phase,
            "sm_strength": sm_strength,
            "sm_phase": sm_phase,
            "has_sm_data": has_sm,
        })

    # Sort by divergence strength descending
    results.sort(key=lambda x: x["divergence_strength"], reverse=True)

    # SM Radar: tokens in netflow but NOT in screener
    sm_radar = []
    for addr, sm in sm_map.items():
        if addr not in screener_addrs:
            # Find the original flow entry for symbol
            for f in flows:
                if f.get("token_address", "").lower() == addr:
                    sm_radar.append({
                        "chain": chain,
                        "token_address": f.get("token_address", ""),
                        "token_symbol": f.get("token_symbol", "???"),
                        "sm_net_flow_24h": sm["sm_net_flow_24h"],
                        "sm_net_flow_7d": sm["sm_net_flow_7d"],
                        "sm_trader_count": sm["sm_trader_count"],
                        "sm_sectors": sm["sm_sectors"],
                        "market_cap": sm["sm_market_cap"],
                    })
                    break

    sm_radar.sort(key=lambda x: abs(x["sm_net_flow_24h"]), reverse=True)
    return results, sm_radar


def scan_multi_chain(
    chains: list[str], timeframe: str = "24h", limit: int = 20
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Scan multiple chains. Returns (chain_results, chain_sm_radar)."""
    all_results = {}
    all_radar = {}
    for chain in chains:
        console.print(f"\n[bold cyan]Scanning {chain.upper()}...[/bold cyan]")
        results, radar = scan_chain(chain, timeframe, limit)
        all_results[chain] = results
        all_radar[chain] = radar
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
    flat.sort(key=lambda x: abs(x["sm_net_flow_24h"]), reverse=True)
    return flat


def count_api_calls(chains: list[str], limit: int = 20) -> int:
    """Estimate the number of API calls for a scan."""
    pages_per_chain = max(1, (limit + 9) // 10)
    # pages for screener + 1-2 pages for netflow
    return len(chains) * (pages_per_chain + 2)


def summarize(results: list[dict], radar: list[dict]) -> dict:
    """Generate summary statistics."""
    divergent = [r for r in results if is_divergent(r["phase"])]
    accumulation = [r for r in results if r["phase"] == "ACCUMULATION"]
    distribution = [r for r in results if r["phase"] == "DISTRIBUTION"]
    with_sm = [r for r in results if r["has_sm_data"]]

    return {
        "total_tokens": len(results),
        "with_sm_data": len(with_sm),
        "sm_radar_tokens": len(radar),
        "divergence_signals": len(divergent),
        "accumulation": len(accumulation),
        "distribution": len(distribution),
    }
