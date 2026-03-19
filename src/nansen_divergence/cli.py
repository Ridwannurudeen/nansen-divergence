"""CLI entry point for nansen-divergence scanner."""

import argparse
import sys

from . import __version__
from .deep_dive import deep_dive_token
from .formatter import (
    print_auto_dive_results,
    print_deep_dive,
    print_history,
    print_json_output,
    print_scan_results,
    print_validation_section,
)
from .scanner import count_api_calls, flatten_and_rank, flatten_radar, scan_multi_chain, summarize

DEFAULT_CHAINS = ["ethereum", "bnb", "solana", "base", "arbitrum", "polygon", "optimism", "avalanche", "linea"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nansen-divergence",
        description="Multi-chain smart money divergence scanner with Wyckoff phase classification",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # Scan command
    scan_p = sub.add_parser("scan", help="Scan multiple chains for divergence signals")
    scan_p.add_argument(
        "--chains",
        default=",".join(DEFAULT_CHAINS),
        help=f"Comma-separated chains to scan (default: {','.join(DEFAULT_CHAINS)})",
    )
    scan_p.add_argument("--timeframe", default="24h", help="Timeframe for screener (default: 24h)")
    scan_p.add_argument("--limit", type=int, default=20, help="Max tokens per chain (default: 20)")
    scan_p.add_argument(
        "--divergence-only", action="store_true", help="Show only divergent tokens (accumulation/distribution)"
    )
    scan_p.add_argument("--auto-dive", type=int, default=0, metavar="N", help="Auto deep-dive top N divergence signals")
    scan_p.add_argument("--json", action="store_true", help="Output structured JSON instead of Rich tables")
    scan_p.add_argument("--include-stables", action="store_true", help="Include stablecoins (filtered by default)")
    scan_p.add_argument("--html", metavar="FILE", help="Generate HTML report to FILE")
    scan_p.add_argument("--telegram", action="store_true", help="Send Telegram alerts for divergence signals")
    scan_p.add_argument("--watch", type=int, metavar="MINS", help="Re-scan every N minutes (watch mode)")

    # Deep dive command
    deep_p = sub.add_parser("deep", help="Deep dive into a specific token")
    deep_p.add_argument("--chain", required=True, help="Chain to analyze (e.g. ethereum, bnb, solana)")
    deep_p.add_argument("--token", required=True, help="Token address to analyze")
    deep_p.add_argument("--days", type=int, default=30, help="Lookback period in days (default: 30)")
    deep_p.add_argument("--wallets", type=int, default=3, help="Number of wallets to profile (default: 3)")

    # History command
    hist_p = sub.add_parser("history", help="View signal history and past scans")
    hist_p.add_argument("--days", type=int, default=7, help="Lookback period in days (default: 7)")
    hist_p.add_argument("--clear", action="store_true", help="Clear all history data")

    return parser.parse_args(argv)


def cmd_scan(args: argparse.Namespace):
    chains = [c.strip().lower() for c in args.chains.split(",") if c.strip()]
    if not chains:
        print("Error: no chains specified", file=sys.stderr)
        sys.exit(1)

    # Watch mode delegates to the watch loop
    if args.watch:
        from .watch import run_watch_loop

        run_watch_loop(args)
        return

    chain_results, chain_radar = scan_multi_chain(
        chains,
        timeframe=args.timeframe,
        limit=args.limit,
        include_stables=args.include_stables,
    )
    flat = flatten_and_rank(chain_results)
    radar = flatten_radar(chain_radar)

    if args.divergence_only:
        flat = [r for r in flat if r["phase"] in ("ACCUMULATION", "DISTRIBUTION")]

    summary_data = summarize(flat, radar)
    api_call_count = count_api_calls(chains, args.limit)

    # Save to history (never crash scan)
    validations = []
    try:
        from .history import detect_new_tokens, init_db, save_scan, validate_signals

        db_conn = init_db()
        new_addrs = detect_new_tokens(flat, conn=db_conn)
        for token in flat:
            if token.get("token_address", "").lower() in new_addrs:
                token["is_new"] = True
        save_scan(flat, chains, args.timeframe, conn=db_conn)
        validations = validate_signals(flat, lookback_days=7, conn=db_conn)
        db_conn.close()
    except Exception:
        pass

    if args.json:
        print_json_output(flat, radar, summary_data)
    else:
        print_scan_results(flat, radar, chains, args.timeframe, summary=summary_data, api_calls=api_call_count)

        # Signal validation section
        if validations:
            print_validation_section(validations)

    # HTML report
    if args.html:
        try:
            from .report import generate_html_report

            html_content = generate_html_report(
                flat, radar, summary_data, chains, args.timeframe, validations=validations or None
            )
            with open(args.html, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"\nHTML report saved to {args.html}", file=sys.stderr)

            import webbrowser

            webbrowser.open(args.html)
        except Exception as e:
            print(f"HTML report error: {e}", file=sys.stderr)

    # Telegram alerts
    if args.telegram:
        try:
            from .alerts import send_divergence_alerts, send_scan_summary

            sent = send_divergence_alerts(flat)
            if sent:
                print(f"Sent {sent} Telegram alert(s)", file=sys.stderr)
            send_scan_summary(summary_data, chains)
        except Exception:
            pass

    # Auto-dive top N divergence signals
    if args.auto_dive > 0 and not args.json:
        from .divergence import is_divergent

        divergent = [r for r in flat if is_divergent(r["phase"]) and r.get("confidence") in ("HIGH", "MEDIUM")]
        dive_targets = divergent[: args.auto_dive]

        if dive_targets:
            from rich.console import Console

            err_console = Console(stderr=True, force_terminal=True)
            err_console.print(
                f"\n[bold bright_magenta]Auto-diving top {len(dive_targets)} signal(s)...[/bold bright_magenta]"
            )

            for target in dive_targets:
                dive_data = deep_dive_token(
                    target["chain"],
                    target["token_address"],
                    days=30,
                    profile_count=2,
                )
                print_auto_dive_results(dive_data, token_symbol=target["token_symbol"])


def cmd_deep(args: argparse.Namespace):
    data = deep_dive_token(args.chain, args.token, days=args.days, profile_count=args.wallets)
    print_deep_dive(data)


def cmd_history(args: argparse.Namespace):
    from .history import clear_history, get_recent_signals, get_scan_history

    if args.clear:
        clear_history()
        print("History cleared.")
        return

    signals = get_recent_signals(days=args.days)
    scans = get_scan_history(limit=20)
    print_history(signals, scans)


def main(argv: list[str] | None = None):
    args = parse_args(argv)

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "deep":
        cmd_deep(args)
    elif args.command == "history":
        cmd_history(args)


if __name__ == "__main__":
    main()
