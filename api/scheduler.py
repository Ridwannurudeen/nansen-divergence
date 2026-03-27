"""Background scheduler — runs scans at fixed intervals with credit budget management."""

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger("nansen.scheduler")

DEFAULT_CHAINS = ["ethereum", "bnb", "solana", "base", "arbitrum"]
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))

# Credit budget management
CREDIT_BUDGET = int(os.getenv("CREDIT_BUDGET", "0"))  # 0 = unlimited (no tracking)
CREDITS_PER_SCAN = int(os.getenv("CREDITS_PER_SCAN", "24"))  # estimated cost per scan
_scans_completed = 0


def _maybe_seed_demo(chains: list[str]):
    """Seed cache with demo data if no cached scan exists yet."""
    from api.cache import get_latest_scan, save_cached_scan
    existing = get_latest_scan()
    if existing and existing.get("results"):
        logger.info("Existing cached data preserved — demo data not needed")
        return
    from api.demo import generate_demo_scan
    demo = generate_demo_scan(chains)
    save_cached_scan(demo)
    logger.info(f"Seeded demo data: {len(demo['results'])} tokens across {len(chains)} chains")


def _run_scan():
    global _scans_completed

    # Credit budget check
    if CREDIT_BUDGET > 0:
        used = _scans_completed * CREDITS_PER_SCAN
        remaining = CREDIT_BUDGET - used
        if remaining < CREDITS_PER_SCAN:
            logger.warning(
                f"Credit budget exhausted: {_scans_completed} scans done, "
                f"~{remaining}/{CREDIT_BUDGET} credits remaining — skipping scan"
            )
            return
        logger.info(f"Credit budget: ~{remaining}/{CREDIT_BUDGET} credits remaining (scan #{_scans_completed + 1})")

    from api.cache import save_cached_scan
    from nansen_divergence.divergence import alpha_score
    from nansen_divergence.history import (
        backtest_stats,
        detect_new_tokens,
        init_db,
        save_scan,
        validate_signals,
    )
    from nansen_divergence.scanner import (
        flatten_and_rank,
        flatten_radar,
        scan_multi_chain,
        summarize,
    )

    chains = os.getenv("SCAN_CHAINS", ",".join(DEFAULT_CHAINS)).split(",")
    limit = int(os.getenv("SCAN_LIMIT", "20"))

    logger.info(f"Starting scheduled scan: {chains} (limit={limit})")

    try:
        chain_results, chain_radar = scan_multi_chain(chains, timeframe="24h", limit=limit)
        flat = flatten_and_rank(chain_results)
        radar = flatten_radar(chain_radar)

        try:
            db_conn = init_db()
            new_addrs = detect_new_tokens(flat, conn=db_conn)
            for token in flat:
                if token.get("token_address", "").lower() in new_addrs:
                    token["is_new"] = True
            save_scan(flat, chains, "24h", conn=db_conn)
            validations = validate_signals(flat, lookback_days=7, conn=db_conn)
            bstats = backtest_stats(validations)
            db_conn.close()
        except Exception as e:
            logger.warning(f"History error: {e}")
            validations = []
            bstats = backtest_stats([])

        summary = summarize(flat, radar)

        for r in flat:
            r["alpha_score"] = alpha_score(r.get("divergence_strength", 0))

        if flat:
            save_cached_scan({
                "results": flat,
                "radar": radar,
                "summary": summary,
                "chains": chains,
                "validations": validations,
                "backtest": bstats,
            })
            _scans_completed += 1
            logger.info(f"Scan complete: {summary.get('total_tokens', 0)} tokens (scan #{_scans_completed})")
        else:
            logger.warning("Scan returned 0 tokens (API credits likely exhausted)")
            _maybe_seed_demo(chains)
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        chains = os.getenv("SCAN_CHAINS", ",".join(DEFAULT_CHAINS)).split(",")
        _maybe_seed_demo(chains)


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(_run_scan, "interval", minutes=SCAN_INTERVAL_MINUTES, id="auto_scan")
    scheduler.add_job(_run_scan, "date", id="initial_scan")
    scheduler.start()
    budget_msg = f", credit budget: {CREDIT_BUDGET}" if CREDIT_BUDGET > 0 else ""
    logger.info(f"Scheduler started: scanning every {SCAN_INTERVAL_MINUTES}min{budget_msg}")
    return scheduler
