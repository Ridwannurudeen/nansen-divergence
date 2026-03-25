"""Background scheduler — runs scans at fixed intervals and caches results."""

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger("nansen.scheduler")

DEFAULT_CHAINS = ["ethereum", "bnb", "solana", "base", "arbitrum"]
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))


def _run_scan():
    from nansen_divergence.divergence import alpha_score
    from nansen_divergence.history import (
        backtest_stats, detect_new_tokens, init_db, save_scan, validate_signals,
    )
    from nansen_divergence.scanner import (
        flatten_and_rank, flatten_radar, scan_multi_chain, summarize,
    )
    from api.cache import save_cached_scan

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

        # Only save if we got actual data — don't overwrite good cached data
        # with empty results (e.g. when API credits are exhausted)
        if flat:
            save_cached_scan({
                "results": flat,
                "radar": radar,
                "summary": summary,
                "chains": chains,
                "validations": validations,
                "backtest": bstats,
            })
            logger.info(f"Scan complete: {summary.get('total_tokens', 0)} tokens")
        else:
            logger.warning("Scan returned 0 tokens — keeping existing cached data")
    except Exception as e:
        logger.error(f"Scan failed: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(_run_scan, "interval", minutes=SCAN_INTERVAL_MINUTES, id="auto_scan")
    scheduler.add_job(_run_scan, "date", id="initial_scan")
    scheduler.start()
    logger.info(f"Scheduler started: scanning every {SCAN_INTERVAL_MINUTES} minutes")
    return scheduler
