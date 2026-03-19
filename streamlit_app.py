"""Nansen Divergence Scanner — Streamlit Web Dashboard."""

import os

import streamlit as st

st.set_page_config(
    page_title="Nansen Divergence Scanner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Imports (after page config)
# ---------------------------------------------------------------------------
from nansen_divergence import __version__  # noqa: E402
from nansen_divergence.divergence import is_divergent  # noqa: E402
from nansen_divergence.report import DEXSCREENER_SLUGS  # noqa: E402
from nansen_divergence.scanner import (  # noqa: E402
    count_api_calls,
    flatten_and_rank,
    flatten_radar,
    scan_multi_chain,
    summarize,
)

ALL_CHAINS = ["ethereum", "bnb", "solana", "base", "arbitrum", "polygon", "optimism", "avalanche", "linea"]

PHASE_COLORS = {
    "ACCUMULATION": "#2ea043",
    "DISTRIBUTION": "#f85149",
    "MARKUP": "#58a6ff",
    "MARKDOWN": "#d29922",
}

PHASE_DESCRIPTIONS = {
    "ACCUMULATION": "SM buying into price weakness",
    "DISTRIBUTION": "SM exiting into price strength",
    "MARKUP": "Trend confirmed — both rising",
    "MARKDOWN": "Capitulation — both falling",
}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title(f"Nansen Divergence v{__version__}")
    st.caption("Multi-Chain SM Divergence Detection + Wyckoff Phases")

    api_key = st.text_input("Nansen API Key (optional)", type="password", help="Set to use REST API instead of CLI")
    if api_key:
        os.environ["NANSEN_API_KEY"] = api_key

    chains = st.multiselect("Chains", ALL_CHAINS, default=["ethereum", "bnb", "solana", "base", "arbitrum"])
    timeframe = st.selectbox("Timeframe", ["24h", "7d", "30d"], index=0)
    limit = st.slider("Token limit per chain", 5, 50, 20)
    divergence_only = st.toggle("Divergence signals only", value=False)
    include_stables = st.toggle("Include stablecoins", value=False)

    scan_btn = st.button("Scan", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.radar = None
    st.session_state.summary = None
    st.session_state.chains = []

if scan_btn and chains:
    with st.spinner(f"Scanning {len(chains)} chain(s)..."):
        chain_results, chain_radar = scan_multi_chain(
            chains,
            timeframe=timeframe,
            limit=limit,
            include_stables=include_stables,
        )
        flat = flatten_and_rank(chain_results)
        radar = flatten_radar(chain_radar)

        # New token detection
        try:
            from nansen_divergence.history import detect_new_tokens, init_db, save_scan, validate_signals

            db_conn = init_db()
            new_addrs = detect_new_tokens(flat, conn=db_conn)
            for token in flat:
                if token.get("token_address", "").lower() in new_addrs:
                    token["is_new"] = True
            save_scan(flat, chains, timeframe, conn=db_conn)
            st.session_state.validations = validate_signals(flat, lookback_days=7, conn=db_conn)
            db_conn.close()
        except Exception:
            st.session_state.validations = []

        if divergence_only:
            flat = [r for r in flat if r["phase"] in ("ACCUMULATION", "DISTRIBUTION")]

        st.session_state.results = flat
        st.session_state.radar = radar
        st.session_state.summary = summarize(flat, radar)
        st.session_state.chains = chains

elif scan_btn and not chains:
    st.warning("Select at least one chain.")


def _dex_link(chain: str, address: str) -> str:
    slug = DEXSCREENER_SLUGS.get(chain, chain)
    return f"https://dexscreener.com/{slug}/{address}"


def _fmt_usd(val: float) -> str:
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
    pct = val * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


# Display results
if st.session_state.results is not None:
    summary = st.session_state.summary
    results = st.session_state.results
    radar = st.session_state.radar

    # Metric cards
    cols = st.columns(6)
    cols[0].metric("Tokens Scanned", summary.get("total_tokens", 0))
    cols[1].metric("Divergence Signals", summary.get("divergence_signals", 0))
    cols[2].metric("SM Coverage", f"{summary.get('sm_data_pct', 0):.0f}%")
    cols[3].metric("HIGH", summary.get("confidence_high", 0))
    cols[4].metric("MEDIUM", summary.get("confidence_medium", 0))
    cols[5].metric("API Calls", f"~{count_api_calls(st.session_state.chains, limit)}")

    st.divider()

    # Phase sections
    phase_order = ["ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN"]
    grouped = {p: [] for p in phase_order}
    for r in results:
        phase = r.get("phase", "MARKUP")
        if phase in grouped:
            grouped[phase].append(r)

    for phase in phase_order:
        grouped[phase].sort(key=lambda x: x.get("divergence_strength", 0), reverse=True)

    for phase in phase_order:
        tokens = grouped[phase]
        if not tokens:
            continue

        color = PHASE_COLORS[phase]
        desc = PHASE_DESCRIPTIONS[phase]
        is_div = is_divergent(phase)
        icon = "🟢" if phase == "ACCUMULATION" else ("🔴" if phase == "DISTRIBUTION" else ("🔵" if phase == "MARKUP" else "🟡"))

        with st.expander(f"{icon} {phase} — {desc} ({len(tokens)} tokens)", expanded=is_div):
            rows = []
            for t in tokens:
                sm_flow = t.get("sm_net_flow", 0)
                mkt_flow = t.get("market_netflow", 0)
                display_flow = sm_flow if sm_flow != 0 else mkt_flow
                new_tag = " 🆕" if t.get("is_new") else ""
                dex = _dex_link(t.get("chain", ""), t.get("token_address", ""))
                rows.append({
                    "Symbol": f"{t.get('token_symbol', '???')}{new_tag}",
                    "Chain": t.get("chain", ""),
                    "Price Chg": _fmt_pct(t.get("price_change", 0)),
                    "Net Flow": _fmt_usd(display_flow),
                    "Confidence": t.get("confidence", "LOW"),
                    "Strength": f"{t.get('divergence_strength', 0):.2f}",
                    "DexScreener": dex,
                })

            st.dataframe(
                rows,
                column_config={
                    "DexScreener": st.column_config.LinkColumn("DexScreener", display_text="View"),
                },
                use_container_width=True,
                hide_index=True,
            )

    # SM Radar
    if radar:
        with st.expander(f"🔮 SMART MONEY RADAR ({len(radar)} tokens)", expanded=False):
            radar_rows = []
            for t in radar[:15]:
                radar_rows.append({
                    "Symbol": t.get("token_symbol", "???"),
                    "Chain": t.get("chain", ""),
                    "Flow 24h": _fmt_usd(t.get("sm_net_flow_24h", 0)),
                    "Flow 7d": _fmt_usd(t.get("sm_net_flow_7d", 0)),
                    "Traders": t.get("sm_trader_count", 0),
                    "Mkt Cap": _fmt_usd(t.get("market_cap", 0)),
                })
            st.dataframe(radar_rows, use_container_width=True, hide_index=True)

    # Signal validation
    validations = st.session_state.get("validations", [])
    if validations:
        with st.expander(f"📈 SIGNAL VALIDATION ({len(validations)} past signals)", expanded=False):
            val_rows = []
            for v in validations:
                pct = v.get("price_change_pct", 0)
                sign = "+" if pct > 0 else ""
                val_rows.append({
                    "Symbol": v.get("token_symbol", "???"),
                    "Phase": v.get("phase", ""),
                    "Signal Price": f"${v.get('signal_price', 0):.2f}",
                    "Current Price": f"${v.get('current_price', 0):.2f}",
                    "Change": f"{sign}{pct:.1f}%",
                    "Days Ago": v.get("days_ago", 0),
                })
            st.dataframe(val_rows, use_container_width=True, hide_index=True)

    # History tab
    try:
        from nansen_divergence.history import get_recent_signals, get_scan_history

        with st.expander("📜 SCAN HISTORY", expanded=False):
            scans = get_scan_history(limit=10)
            if scans:
                st.dataframe(
                    [{
                        "ID": s.get("id", ""),
                        "Time": str(s.get("timestamp", ""))[:19],
                        "Chains": s.get("chains", ""),
                        "Tokens": s.get("token_count", 0),
                        "Divergent": s.get("divergence_count", 0),
                    } for s in scans],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No scan history yet.")
    except Exception:
        pass

else:
    st.markdown("## Nansen Divergence Scanner")
    st.markdown(
        "Multi-chain smart money divergence detection with Wyckoff phase classification. "
        "Select chains and click **Scan** to start."
    )
    st.markdown(f"""
| Phase | SM Flow | Price | Signal |
|-------|---------|-------|--------|
| **ACCUMULATION** | Buying | Falling | Bullish divergence |
| **DISTRIBUTION** | Selling | Rising | Bearish divergence |
| **MARKUP** | Buying | Rising | Trend confirmed |
| **MARKDOWN** | Selling | Falling | Capitulation |
""")
