"""Deep dive into a specific token: flow intelligence, buyers/sellers, wallet profiling."""

from rich.console import Console

from . import nansen

console = Console(stderr=True, force_terminal=True)


def deep_dive_token(chain: str, token: str, days: int = 30, profile_count: int = 3) -> dict:
    """Run a full deep dive on a single token.

    Makes 2 + (profile_count * 2) API calls:
      - flow-intelligence
      - who-bought-sold
      - profiler labels + pnl-summary per top wallet
    """
    result = {"chain": chain, "token": token, "wallets": []}

    # 1. Flow intelligence by label
    console.print(f"  [dim]Fetching flow intelligence for {token[:10]}...[/dim]")
    fi = nansen.flow_intelligence(chain, token, days=days)
    result["flow_intelligence"] = fi

    # 2. Who bought/sold
    console.print(f"  [dim]Fetching who bought/sold for {token[:10]}...[/dim]")
    wbs = nansen.who_bought_sold(chain, token, days=days)
    result["who_bought_sold"] = wbs

    # 3. Profile top wallets
    addresses = _extract_top_addresses(wbs, limit=profile_count)
    for addr in addresses:
        console.print(f"  [dim]Profiling wallet {addr[:10]}...[/dim]")
        labels = nansen.profiler_labels(addr, chain=chain)
        pnl = nansen.profiler_pnl_summary(addr, chain=chain, days=days)
        result["wallets"].append({
            "address": addr,
            "labels": labels,
            "pnl_summary": pnl,
        })

    return result


def _extract_top_addresses(wbs_data: dict, limit: int = 3) -> list[str]:
    """Extract unique wallet addresses from who-bought-sold data."""
    addresses = []
    seen = set()

    # Try various response structures
    for key in ("buyers", "sellers", "data"):
        entries = wbs_data.get(key, [])
        if isinstance(entries, list):
            for entry in entries:
                addr = entry.get("address") or entry.get("wallet_address") or entry.get("owner", "")
                if addr and addr not in seen:
                    seen.add(addr)
                    addresses.append(addr)
                if len(addresses) >= limit:
                    return addresses

    # Fallback: try top-level data list
    if isinstance(wbs_data.get("data"), list):
        for entry in wbs_data["data"]:
            addr = entry.get("address") or entry.get("wallet_address") or entry.get("owner", "")
            if addr and addr not in seen:
                seen.add(addr)
                addresses.append(addr)
            if len(addresses) >= limit:
                return addresses

    return addresses


def count_api_calls(profile_count: int = 3) -> int:
    """Estimate API calls for a deep dive."""
    return 2 + (profile_count * 2)  # flow-intel + wbs + (labels + pnl) per wallet
