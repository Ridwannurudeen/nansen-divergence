"""Background scheduler — runs scans at fixed intervals with credit budget management."""

import logging
import os
import time as _time

from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s")
logger = logging.getLogger("nansen.scheduler")

DEFAULT_CHAINS = ["ethereum", "bnb", "solana", "base", "arbitrum"]
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))

# CLI enrichment settings
CLI_ENRICH_MINUTES = int(os.getenv("CLI_ENRICH_MINUTES", "30"))
CLI_ENRICH_CHAINS = os.getenv("CLI_ENRICH_CHAINS", "ethereum,bnb").split(",")
_last_cli_enrich: float = 0.0  # timestamp of last CLI enrichment

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


def _enrich_with_cli(results: list[dict]) -> list[dict]:
    """Enrich MCP-discovered tokens with real Nansen CLI/REST data.

    Calls token_screener + smart_money_netflow for CLI_ENRICH_CHAINS,
    then overrides volume-proxy fields with real SM data where available.
    Uses REST API directly to avoid CLI binary auth issues in Docker.
    Cost: ~12 credits per run (2 chains × 6 credits).
    """
    from nansen_divergence.divergence import score_divergence
    from nansen_divergence.nansen import (
        InsufficientCreditsError,
        _api_post,
        _get_api_key,
        _notify_log,
        smart_money_netflow,
        token_screener,
    )

    enriched_count = 0

    for chain in CLI_ENRICH_CHAINS:
        chain = chain.strip()
        if not chain:
            continue

        screener_lookup: dict[str, dict] = {}
        netflow_lookup: dict[str, dict] = {}

        # Fetch screener data — try REST first (avoids Docker CLI auth issues)
        try:
            if _get_api_key():
                resp = _api_post("/token-screener", {"chain": chain, "timeframe": "24h", "page": 1})
                data = resp.get("data", resp)
                screener_data = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            else:
                screener_data = token_screener(chain, pages=1)
            for t in screener_data:
                addr = (t.get("token_address") or "").lower()
                if addr:
                    screener_lookup[addr] = t
            logger.info(f"CLI enrichment: {chain} screener returned {len(screener_data)} tokens")
        except InsufficientCreditsError:
            logger.warning(f"CLI enrichment: insufficient credits for {chain} screener — skipping")
            continue
        except Exception as e:
            logger.warning(f"CLI enrichment: {chain} screener failed: {e}")

        # Fetch SM netflow data — try REST first
        try:
            if _get_api_key():
                resp = _api_post("/smart-money/netflow", {"chain": chain, "page": 1})
                data = resp.get("data", resp)
                netflow_data = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            else:
                netflow_data = smart_money_netflow(chain, pages=1)
            for f in netflow_data:
                addr = (f.get("token_address") or "").lower()
                if addr:
                    netflow_lookup[addr] = f
            logger.info(f"CLI enrichment: {chain} netflow returned {len(netflow_data)} tokens")
        except InsufficientCreditsError:
            logger.warning(f"CLI enrichment: insufficient credits for {chain} netflow — skipping")
        except Exception as e:
            logger.warning(f"CLI enrichment: {chain} netflow failed: {e}")

        # Override MCP results with real CLI data
        for r in results:
            if r.get("chain", "").lower() != chain.lower():
                continue
            addr = (r.get("token_address") or "").lower()

            updated = False

            # Override with screener data
            if addr in screener_lookup:
                s = screener_lookup[addr]
                if s.get("market_cap_usd"):
                    r["market_cap"] = s["market_cap_usd"]
                if s.get("price_usd"):
                    r["price_usd"] = s["price_usd"]
                if s.get("netflow"):
                    r["market_netflow"] = s["netflow"]
                updated = True

            # Override with netflow data
            if addr in netflow_lookup:
                nf = netflow_lookup[addr]
                flow_24h = nf.get("net_flow_24h_usd", 0)
                if flow_24h:
                    r["sm_net_flow"] = flow_24h
                updated = True

            if updated:
                # Re-score with real data
                scoring_flow = r.get("sm_net_flow", 0) or r.get("market_netflow", 0)
                strength, phase, confidence = score_divergence(
                    sm_net_flow=scoring_flow,
                    price_change_pct=r.get("price_change", 0),
                    market_cap=r.get("market_cap", 0),
                    trader_count=r.get("sm_trader_count", 0),
                    holdings_change=r.get("sm_holdings_change", 0),
                )
                r["divergence_strength"] = strength
                r["phase"] = phase
                r["confidence"] = confidence
                r["signal_source"] = "nansen_cli"
                enriched_count += 1

    logger.info(f"CLI enrichment complete: {enriched_count} tokens enriched across {CLI_ENRICH_CHAINS}")
    return results


def _prefetch_deep_dives(results: list[dict], scan_data: dict):
    """Pre-fetch deep dive data for top divergent tokens on enriched chains.

    Uses flow_intelligence + who_bought_sold + token_indicators (3 endpoints).
    Stores results in scan_data["prefetched_dives"] for dashboard display.
    """
    from nansen_divergence.nansen import InsufficientCreditsError

    # Pick top 3 tokens from CLI-enriched chains
    candidates = [
        r for r in results
        if r.get("chain", "").lower() in [c.strip().lower() for c in CLI_ENRICH_CHAINS]
        and r.get("divergence_strength", 0) > 0
    ]
    candidates.sort(key=lambda x: x.get("divergence_strength", 0), reverse=True)
    top_tokens = candidates[:2]

    if not top_tokens:
        logger.info("No candidates for pre-built deep dives")
        return

    dives = []
    for token in top_tokens:
        chain = token["chain"]
        addr = token["token_address"]
        symbol = token.get("token_symbol", "???")
        logger.info(f"Pre-fetching deep dive: {symbol} on {chain}")
        dive = {"chain": chain, "token_address": addr, "token_symbol": symbol}
        try:
            from nansen_divergence import nansen
            dive["flow_intelligence"] = nansen.flow_intelligence(chain, addr, days=7)
            dive["who_bought_sold"] = nansen.who_bought_sold(chain, addr, days=7)
            dive["indicators"] = nansen.token_indicators(chain, addr)
            dive["success"] = True
            dives.append(dive)
            logger.info(f"Deep dive complete: {symbol}")
        except InsufficientCreditsError:
            logger.warning(f"Deep dive credits exhausted at {symbol} — stopping")
            dive["success"] = False
            dives.append(dive)
            break
        except Exception as e:
            logger.warning(f"Deep dive failed for {symbol}: {e}")
            dive["success"] = False
            dives.append(dive)

    scan_data["prefetched_dives"] = dives
    logger.info(f"Pre-built deep dives: {len([d for d in dives if d.get('success')])} of {len(dives)} successful")


def _run_mcp_refresh():
    """Run a zero-credit scan using MCP general_search."""
    from api.cache import save_cached_scan
    from nansen_divergence.history import (
        backtest_stats,
        detect_new_tokens,
        init_db,
        save_scan,
        validate_signals,
    )

    logger.info("Starting MCP search refresh (0 credits)")
    try:
        from nansen_divergence.mcp_search import run_mcp_search_scan

        scan_data = run_mcp_search_scan(max_tokens=150)
        if scan_data.get("results"):
            results = scan_data["results"]
            chains = scan_data.get("chains", [])

            # Persist signal history to SQLite for backtesting
            try:
                db_conn = init_db()
                new_addrs = detect_new_tokens(results, conn=db_conn)
                for token in results:
                    if token.get("token_address", "").lower() in new_addrs:
                        token["is_new"] = True
                save_scan(results, chains, "24h", conn=db_conn)
                validations = validate_signals(results, lookback_days=7, conn=db_conn)
                bstats = backtest_stats(validations)
                db_conn.close()
            except Exception as e:
                logger.warning(f"History error: {e}")
                validations = []
                bstats = backtest_stats([])

            scan_data["validations"] = validations
            scan_data["backtest"] = bstats

            # CLI enrichment (rate-limited)
            global _last_cli_enrich
            now = _time.time()
            if CLI_ENRICH_MINUTES > 0 and (now - _last_cli_enrich) >= CLI_ENRICH_MINUTES * 60:
                try:
                    results = _enrich_with_cli(results)
                    # Update summary with CLI-enriched count
                    cli_count = sum(1 for r in results if r.get("signal_source") == "nansen_cli")
                    scan_data["summary"]["cli_enriched_count"] = cli_count
                    # Re-sort by divergence strength after enrichment
                    results.sort(key=lambda x: x.get("divergence_strength", 0), reverse=True)
                    scan_data["results"] = results
                    _last_cli_enrich = now
                    logger.info(f"CLI enrichment applied: {cli_count} tokens enriched")

                    # Pre-fetch deep dives for top tokens (uses 3 more endpoints)
                    try:
                        _prefetch_deep_dives(results, scan_data)
                    except Exception as dive_err:
                        logger.warning(f"Pre-fetch deep dives failed: {dive_err}")
                except Exception as e:
                    logger.warning(f"CLI enrichment failed (graceful fallback): {e}")

            save_cached_scan(scan_data)
            logger.info(
                f"MCP refresh complete: {scan_data['summary']['total_tokens']} tokens, "
                f"{scan_data['summary']['divergence_signals']} divergent, "
                f"{scan_data['summary']['confidence_high']} HIGH across "
                f"{scan_data['summary']['chains_scanned']} chains"
            )
        else:
            logger.warning("MCP refresh returned 0 tokens")
    except Exception as e:
        logger.error(f"MCP refresh failed: {e}")


# MCP refresh interval (separate from credit-based scans)
# Default 5min — general_search is unlimited so we refresh aggressively
MCP_REFRESH_MINUTES = int(os.getenv("MCP_REFRESH_MINUTES", "5"))


def start_scheduler():
    scheduler = BackgroundScheduler()

    # Seed demo data on startup if cache is empty (no scan triggered)
    chains = os.getenv("SCAN_CHAINS", ",".join(DEFAULT_CHAINS)).split(",")
    _maybe_seed_demo(chains)

    # Skip scheduling if interval is 0 (disabled)
    if SCAN_INTERVAL_MINUTES <= 0 and MCP_REFRESH_MINUTES <= 0:
        logger.info("Scheduler disabled (all intervals=0)")
        return scheduler

    # Credit-based scan (if enabled)
    if SCAN_INTERVAL_MINUTES > 0:
        scheduler.add_job(_run_scan, "interval", minutes=SCAN_INTERVAL_MINUTES, id="auto_scan")

    # MCP zero-credit refresh (always enabled unless explicitly disabled)
    if MCP_REFRESH_MINUTES > 0:
        scheduler.add_job(
            _run_mcp_refresh, "interval",
            minutes=MCP_REFRESH_MINUTES, id="mcp_refresh",
        )
        # Run MCP refresh on startup
        scheduler.add_job(_run_mcp_refresh, "date", id="initial_mcp_refresh")
        logger.info(f"MCP refresh enabled: every {MCP_REFRESH_MINUTES}min (0 credits)")

    # Only run initial credit scan if SCAN_ON_STARTUP=1
    if SCAN_INTERVAL_MINUTES > 0 and os.getenv("SCAN_ON_STARTUP", "0") == "1":
        scheduler.add_job(_run_scan, "date", id="initial_scan")

    scheduler.start()
    budget_msg = f", credit budget: {CREDIT_BUDGET}" if CREDIT_BUDGET > 0 else ""
    cli_msg = f", CLI enrichment every {CLI_ENRICH_MINUTES}min for {','.join(CLI_ENRICH_CHAINS)}" if CLI_ENRICH_MINUTES > 0 else ""
    logger.info(f"Scheduler started: credit scan every {SCAN_INTERVAL_MINUTES}min{budget_msg}{cli_msg}")
    return scheduler
