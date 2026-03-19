"""Watch mode: re-scan at intervals with diff detection and alerting."""

import signal
import time

from rich.console import Console

from .alerts import send_divergence_alerts, send_scan_summary
from .history import init_db, save_scan, validate_signals
from .scanner import count_api_calls, flatten_and_rank, flatten_radar, scan_multi_chain, summarize

console = Console(stderr=True, force_terminal=True)

_stop_flag = False


def _signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global _stop_flag
    _stop_flag = True
    console.print("\n[bold yellow]Watch mode stopping...[/bold yellow]")


def run_watch_loop(args):
    """Run the scan-watch loop at the specified interval.

    args should have: chains (str), timeframe, limit, include_stables, divergence_only,
    watch (int minutes), telegram (bool), html (str|None)
    """
    global _stop_flag
    _stop_flag = False

    chains = [c.strip().lower() for c in args.chains.split(",") if c.strip()]
    interval_mins = args.watch
    use_telegram = getattr(args, "telegram", False)
    api_calls_per_scan = count_api_calls(chains, args.limit)

    # Credit warning
    scans_per_hour = 60 // interval_mins if interval_mins > 0 else 1
    credits_hr = api_calls_per_scan * scans_per_hour
    console.print(
        f"\n[bold yellow]WATCH MODE[/bold yellow] — scanning every {interval_mins} min\n"
        f"  ~{api_calls_per_scan} credits/scan x {scans_per_hour}/hr = ~{credits_hr} credits/hr\n"
        f"  Press Ctrl+C to stop\n"
    )

    # Set up signal handler
    prev_handler = signal.signal(signal.SIGINT, _signal_handler)

    previous_signals: set[tuple[str, str]] = set()
    scan_count = 0
    db_conn = init_db()

    try:
        while not _stop_flag:
            scan_count += 1
            console.print(f"\n[bold cyan]--- Watch scan #{scan_count} ---[/bold cyan]")

            try:
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

                # Save to history
                try:
                    save_scan(flat, chains, args.timeframe, conn=db_conn)
                except Exception:
                    pass

                # Validate past signals
                try:
                    validations = validate_signals(flat, lookback_days=7, conn=db_conn)
                except Exception:
                    validations = []

                # Display results
                from .formatter import print_scan_results, print_validation_section

                print_scan_results(
                    flat,
                    radar,
                    chains,
                    args.timeframe,
                    summary=summary_data,
                    api_calls=api_calls_per_scan,
                )

                if validations:
                    print_validation_section(validations)

                # Diff detection: find new HIGH/MED divergent signals
                current_signals: set[tuple[str, str]] = set()
                for r in flat:
                    if r.get("phase") in ("ACCUMULATION", "DISTRIBUTION") and r.get("confidence") in ("HIGH", "MEDIUM"):
                        current_signals.add((r["chain"], r.get("token_address", "")))

                new_signals = current_signals - previous_signals
                if new_signals and scan_count > 1:
                    console.print(f"\n[bold green]+ {len(new_signals)} new signal(s) detected![/bold green]")
                    for r in flat:
                        key = (r["chain"], r.get("token_address", ""))
                        if key in new_signals:
                            console.print(
                                f"  [green]+[/green] {r['phase']} {r['token_symbol']} "
                                f"({r['chain']}) strength={r['divergence_strength']:.2f}"
                            )

                previous_signals = current_signals

                # Telegram alerts
                if use_telegram:
                    try:
                        new_tokens = (
                            [r for r in flat if (r["chain"], r.get("token_address", "")) in new_signals]
                            if scan_count > 1
                            else [
                                r
                                for r in flat
                                if r.get("phase") in ("ACCUMULATION", "DISTRIBUTION")
                                and r.get("confidence") in ("HIGH", "MEDIUM")
                            ]
                        )
                        if new_tokens:
                            sent = send_divergence_alerts(new_tokens)
                            if sent:
                                console.print(f"  [dim]Sent {sent} Telegram alert(s)[/dim]")
                        if scan_count == 1:
                            send_scan_summary(summary_data, chains)
                    except Exception:
                        pass

            except Exception as e:
                console.print(f"[red]Scan error: {e}[/red]")

            if _stop_flag:
                break

            # Sleep with interruptible check
            console.print(f"\n[dim]Next scan in {interval_mins} min...[/dim]")
            sleep_seconds = interval_mins * 60
            for _ in range(sleep_seconds):
                if _stop_flag:
                    break
                time.sleep(1)

    finally:
        db_conn.close()
        signal.signal(signal.SIGINT, prev_handler)
        console.print("[bold]Watch mode stopped.[/bold]")
