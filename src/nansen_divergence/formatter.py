"""Rich terminal output formatting for scan results and deep dives."""

import io
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .divergence import PHASES, is_divergent

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(force_terminal=True, width=110)

PHASE_COLORS = {
    "ACCUMULATION": "green",
    "DISTRIBUTION": "red",
    "MARKUP": "cyan",
    "MARKDOWN": "yellow",
}

PHASE_ICONS = {
    "ACCUMULATION": "[bold green]ACCUMULATION[/bold green]",
    "DISTRIBUTION": "[bold red]DISTRIBUTION[/bold red]",
    "MARKUP": "[bold cyan]MARKUP[/bold cyan]",
    "MARKDOWN": "[bold yellow]MARKDOWN[/bold yellow]",
}


def _fmt_usd(val: float) -> str:
    """Format USD value with sign and abbreviation."""
    sign = "+" if val > 0 else ("-" if val < 0 else "")
    abs_val = abs(val)
    if abs_val >= 1_000_000_000:
        return f"{sign}${abs_val / 1_000_000_000:.1f}B"
    if abs_val >= 1_000_000:
        return f"{sign}${abs_val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{sign}${abs_val / 1_000:.1f}K"
    if abs_val >= 1:
        return f"{sign}${abs_val:.0f}"
    return f"{sign}${abs_val:.2f}"


def _fmt_pct(val: float) -> str:
    """Format percentage with sign."""
    pct = val * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


def _strength_bar(strength: float, width: int = 10) -> str:
    """Create a visual strength bar."""
    filled = int(strength * width)
    empty = width - filled
    return f"{'#' * filled}{'.' * empty} {strength:.2f}"


def print_header(chains: list[str], timeframe: str):
    """Print the main scanner header."""
    chain_str = ", ".join(c.upper() for c in chains)
    console.print()
    console.print(
        Panel(
            f"[bold white]NANSEN DIVERGENCE SCANNER[/bold white]\n"
            f"[dim]Multi-Chain Wyckoff Phase Detection[/dim]\n\n"
            f"[dim]Chains:[/dim] {chain_str}  [dim]|  Timeframe:[/dim] {timeframe}",
            border_style="bright_blue",
            padding=(1, 4),
        )
    )


def print_phase_section(phase: str, tokens: list[dict]):
    """Print a section for one Wyckoff phase."""
    if not tokens:
        return

    color = PHASE_COLORS[phase]
    desc = PHASES[phase]
    icon = PHASE_ICONS[phase]

    console.print(f"\n{icon} -- {desc}")
    console.print(f"[{color}]{'=' * 90}[/{color}]")

    table = Table(show_header=True, header_style=f"bold {color}", box=None, padding=(0, 1))
    table.add_column("Chain", style="dim", width=10)
    table.add_column("Token", width=12)
    table.add_column("Mkt Netflow", justify="right", width=14)
    table.add_column("Price Chg", justify="right", width=10)
    table.add_column("Mkt Cap", justify="right", width=12)
    table.add_column("SM Flow", justify="right", width=12)
    table.add_column("Strength", width=18)

    for t in tokens:
        mkt_flow = t["market_netflow"]
        mkt_color = "green" if mkt_flow > 0 else "red"
        mkt_arrow = " ^" if mkt_flow > 0 else " v"

        price_chg = t["price_change"]
        price_color = "green" if price_chg > 0 else "red"
        price_arrow = " ^" if price_chg > 0 else " v"

        sm_flow = t.get("sm_net_flow_24h", 0)
        if sm_flow != 0:
            sm_str = _fmt_usd(sm_flow)
        else:
            sm_str = "[dim]--[/dim]"

        str_color = color
        bar = _strength_bar(t["divergence_strength"])

        table.add_row(
            t["chain"],
            f"[bold]{t['token_symbol']}[/bold]",
            f"[{mkt_color}]{_fmt_usd(mkt_flow)}{mkt_arrow}[/{mkt_color}]",
            f"[{price_color}]{_fmt_pct(price_chg)}{price_arrow}[/{price_color}]",
            _fmt_usd(t["market_cap"]),
            sm_str,
            f"[{str_color}]{bar}[/{str_color}]",
        )

    console.print(table)


def print_sm_radar(radar_tokens: list[dict]):
    """Print the Smart Money Radar section — tokens with SM activity not in screener."""
    if not radar_tokens:
        return

    console.print(f"\n[bold magenta]SMART MONEY RADAR[/bold magenta] -- Tokens with SM activity outside top screener")
    console.print(f"[magenta]{'=' * 90}[/magenta]")

    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))
    table.add_column("Chain", style="dim", width=10)
    table.add_column("Token", width=12)
    table.add_column("SM Flow 24h", justify="right", width=14)
    table.add_column("SM Flow 7d", justify="right", width=14)
    table.add_column("Traders", justify="right", width=8)
    table.add_column("Mkt Cap", justify="right", width=12)
    table.add_column("Sectors", width=24)

    for t in radar_tokens[:15]:
        flow_24 = t["sm_net_flow_24h"]
        flow_color = "green" if flow_24 > 0 else "red"
        flow_arrow = " ^" if flow_24 > 0 else " v"

        flow_7d = t["sm_net_flow_7d"]
        flow7_color = "green" if flow_7d > 0 else "red"
        flow7_arrow = " ^" if flow_7d > 0 else " v"

        sectors = ", ".join(t.get("sm_sectors", [])[:2]) or "--"

        table.add_row(
            t["chain"],
            f"[bold]{t['token_symbol']}[/bold]",
            f"[{flow_color}]{_fmt_usd(flow_24)}{flow_arrow}[/{flow_color}]",
            f"[{flow7_color}]{_fmt_usd(flow_7d)}{flow7_arrow}[/{flow7_color}]",
            str(t.get("sm_trader_count", 0)),
            _fmt_usd(t.get("market_cap", 0)),
            f"[dim]{sectors}[/dim]",
        )

    console.print(table)


def print_scan_results(results: list[dict], radar: list[dict], chains: list[str], timeframe: str):
    """Print the full scan results, grouped by Wyckoff phase."""
    print_header(chains, timeframe)

    # Group by phase, divergent phases first
    phase_order = ["ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN"]
    grouped = {p: [] for p in phase_order}
    for r in results:
        grouped[r["phase"]].append(r)

    # Sort each group by strength
    for phase in phase_order:
        grouped[phase].sort(key=lambda x: x["divergence_strength"], reverse=True)

    for phase in phase_order:
        tokens = grouped[phase]
        if tokens:
            print_phase_section(phase, tokens)

    # SM Radar section
    print_sm_radar(radar)

    # Summary
    total = len(results)
    divergent = sum(1 for r in results if is_divergent(r["phase"]))
    with_sm = sum(1 for r in results if r.get("has_sm_data"))
    chain_count = len(chains)
    radar_count = len(radar)

    console.print(f"\n[dim]{'=' * 90}[/dim]")
    console.print(
        f"[bold]Summary:[/bold] {chain_count} chains | "
        f"{total} tokens scanned | "
        f"[bold green]{divergent} divergence signals[/bold green] | "
        f"{with_sm} SM-confirmed | "
        f"{radar_count} SM radar"
    )
    console.print()


def print_deep_dive(data: dict, token_symbol: str = ""):
    """Print deep dive results for a single token."""
    chain = data.get("chain", "")
    token = data.get("token", "")
    display = token_symbol or token[:16]

    console.print()
    console.print(
        Panel(
            f"[bold white]DEEP DIVE: {display}[/bold white]\n"
            f"[dim]Chain:[/dim] {chain}  [dim]|  Address:[/dim] {token}",
            border_style="bright_magenta",
            padding=(1, 4),
        )
    )

    # Flow intelligence
    fi = data.get("flow_intelligence", {})
    if fi:
        console.print("\n[bold magenta]Flow Intelligence by Label[/bold magenta]")
        console.print(f"[magenta]{'=' * 60}[/magenta]")
        _print_flow_intelligence(fi)

    # Who bought/sold
    wbs = data.get("who_bought_sold", {})
    if wbs:
        console.print("\n[bold magenta]Who Bought / Sold[/bold magenta]")
        console.print(f"[magenta]{'=' * 60}[/magenta]")
        _print_wbs(wbs)

    # Wallet profiles
    wallets = data.get("wallets", [])
    if wallets:
        console.print(f"\n[bold magenta]Top {len(wallets)} Wallet Profiles[/bold magenta]")
        console.print(f"[magenta]{'=' * 60}[/magenta]")
        for w in wallets:
            _print_wallet_profile(w)

    console.print()


def _print_flow_intelligence(fi: dict):
    """Print flow intelligence data as a structured table."""
    raw = fi.get("data", fi)
    # data can be a list of one dict or a dict directly
    if isinstance(raw, list) and raw:
        fi_data = raw[0]
    elif isinstance(raw, dict):
        fi_data = raw
    else:
        _print_nested_data(fi, indent=2)
        return

    # Extract label categories from the flat dict
    labels = ["public_figure", "top_pnl", "whale", "smart_trader", "exchange", "fresh_wallets"]
    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))
    table.add_column("Label", width=16)
    table.add_column("Net Flow", justify="right", width=14)
    table.add_column("Avg Flow", justify="right", width=14)
    table.add_column("Wallets", justify="right", width=8)

    for label in labels:
        net = fi_data.get(f"{label}_net_flow_usd", 0)
        avg = fi_data.get(f"{label}_avg_flow_usd", 0)
        count = fi_data.get(f"{label}_wallet_count", 0)
        if net is None:
            net = 0
        if avg is None:
            avg = 0

        net_color = "green" if net > 0 else ("red" if net < 0 else "dim")
        display_label = label.replace("_", " ").title()

        table.add_row(
            display_label,
            f"[{net_color}]{_fmt_usd(net)}[/{net_color}]",
            _fmt_usd(avg),
            str(count or 0),
        )

    console.print(table)


def _print_nested_data(data: dict, indent: int = 0):
    """Print nested dict data in a readable format."""
    prefix = " " * indent
    if isinstance(data, dict):
        for key, val in data.items():
            if key in ("pagination",):
                continue
            if isinstance(val, dict):
                console.print(f"{prefix}[bold]{key}:[/bold]")
                _print_nested_data(val, indent + 2)
            elif isinstance(val, list):
                console.print(f"{prefix}[bold]{key}:[/bold]")
                for item in val[:10]:
                    if isinstance(item, dict):
                        _print_dict_row(item, indent + 2)
                    else:
                        console.print(f"{prefix}  {item}")
            else:
                if isinstance(val, float):
                    val = f"{val:,.2f}" if abs(val) > 1 else f"{val:.6f}"
                console.print(f"{prefix}[dim]{key}:[/dim] {val}")


def _print_dict_row(d: dict, indent: int = 0):
    """Print a dict as a compact row."""
    prefix = " " * indent
    parts = []
    for k, v in d.items():
        if k in ("pagination",):
            continue
        if isinstance(v, float):
            v = _fmt_usd(v) if "usd" in k.lower() or "flow" in k.lower() or "volume" in k.lower() else f"{v:.4f}"
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v[:3])
        parts.append(f"[dim]{k}:[/dim] {v}")
    console.print(f"{prefix}{'  |  '.join(parts)}")


def _print_wbs(wbs: dict):
    """Print who-bought-sold data."""
    for side in ("buyers", "sellers", "data"):
        entries = wbs.get(side, [])
        if not isinstance(entries, list) or not entries:
            continue
        label = side.upper()
        console.print(f"\n  [bold]{label}[/bold]")
        for entry in entries[:8]:
            addr = entry.get("address") or entry.get("wallet_address") or entry.get("owner", "???")
            name = entry.get("name") or entry.get("label", "")
            amount = entry.get("amount_usd") or entry.get("usd_amount", 0)
            if isinstance(amount, (int, float)):
                amount = _fmt_usd(amount)
            name_str = f" ({name})" if name else ""
            console.print(f"    {addr[:16]}...{name_str}  {amount}")


def _print_wallet_profile(wallet: dict):
    """Print a single wallet profile."""
    addr = wallet.get("address", "???")
    console.print(f"\n  [bold]{addr}[/bold]")

    labels = wallet.get("labels", {})
    if labels:
        if isinstance(labels, list):
            label_data = labels
        elif isinstance(labels, dict):
            label_data = labels.get("data", labels)
        else:
            label_data = None

        if isinstance(label_data, list):
            label_names = [l.get("label") or l.get("name", "") for l in label_data if isinstance(l, dict)]
            if label_names:
                console.print(f"    [dim]Labels:[/dim] {', '.join(label_names)}")
        elif isinstance(label_data, dict):
            _print_nested_data(label_data, indent=4)

    pnl = wallet.get("pnl_summary", {})
    if pnl:
        if isinstance(pnl, list):
            pnl_data = pnl[0] if pnl else {}
        elif isinstance(pnl, dict):
            pnl_data = pnl.get("data", pnl)
        else:
            pnl_data = {}
        if isinstance(pnl_data, dict):
            realized = pnl_data.get("realized_pnl") or pnl_data.get("total_realized_pnl", 0)
            win_rate = pnl_data.get("win_rate", 0)
            trades = pnl_data.get("total_trades") or pnl_data.get("trade_count", 0)
            if isinstance(realized, (int, float)):
                console.print(f"    [dim]Realized PnL:[/dim] {_fmt_usd(realized)}")
            if win_rate:
                console.print(
                    f"    [dim]Win Rate:[/dim] {win_rate:.1%}"
                    if isinstance(win_rate, float)
                    else f"    [dim]Win Rate:[/dim] {win_rate}"
                )
            if trades:
                console.print(f"    [dim]Trades:[/dim] {trades}")
