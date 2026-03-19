"""Rich terminal output formatting for scan results and deep dives."""

import io
import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .divergence import PHASES, is_divergent

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(force_terminal=True, width=120)

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

CONFIDENCE_BADGE = {
    "HIGH": "[bold green]HIGH[/bold green]",
    "MEDIUM": "[bold yellow]MED[/bold yellow]",
    "LOW": "[dim]LOW[/dim]",
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
    """Create a visual gradient strength bar with color hint."""
    filled = int(strength * width)
    empty = width - filled
    bar = "#" * filled + "." * empty
    if strength >= 0.6:
        return f"[green]{bar}[/green] {strength:.2f}"
    elif strength >= 0.3:
        return f"[yellow]{bar}[/yellow] {strength:.2f}"
    else:
        return f"[dim]{bar}[/dim] {strength:.2f}"


def print_header(chains: list[str], timeframe: str, api_calls: int = 0):
    """Print the main scanner header."""
    chain_str = ", ".join(c.upper() for c in chains)
    api_str = f"  [dim]|  API calls:[/dim] ~{api_calls}" if api_calls else ""
    console.print()
    console.print(
        Panel(
            f"[bold white]NANSEN DIVERGENCE SCANNER v2.0[/bold white]\n"
            f"[dim]Multi-Chain SM Divergence Detection + Wyckoff Phases[/dim]\n\n"
            f"[dim]Chains:[/dim] {chain_str}  [dim]|  Timeframe:[/dim] {timeframe}"
            f"  [dim]|  CLI commands:[/dim] 9{api_str}",
            border_style="bright_blue",
            padding=(1, 4),
        )
    )


def print_phase_section(phase: str, tokens: list[dict]):
    """Print a section for one Wyckoff phase with confidence badges and narratives."""
    if not tokens:
        return

    color = PHASE_COLORS[phase]
    desc = PHASES[phase]
    icon = PHASE_ICONS[phase]

    console.print(f"\n{icon} -- {desc}")
    console.print(f"[{color}]{'=' * 100}[/{color}]")

    table = Table(show_header=True, header_style=f"bold {color}", box=None, padding=(0, 1))
    table.add_column("Chain", style="dim", width=9)
    table.add_column("Token", width=10)
    table.add_column("Price Chg", justify="right", width=9)
    table.add_column("Mkt Cap", justify="right", width=10)
    table.add_column("Net Flow", justify="right", width=14)
    table.add_column("SM Detail", justify="right", width=16)
    table.add_column("Conf", width=6)
    table.add_column("Strength", width=18)

    for t in tokens:
        price_chg = t["price_change"]
        price_color = "green" if price_chg > 0 else "red"
        price_arrow = " ^" if price_chg > 0 else " v"

        # Show the scoring flow: SM trade flow > SM holdings > market netflow
        sm_flow = t.get("sm_net_flow", 0)
        mkt_flow = t.get("market_netflow", 0)
        hold_val = t.get("sm_holdings_value", 0)
        display_flow = sm_flow if sm_flow != 0 else mkt_flow
        flow_color = "green" if display_flow > 0 else "red"
        flow_suffix = ""
        if sm_flow != 0:
            flow_suffix = " SM"
        elif hold_val > 0:
            flow_suffix = " H"
        flow_str = f"[{flow_color}]{_fmt_usd(display_flow)}[/{flow_color}]{flow_suffix}"

        # SM detail: buy/sell if available, else holdings value, else --
        sm_buy = t.get("sm_buy_volume", 0)
        sm_sell = t.get("sm_sell_volume", 0)
        if sm_buy or sm_sell:
            detail_str = f"[green]{_fmt_usd(sm_buy)}[/green]/[red]{_fmt_usd(sm_sell)}[/red]"
        elif hold_val > 0:
            hold_chg = t.get("sm_holdings_change", 0)
            chg_color = "green" if hold_chg >= 0 else "red"
            detail_str = f"Hold [{chg_color}]{_fmt_usd(hold_val)}[/{chg_color}]"
        else:
            detail_str = "[dim]--[/dim]"

        conf = t.get("confidence", "LOW")
        conf_badge = CONFIDENCE_BADGE.get(conf, "[dim]LOW[/dim]")

        bar = _strength_bar(t["divergence_strength"])

        table.add_row(
            t["chain"],
            f"[bold]{t['token_symbol']}[/bold]",
            f"[{price_color}]{_fmt_pct(price_chg)}{price_arrow}[/{price_color}]",
            _fmt_usd(t["market_cap"]),
            flow_str,
            detail_str,
            conf_badge,
            bar,
        )

    console.print(table)

    # Print narratives for HIGH/MEDIUM confidence divergent tokens
    if is_divergent(phase):
        narratives = [
            t["narrative"] for t in tokens if t.get("narrative") and t.get("confidence") in ("HIGH", "MEDIUM")
        ]
        if narratives:
            console.print()
            for n in narratives:
                console.print(f"  [dim italic]{n}[/dim italic]")


def print_sm_radar(radar_tokens: list[dict]):
    """Print the Smart Money Radar section -- tokens with SM activity not in screener."""
    if not radar_tokens:
        return

    console.print("\n[bold magenta]SMART MONEY RADAR[/bold magenta] -- Tokens with SM activity outside top screener")
    console.print(f"[magenta]{'=' * 100}[/magenta]")

    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))
    table.add_column("Chain", style="dim", width=9)
    table.add_column("Token", width=10)
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


def print_summary_panel(summary: dict, chains: list[str], api_calls: int = 0):
    """Print a summary panel with SM data coverage and confidence breakdown."""
    sm_pct = summary.get("sm_data_pct", 0)
    high = summary.get("confidence_high", 0)
    med = summary.get("confidence_medium", 0)
    low = summary.get("confidence_low", 0)

    coverage_color = "green" if sm_pct >= 50 else ("yellow" if sm_pct >= 25 else "red")

    console.print(f"\n[dim]{'=' * 100}[/dim]")
    console.print(
        Panel(
            f"[bold]Summary[/bold]\n\n"
            f"  {len(chains)} chains  |  {summary['total_tokens']} tokens scanned  |  "
            f"[bold green]{summary['divergence_signals']} divergence signals[/bold green]  |  "
            f"{summary['sm_radar_tokens']} SM radar\n"
            f"  SM data coverage: [{coverage_color}]{sm_pct:.0f}%[/{coverage_color}] "
            f"({summary['with_sm_data']}/{summary['total_tokens']})\n"
            f"  Confidence: [bold green]{high} HIGH[/bold green]  "
            f"[bold yellow]{med} MED[/bold yellow]  "
            f"[dim]{low} LOW[/dim]\n"
            f"  Accumulation: [green]{summary['accumulation']}[/green]  |  "
            f"Distribution: [red]{summary['distribution']}[/red]"
            + (f"\n  API calls used: ~{api_calls}" if api_calls else ""),
            border_style="dim",
            padding=(0, 2),
        )
    )
    console.print()


def print_scan_results(
    results: list[dict],
    radar: list[dict],
    chains: list[str],
    timeframe: str,
    summary: dict | None = None,
    api_calls: int = 0,
):
    """Print the full scan results, grouped by Wyckoff phase."""
    print_header(chains, timeframe, api_calls=api_calls)

    # Group by phase, divergent phases first
    phase_order = ["ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN"]
    grouped: dict[str, list[dict]] = {p: [] for p in phase_order}
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

    # Summary panel
    if summary:
        print_summary_panel(summary, chains, api_calls=api_calls)
    else:
        # Legacy summary
        total = len(results)
        divergent = sum(1 for r in results if is_divergent(r["phase"]))
        with_sm = sum(1 for r in results if r.get("has_sm_data"))
        radar_count = len(radar)

        console.print(f"\n[dim]{'=' * 100}[/dim]")
        console.print(
            f"[bold]Summary:[/bold] {len(chains)} chains | "
            f"{total} tokens scanned | "
            f"[bold green]{divergent} divergence signals[/bold green] | "
            f"{with_sm} SM-confirmed | "
            f"{radar_count} SM radar"
        )
        console.print()


def print_json_output(results: list[dict], radar: list[dict], summary: dict):
    """Print structured JSON output for --json flag."""
    output = {
        "version": "2.0.0",
        "summary": summary,
        "tokens": results,
        "sm_radar": radar,
    }
    print(json.dumps(output, indent=2, default=str))


def print_auto_dive_results(dive_data: dict, token_symbol: str = ""):
    """Print inline deep-dive results within scan output."""
    chain = dive_data.get("chain", "")
    token = dive_data.get("token", "")
    display = token_symbol or token[:16]

    console.print(f"\n  [bold bright_magenta]>> AUTO-DIVE: {display} ({chain})[/bold bright_magenta]")
    console.print(f"  [magenta]{'- ' * 40}[/magenta]")

    # Flow intelligence summary
    fi = dive_data.get("flow_intelligence", {})
    if fi:
        _print_flow_intelligence(fi, indent=4)

    # Indicators (Nansen Score)
    indicators = dive_data.get("indicators", {})
    if indicators:
        _print_indicators(indicators, indent=4)

    # Top wallets summary
    wallets = dive_data.get("wallets", [])
    if wallets:
        console.print("    [bold]Top Wallets:[/bold]")
        for w in wallets:
            addr = w.get("address", "???")
            labels = w.get("labels", {})
            if isinstance(labels, dict):
                label_data = labels.get("data", [])
            elif isinstance(labels, list):
                label_data = labels
            else:
                label_data = []

            label_names = []
            if isinstance(label_data, list):
                label_names = [lb.get("label") or lb.get("name", "") for lb in label_data if isinstance(lb, dict)]

            label_str = f" ({', '.join(label_names[:3])})" if label_names else ""
            console.print(f"      {addr[:12]}...{label_str}")


def print_deep_dive(data: dict, token_symbol: str = ""):
    """Print deep dive results for a single token."""
    chain = data.get("chain", "")
    token = data.get("token", "")
    display = token_symbol or token[:16]

    console.print()
    console.print(
        Panel(
            f"[bold white]DEEP DIVE: {display}[/bold white]\n[dim]Chain:[/dim] {chain}  [dim]|  Address:[/dim] {token}",
            border_style="bright_magenta",
            padding=(1, 4),
        )
    )

    # Indicators (Nansen Score)
    indicators = data.get("indicators", {})
    if indicators:
        console.print("\n[bold magenta]Nansen Score / Indicators[/bold magenta]")
        console.print(f"[magenta]{'=' * 60}[/magenta]")
        _print_indicators(indicators)

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


def _print_indicators(indicators: dict, indent: int = 0):
    """Print Nansen Score / token indicators."""
    prefix = " " * indent
    raw = indicators.get("data", indicators)

    if isinstance(raw, list) and raw:
        raw = raw[0]
    if not isinstance(raw, dict):
        console.print(f"{prefix}[dim]No indicator data available[/dim]")
        return

    score = raw.get("nansen_score") or raw.get("score")
    risk = raw.get("risk_score") or raw.get("risk")
    reward = raw.get("reward_score") or raw.get("reward")

    parts = []
    if score is not None:
        parts.append(f"[bold]Nansen Score:[/bold] {score}")
    if risk is not None:
        risk_color = "red" if (isinstance(risk, (int, float)) and risk >= 7) else "yellow"
        parts.append(f"[bold]Risk:[/bold] [{risk_color}]{risk}[/{risk_color}]")
    if reward is not None:
        reward_color = "green" if (isinstance(reward, (int, float)) and reward >= 7) else "dim"
        parts.append(f"[bold]Reward:[/bold] [{reward_color}]{reward}[/{reward_color}]")

    if parts:
        console.print(f"{prefix}{'  |  '.join(parts)}")
    else:
        # Fallback: print all keys
        for k, v in raw.items():
            if k not in ("pagination",):
                console.print(f"{prefix}[dim]{k}:[/dim] {v}")


def _print_flow_intelligence(fi: dict, indent: int = 0):
    """Print flow intelligence data as a structured table."""
    prefix = " " * indent
    raw = fi.get("data", fi)
    if isinstance(raw, list) and raw:
        fi_data = raw[0]
    elif isinstance(raw, dict):
        fi_data = raw
    else:
        _print_nested_data(fi, indent=indent)
        return

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

    if prefix:
        # Indent the whole table by printing with prefix
        with console.capture() as capture:
            console.print(table)
        for line in capture.get().splitlines():
            console.print(f"{prefix}{line}")
    else:
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
            label_names = [lb.get("label") or lb.get("name", "") for lb in label_data if isinstance(lb, dict)]
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
