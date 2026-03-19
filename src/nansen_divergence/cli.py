"""CLI entry point for nansen-divergence scanner."""

import argparse
import sys

from . import __version__
from .deep_dive import deep_dive_token
from .formatter import print_auto_dive_results, print_deep_dive, print_json_output, print_scan_results
from .scanner import count_api_calls, flatten_and_rank, flatten_radar, scan_multi_chain, summarize

DEFAULT_CHAINS = ["ethereum", "bnb", "solana", "base", "arbitrum"]


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

    # Deep dive command
    deep_p = sub.add_parser("deep", help="Deep dive into a specific token")
    deep_p.add_argument("--chain", required=True, help="Chain to analyze (e.g. ethereum, bnb, solana)")
    deep_p.add_argument("--token", required=True, help="Token address to analyze")
    deep_p.add_argument("--days", type=int, default=30, help="Lookback period in days (default: 30)")
    deep_p.add_argument("--wallets", type=int, default=3, help="Number of wallets to profile (default: 3)")

    return parser.parse_args(argv)


def cmd_scan(args: argparse.Namespace):
    chains = [c.strip().lower() for c in args.chains.split(",") if c.strip()]
    if not chains:
        print("Error: no chains specified", file=sys.stderr)
        sys.exit(1)

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

    if args.json:
        print_json_output(flat, radar, summary_data)
    else:
        print_scan_results(flat, radar, chains, args.timeframe, summary=summary_data, api_calls=api_call_count)

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


def main(argv: list[str] | None = None):
    args = parse_args(argv)

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "deep":
        cmd_deep(args)


if __name__ == "__main__":
    main()
