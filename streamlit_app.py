"""SM Divergence Terminal v4.0 — Streamlit Dashboard."""

import os
import time
from datetime import datetime, timezone

import streamlit as st

st.set_page_config(
    page_title="SM DIVERGENCE TERMINAL",
    page_icon="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f525.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Imports (must come after set_page_config)
# ---------------------------------------------------------------------------
import plotly.graph_objects as go  # noqa: E402

from nansen_divergence import __version__  # noqa: E402
from nansen_divergence.alerts import send_divergence_alerts, send_scan_summary  # noqa: E402
from nansen_divergence.divergence import (  # noqa: E402
    alpha_score,
    is_divergent,
)
from nansen_divergence.history import (  # noqa: E402
    backtest_stats,
    detect_new_tokens,
    get_scan_history,
    init_db,
    save_scan,
    validate_signals,
)
from nansen_divergence.report import DEXSCREENER_SLUGS  # noqa: E402
from nansen_divergence.scanner import (  # noqa: E402
    count_api_credits,
    flatten_and_rank,
    flatten_radar,
    scan_multi_chain,
    summarize,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALL_CHAINS = [
    "ethereum", "bnb", "solana", "base", "arbitrum",
    "polygon", "optimism", "avalanche", "linea",
]

CHAIN_LABELS = {
    "ethereum": "ETH", "bnb": "BNB", "solana": "SOL", "base": "BASE",
    "arbitrum": "ARB", "polygon": "POL", "optimism": "OP",
    "avalanche": "AVAX", "linea": "LNA",
}

PHASE_COLORS = {
    "ACCUMULATION": "#4ade80",
    "DISTRIBUTION": "#f43f5e",
    "MARKUP": "#6366f1",
    "MARKDOWN": "#facc15",
}

PHASE_DESCRIPTIONS = {
    "ACCUMULATION": "SM buying into price weakness",
    "DISTRIBUTION": "SM exiting into price strength",
    "MARKUP": "Trend confirmed -- both rising",
    "MARKDOWN": "Capitulation -- both falling",
}

COL_BG = "#0d0d0d"
COL_SURFACE = "#1a1a1a"
COL_BORDER = "#2a2a2a"
COL_ACCENT = "#f97316"
COL_SECONDARY = "#fb923c"
COL_BULLISH = "#4ade80"
COL_BEARISH = "#f43f5e"
COL_WARNING = "#facc15"
COL_NEUTRAL = "#6366f1"
COL_TEXT = "#d4d4d4"
COL_MUTED = "#737373"


# ---------------------------------------------------------------------------
# CSS Injection
# ---------------------------------------------------------------------------
def _inject_css():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');

/* ---------- Global Overrides ---------- */
:root {
    --bg: #0d0d0d;
    --surface: #1a1a1a;
    --border: #2a2a2a;
    --accent: #f97316;
    --secondary: #fb923c;
    --bullish: #4ade80;
    --bearish: #f43f5e;
    --warning: #facc15;
    --neutral: #6366f1;
    --text: #d4d4d4;
    --muted: #737373;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}

[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}

/* Header / title overrides */
h1, h2, h3, h4, h5, h6 {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    color: var(--text) !important;
}

/* Streamlit metric cards */
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

[data-testid="stMetricLabel"] {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    color: var(--muted) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}

/* Metric container styling */
[data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 16px !important;
}

/* Primary button: vivid orange */
.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #f97316, #fb923c) !important;
    color: #0d0d0d !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-weight: 700 !important;
    border: none !important;
    letter-spacing: 0.05em !important;
}

.stButton > button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, #fb923c, #f97316) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(249, 115, 22, 0.4) !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

[data-testid="stExpander"] summary {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-weight: 600 !important;
}

/* Selectbox, text inputs */
[data-testid="stSelectbox"],
[data-testid="stTextInput"],
[data-testid="stMultiSelect"] {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}

input, select, textarea {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}

/* Divider */
hr {
    border-color: var(--border) !important;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }

/* ---------- Custom Components ---------- */
.chain-pulse-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 16px;
    flex-wrap: wrap;
}

.chain-pulse-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text);
}

.chain-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}

.chain-dot-green { background: #4ade80; box-shadow: 0 0 6px #4ade8080; }
.chain-dot-red { background: #f43f5e; box-shadow: 0 0 6px #f43f5e80; }
.chain-dot-gray { background: #737373; }

.pulse-meta {
    margin-left: auto;
    font-size: 0.7rem;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
}

/* Signal Feed */
.signal-feed {
    max-height: 420px;
    overflow-y: auto;
    padding-right: 4px;
}

.signal-item {
    background: var(--surface);
    border-left: 3px solid var(--border);
    border-radius: 0 6px 6px 0;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
}

.signal-item .sig-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.signal-item .sig-symbol {
    font-weight: 700;
    color: var(--text);
}

.signal-item .sig-chain {
    font-size: 0.7rem;
    color: var(--muted);
}

.signal-item .sig-narrative {
    font-size: 0.72rem;
    color: var(--muted);
    font-style: italic;
}

.signal-item .sig-conf {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 8px;
    font-size: 0.65rem;
    font-weight: 700;
    color: #0d0d0d;
}

.conf-high { background: #4ade80; }
.conf-medium { background: #f97316; }
.conf-low { background: #737373; color: #d4d4d4 !important; }

/* Token table */
.token-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
}

.token-table th {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid var(--border);
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.token-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #1f1f1f;
    vertical-align: middle;
}

.token-table tr:hover td {
    background: #111111;
}

.new-badge {
    display: inline-block;
    background: #f97316;
    color: #0d0d0d;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.6rem;
    font-weight: 700;
    margin-left: 5px;
    vertical-align: middle;
}

.alpha-bar-container {
    width: 80px;
    height: 8px;
    background: #1f1f1f;
    border-radius: 4px;
    overflow: hidden;
    display: inline-block;
    vertical-align: middle;
    margin-right: 6px;
}

.alpha-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s;
}

.alpha-label {
    font-weight: 600;
    font-size: 0.78rem;
    vertical-align: middle;
}

.narrative-row td {
    padding: 4px 12px 12px 12px;
    font-size: 0.72rem;
    color: var(--muted);
    font-style: italic;
    border-bottom: 1px solid var(--border);
}

.dex-link {
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
    font-size: 0.78rem;
}

.dex-link:hover {
    text-decoration: underline;
    color: var(--secondary);
}

/* Deep dive card */
.deep-dive-section {
    background: #111;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 14px 16px;
    margin-top: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
}

.deep-dive-section h4 {
    color: var(--accent) !important;
    font-size: 0.82rem !important;
    margin-bottom: 8px !important;
}

.dd-stat {
    display: inline-block;
    margin-right: 18px;
    margin-bottom: 6px;
}

.dd-stat-label {
    color: var(--muted);
    font-size: 0.68rem;
    text-transform: uppercase;
}

.dd-stat-value {
    font-weight: 600;
    color: var(--text);
}

/* Landing terminal */
.terminal-welcome {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 32px;
    max-width: 720px;
    margin: 40px auto;
    font-family: 'JetBrains Mono', monospace;
}

.terminal-welcome h2 {
    color: var(--accent) !important;
    font-size: 1.4rem !important;
    margin-bottom: 4px !important;
}

.terminal-welcome .version-tag {
    color: var(--muted);
    font-size: 0.78rem;
    margin-bottom: 20px;
}

.terminal-welcome .prompt-line {
    color: var(--accent);
    font-size: 0.85rem;
    margin-bottom: 12px;
}

.terminal-welcome .info-text {
    color: var(--text);
    font-size: 0.82rem;
    line-height: 1.6;
    margin-bottom: 16px;
}

.wyckoff-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    margin-top: 16px;
}

.wyckoff-table th {
    text-align: left;
    padding: 8px 12px;
    border-bottom: 2px solid var(--border);
    color: var(--accent);
    font-size: 0.72rem;
    text-transform: uppercase;
}

.wyckoff-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #1f1f1f;
    color: var(--text);
}

/* Radar table */
.radar-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
}

.radar-table th {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid var(--border);
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.radar-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #1f1f1f;
}

/* History table */
.history-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
}

.history-table th {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid var(--border);
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
}

.history-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #1f1f1f;
}
</style>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


def _alpha_bar_color(score: int) -> str:
    """Return gradient color for alpha score: blue -> orange -> red."""
    if score < 30:
        return "#3b82f6"  # cold blue
    if score < 60:
        return COL_ACCENT  # warm orange
    return COL_BEARISH  # hot red


def _conf_class(conf: str) -> str:
    return {"HIGH": "conf-high", "MEDIUM": "conf-medium"}.get(conf, "conf-low")


# ---------------------------------------------------------------------------
# Chain Pulse Bar
# ---------------------------------------------------------------------------
def _render_chain_pulse(scanned_chains: list[str], results: list[dict]):
    """Render a bar of chain labels with colored status dots."""
    # Determine dominant phase per chain
    chain_phases: dict[str, str] = {}
    for chain in scanned_chains:
        chain_tokens = [r for r in results if r.get("chain") == chain]
        acc = sum(1 for t in chain_tokens if t.get("phase") == "ACCUMULATION")
        dist = sum(1 for t in chain_tokens if t.get("phase") == "DISTRIBUTION")
        if acc > dist:
            chain_phases[chain] = "acc"
        elif dist > acc:
            chain_phases[chain] = "dist"
        else:
            chain_phases[chain] = "acc" if acc > 0 else "neutral"

    now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    credits_est = count_api_credits(scanned_chains, st.session_state.get("limit", 20))

    items_html = ""
    for chain_key in ALL_CHAINS:
        label = CHAIN_LABELS[chain_key]
        if chain_key in scanned_chains:
            phase = chain_phases.get(chain_key, "neutral")
            dot_class = "chain-dot-green" if phase == "acc" else (
                "chain-dot-red" if phase == "dist" else "chain-dot-gray"
            )
        else:
            dot_class = "chain-dot-gray"
        items_html += f'<span class="chain-pulse-item"><span class="chain-dot {dot_class}"></span>{label}</span>'

    st.markdown(
        f"""<div class="chain-pulse-bar">
{items_html}
<span class="pulse-meta">{now} | ~{credits_est} credits</span>
</div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Metric Cards
# ---------------------------------------------------------------------------
def _render_metrics(summary: dict, validations: list[dict]):
    """Render the 6 top metric cards."""
    stats = backtest_stats(validations) if validations else {}
    win_rate = stats.get("win_rate", 0.0) if stats else 0.0

    # Compute avg alpha
    results = st.session_state.get("results", [])
    divergent = [r for r in results if is_divergent(r.get("phase", ""))]
    avg_alpha = 0
    if divergent:
        avg_alpha = round(
            sum(alpha_score(r.get("divergence_strength", 0)) for r in divergent) / len(divergent)
        )

    cols = st.columns(6)
    cols[0].metric("Tokens", summary.get("total_tokens", 0))
    cols[1].metric("Divergence", summary.get("divergence_signals", 0))
    cols[2].metric("Win Rate", f"{win_rate:.0f}%")
    cols[3].metric("HIGH", summary.get("confidence_high", 0))
    cols[4].metric("MEDIUM", summary.get("confidence_medium", 0))
    cols[5].metric("Avg Alpha", avg_alpha)


# ---------------------------------------------------------------------------
# Phase Heatmap (Plotly Treemap)
# ---------------------------------------------------------------------------
def _render_heatmap(results: list[dict]):
    """Render a Plotly treemap of tokens colored by phase."""
    if not results:
        st.info("No tokens to display in heatmap.")
        return

    labels = []
    parents = []
    values = []
    colors = []
    hover_texts = []

    for r in results:
        symbol = r.get("token_symbol", "???")
        phase = r.get("phase", "MARKUP")
        strength = r.get("divergence_strength", 0)
        chain = r.get("chain", "")
        label = CHAIN_LABELS.get(chain, chain.upper())
        alpha = alpha_score(strength)
        price_chg = r.get("price_change", 0)

        labels.append(f"{symbol}")
        parents.append("")
        values.append(max(alpha, 1))
        colors.append(PHASE_COLORS.get(phase, COL_MUTED))
        hover_texts.append(
            f"<b>{symbol}</b> ({label})<br>"
            f"Phase: {phase}<br>"
            f"Alpha: {alpha}<br>"
            f"Price: {_fmt_pct(price_chg)}"
        )

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors, line=dict(color=COL_BG, width=2)),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover_texts,
        textinfo="label+value",
        textfont=dict(family="JetBrains Mono, Fira Code, monospace", size=12, color="#d4d4d4"),
    ))
    fig.update_layout(
        margin=dict(t=4, l=4, r=4, b=4),
        paper_bgcolor=COL_BG,
        plot_bgcolor=COL_SURFACE,
        height=400,
        font=dict(family="JetBrains Mono, Fira Code, monospace"),
    )
    st.plotly_chart(fig, use_container_width=True, key="heatmap")


# ---------------------------------------------------------------------------
# Signal Feed
# ---------------------------------------------------------------------------
def _render_signal_feed(results: list[dict]):
    """Render a scrolling list of HIGH/MEDIUM divergent tokens."""
    divergent = [
        r for r in results
        if is_divergent(r.get("phase", ""))
        and r.get("confidence") in ("HIGH", "MEDIUM")
    ]
    divergent.sort(key=lambda x: x.get("divergence_strength", 0), reverse=True)

    if not divergent:
        st.markdown(
            '<div style="color:#737373;font-family:JetBrains Mono,monospace;font-size:0.82rem;'
            'padding:20px;text-align:center;">No divergence signals detected.</div>',
            unsafe_allow_html=True,
        )
        return

    items_html = ""
    for r in divergent[:20]:
        symbol = r.get("token_symbol", "???")
        chain = CHAIN_LABELS.get(r.get("chain", ""), r.get("chain", "").upper())
        phase = r.get("phase", "")
        conf = r.get("confidence", "LOW")
        narrative = r.get("narrative", "")
        alpha = alpha_score(r.get("divergence_strength", 0))
        border_color = PHASE_COLORS.get(phase, COL_BORDER)

        items_html += f"""<div class="signal-item" style="border-left-color:{border_color}">
  <div class="sig-header">
    <span><span class="sig-symbol">{symbol}</span> <span class="sig-chain">{chain}</span></span>
    <span><span class="sig-conf {_conf_class(conf)}">{conf}</span> <span style="color:{COL_MUTED};font-size:0.7rem;margin-left:4px;">A:{alpha}</span></span>
  </div>
  <div class="sig-narrative">{narrative}</div>
</div>"""

    st.markdown(f'<div class="signal-feed">{items_html}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Phase Token Tables (Custom HTML)
# ---------------------------------------------------------------------------
def _render_token_table(tokens: list[dict], phase: str):
    """Render an HTML token table for a given phase."""
    if not tokens:
        return

    rows_html = ""
    for t in tokens:
        symbol = t.get("token_symbol", "???")
        chain = CHAIN_LABELS.get(t.get("chain", ""), t.get("chain", "").upper())
        price_chg = t.get("price_change", 0)
        price_color = COL_BULLISH if price_chg > 0 else COL_BEARISH

        sm_flow = t.get("sm_net_flow", 0)
        mkt_flow = t.get("market_netflow", 0)
        display_flow = sm_flow if sm_flow != 0 else mkt_flow

        strength = t.get("divergence_strength", 0)
        alpha = alpha_score(strength)
        alpha_color = _alpha_bar_color(alpha)
        conf = t.get("confidence", "LOW")
        narrative = t.get("narrative", "")
        is_new = t.get("is_new", False)

        addr = t.get("token_address", "")
        dex = _dex_link(t.get("chain", ""), addr)

        new_html = '<span class="new-badge">NEW</span>' if is_new else ""

        rows_html += f"""<tr>
  <td><strong style="color:{COL_TEXT}">{symbol}</strong>{new_html}</td>
  <td>{chain}</td>
  <td style="color:{price_color};font-weight:600">{_fmt_pct(price_chg)}</td>
  <td style="color:{'#4ade80' if display_flow > 0 else '#f43f5e'}">{_fmt_usd(display_flow)}</td>
  <td>
    <span class="alpha-bar-container"><span class="alpha-bar" style="width:{alpha}%;background:{alpha_color}"></span></span>
    <span class="alpha-label" style="color:{alpha_color}">{alpha}</span>
  </td>
  <td><span class="sig-conf {_conf_class(conf)}">{conf}</span></td>
  <td><a class="dex-link" href="{dex}" target="_blank" rel="noopener">DexScreener</a></td>
</tr>"""
        if narrative and is_divergent(phase):
            rows_html += f'<tr class="narrative-row"><td colspan="7">{narrative}</td></tr>'

    table_html = f"""<table class="token-table">
<thead><tr>
  <th>Symbol</th><th>Chain</th><th>Price Chg</th><th>Net Flow</th>
  <th>Alpha Score</th><th>Confidence</th><th>Link</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>"""

    st.markdown(table_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Deep Dive Drawer
# ---------------------------------------------------------------------------
def _render_deep_dive(token: dict):
    """Render a deep-dive expander for a single token."""
    symbol = token.get("token_symbol", "???")
    chain = token.get("chain", "")
    addr = token.get("token_address", "")

    with st.expander(f"Deep Dive: {symbol} ({chain})", expanded=False):
        try:
            from nansen_divergence.deep_dive import deep_dive_token

            with st.spinner(f"Fetching deep dive for {symbol}..."):
                dd = deep_dive_token(chain, addr)

            # Flow Intelligence
            fi = dd.get("flow_intelligence", {})
            if fi:
                st.markdown('<h4 style="color:#f97316;font-family:JetBrains Mono,monospace;font-size:0.85rem">Flow Intelligence</h4>', unsafe_allow_html=True)
                fi_items = ""
                if isinstance(fi, dict):
                    for label, data in fi.items():
                        if isinstance(data, dict):
                            flow_val = data.get("net_flow", data.get("value", 0))
                            fi_items += f'<span class="dd-stat"><span class="dd-stat-label">{label}</span><br><span class="dd-stat-value">{_fmt_usd(flow_val)}</span></span>'
                        else:
                            fi_items += f'<span class="dd-stat"><span class="dd-stat-label">{label}</span><br><span class="dd-stat-value">{data}</span></span>'
                if fi_items:
                    st.markdown(f'<div class="deep-dive-section">{fi_items}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="deep-dive-section"><pre style="color:#737373;font-size:0.75rem">{fi}</pre></div>', unsafe_allow_html=True)

            # Nansen Score / Indicators
            indicators = dd.get("indicators", {})
            if indicators:
                st.markdown('<h4 style="color:#f97316;font-family:JetBrains Mono,monospace;font-size:0.85rem">Nansen Score</h4>', unsafe_allow_html=True)
                ind_items = ""
                if isinstance(indicators, dict):
                    for key, val in indicators.items():
                        if isinstance(val, (int, float)):
                            ind_items += f'<span class="dd-stat"><span class="dd-stat-label">{key}</span><br><span class="dd-stat-value">{val}</span></span>'
                        elif isinstance(val, str):
                            ind_items += f'<span class="dd-stat"><span class="dd-stat-label">{key}</span><br><span class="dd-stat-value">{val}</span></span>'
                if ind_items:
                    st.markdown(f'<div class="deep-dive-section">{ind_items}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="deep-dive-section"><pre style="color:#737373;font-size:0.75rem">{indicators}</pre></div>', unsafe_allow_html=True)

            # Wallet Profiles
            wallets = dd.get("wallets", [])
            if wallets:
                st.markdown('<h4 style="color:#f97316;font-family:JetBrains Mono,monospace;font-size:0.85rem">Top Wallet Profiles</h4>', unsafe_allow_html=True)
                for w in wallets:
                    addr_short = w.get("address", "")[:10] + "..."
                    labels = w.get("labels", {})
                    pnl = w.get("pnl_summary", {})
                    label_tags = ""
                    if isinstance(labels, dict):
                        for lbl in labels.get("labels", labels.get("data", [])):
                            if isinstance(lbl, dict):
                                label_tags += f'<span style="background:#2a2a2a;color:#d4d4d4;padding:2px 6px;border-radius:4px;font-size:0.68rem;margin-right:4px">{lbl.get("label", lbl.get("name", ""))}</span>'
                            elif isinstance(lbl, str):
                                label_tags += f'<span style="background:#2a2a2a;color:#d4d4d4;padding:2px 6px;border-radius:4px;font-size:0.68rem;margin-right:4px">{lbl}</span>'
                    elif isinstance(labels, list):
                        for lbl in labels:
                            if isinstance(lbl, str):
                                label_tags += f'<span style="background:#2a2a2a;color:#d4d4d4;padding:2px 6px;border-radius:4px;font-size:0.68rem;margin-right:4px">{lbl}</span>'

                    pnl_text = ""
                    if isinstance(pnl, dict):
                        total_pnl = pnl.get("total_pnl", pnl.get("realized_pnl", 0))
                        if total_pnl:
                            pnl_color = COL_BULLISH if total_pnl > 0 else COL_BEARISH
                            pnl_text = f' <span style="color:{pnl_color};font-weight:600">PnL: {_fmt_usd(total_pnl)}</span>'

                    st.markdown(
                        f'<div class="deep-dive-section" style="margin-bottom:6px">'
                        f'<span style="color:#f97316;font-weight:600">{addr_short}</span>{pnl_text}<br>'
                        f'{label_tags}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        except Exception as e:
            st.warning(f"Deep dive unavailable for {symbol}: {e}")


# ---------------------------------------------------------------------------
# Signal Performance (Backtesting)
# ---------------------------------------------------------------------------
def _render_backtesting(validations: list[dict]):
    """Render backtesting stats and outcome chart."""
    if not validations:
        return

    stats = backtest_stats(validations)
    if stats.get("total_signals", 0) == 0:
        return

    st.markdown(
        '<h3 style="color:#f97316;font-family:JetBrains Mono,monospace;margin-bottom:12px">'
        'SIGNAL PERFORMANCE</h3>',
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    cols[0].metric("Win Rate", f"{stats['win_rate']:.0f}%")
    cols[1].metric("Avg Return", f"{stats['avg_return']:.1f}%")
    cols[2].metric("Best", f"+{stats['best_return']:.1f}%")
    cols[3].metric("Worst", f"{stats['worst_return']:.1f}%")

    # Bar chart of signal outcomes
    symbols = [v.get("token_symbol", "???") for v in validations]
    returns = [v.get("price_change_pct", 0) for v in validations]
    bar_colors = [COL_BULLISH if r > 0 else COL_BEARISH for r in returns]

    fig = go.Figure(go.Bar(
        x=symbols,
        y=returns,
        marker_color=bar_colors,
        hovertemplate="<b>%{x}</b><br>Return: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=COL_BG,
        plot_bgcolor=COL_SURFACE,
        font=dict(family="JetBrains Mono, Fira Code, monospace", color=COL_TEXT),
        xaxis=dict(
            title=None,
            gridcolor=COL_BORDER,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            title="Return %",
            gridcolor=COL_BORDER,
            zerolinecolor=COL_BORDER,
            tickfont=dict(size=10),
        ),
        margin=dict(t=10, l=50, r=20, b=40),
        height=280,
        bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True, key="backtest_chart")


# ---------------------------------------------------------------------------
# SM Radar
# ---------------------------------------------------------------------------
def _render_radar(radar: list[dict]):
    """Render SM Radar table."""
    if not radar:
        return

    rows_html = ""
    for t in radar[:15]:
        symbol = t.get("token_symbol", "???")
        chain = CHAIN_LABELS.get(t.get("chain", ""), t.get("chain", "").upper())
        flow_24 = t.get("sm_net_flow_24h", 0)
        flow_7d = t.get("sm_net_flow_7d", 0)
        traders = t.get("sm_trader_count", 0)
        mcap = t.get("market_cap", 0)
        f24_color = COL_BULLISH if flow_24 > 0 else COL_BEARISH
        f7d_color = COL_BULLISH if flow_7d > 0 else COL_BEARISH

        rows_html += f"""<tr>
  <td><strong>{symbol}</strong></td>
  <td>{chain}</td>
  <td style="color:{f24_color};font-weight:600">{_fmt_usd(flow_24)}</td>
  <td style="color:{f7d_color}">{_fmt_usd(flow_7d)}</td>
  <td>{traders}</td>
  <td>{_fmt_usd(mcap)}</td>
</tr>"""

    table_html = f"""<table class="radar-table">
<thead><tr><th>Token</th><th>Chain</th><th>Flow 24h</th><th>Flow 7d</th><th>Traders</th><th>Mkt Cap</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>"""

    st.markdown(table_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Scan History
# ---------------------------------------------------------------------------
def _render_history():
    """Render scan history table."""
    try:
        scans = get_scan_history(limit=10)
    except Exception:
        scans = []

    if not scans:
        st.markdown(
            '<div style="color:#737373;font-family:JetBrains Mono,monospace;font-size:0.82rem;'
            'padding:12px;">No scan history yet.</div>',
            unsafe_allow_html=True,
        )
        return

    rows_html = ""
    for s in scans:
        ts = str(s.get("timestamp", ""))[:19]
        chains_str = s.get("chains", "")
        tok_count = s.get("token_count", 0)
        div_count = s.get("divergence_count", 0)
        rows_html += f"""<tr>
  <td style="color:{COL_MUTED}">{s.get('id', '')}</td>
  <td>{ts}</td>
  <td>{chains_str}</td>
  <td>{tok_count}</td>
  <td style="color:{COL_ACCENT};font-weight:600">{div_count}</td>
</tr>"""

    table_html = f"""<table class="history-table">
<thead><tr><th>ID</th><th>Time</th><th>Chains</th><th>Tokens</th><th>Divergent</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>"""

    st.markdown(table_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Landing Page
# ---------------------------------------------------------------------------
def _render_landing():
    """Render the terminal-styled welcome / landing page."""
    st.markdown(
        f"""<div class="terminal-welcome">
  <h2>SM DIVERGENCE TERMINAL</h2>
  <div class="version-tag">v{__version__} // Multi-Chain Smart Money Divergence Detection</div>
  <div class="prompt-line">&gt; Detecting where smart money flows disagree with price...</div>
  <div class="info-text">
    This terminal scans 9 chains via the Nansen API, aggregates smart money wallet flows,
    and classifies every token into a Wyckoff phase. Divergence signals highlight where
    institutional wallets are moving against the crowd -- the highest-edge setups in crypto.
  </div>
  <div class="info-text" style="color:#f97316;">
    Select chains in the sidebar, enter your API key, and hit SCAN to begin.
  </div>
  <table class="wyckoff-table">
    <thead>
      <tr><th>Phase</th><th>SM Flow</th><th>Price</th><th>Signal</th></tr>
    </thead>
    <tbody>
      <tr><td style="color:#4ade80;font-weight:700">ACCUMULATION</td><td>Buying</td><td>Falling</td><td>Bullish divergence</td></tr>
      <tr><td style="color:#f43f5e;font-weight:700">DISTRIBUTION</td><td>Selling</td><td>Rising</td><td>Bearish divergence</td></tr>
      <tr><td style="color:#6366f1;font-weight:700">MARKUP</td><td>Buying</td><td>Rising</td><td>Trend confirmed</td></tr>
      <tr><td style="color:#facc15;font-weight:700">MARKDOWN</td><td>Selling</td><td>Falling</td><td>Capitulation</td></tr>
    </tbody>
  </table>
</div>""",
        unsafe_allow_html=True,
    )


# ===========================================================================
# SIDEBAR
# ===========================================================================
_inject_css()

with st.sidebar:
    st.markdown(
        f'<h2 style="color:#f97316;font-family:JetBrains Mono,monospace;margin:0;font-size:1.1rem">'
        f'SM DIVERGENCE v{__version__}</h2>',
        unsafe_allow_html=True,
    )
    st.caption("Smart Money vs Price -- Who's Right?")
    st.divider()

    # Credentials
    st.markdown(
        '<span style="color:#737373;font-family:JetBrains Mono,monospace;font-size:0.72rem;'
        'text-transform:uppercase;letter-spacing:0.05em">Credentials</span>',
        unsafe_allow_html=True,
    )
    api_key = st.text_input("Nansen API Key", type="password", label_visibility="collapsed",
                            placeholder="Nansen API Key")
    if api_key:
        os.environ["NANSEN_API_KEY"] = api_key

    st.divider()

    # Telegram Alerts
    with st.expander("Telegram Alerts (optional)", expanded=False):
        tg_token = st.text_input("Bot Token", type="password", key="tg_token",
                                 placeholder="Bot Token")
        tg_chat = st.text_input("Chat ID", key="tg_chat", placeholder="Chat ID")
        if tg_token:
            os.environ["TELEGRAM_BOT_TOKEN"] = tg_token
        if tg_chat:
            os.environ["TELEGRAM_CHAT_ID"] = tg_chat

    st.divider()

    # Chains (3 columns of checkboxes)
    st.markdown(
        '<span style="color:#737373;font-family:JetBrains Mono,monospace;font-size:0.72rem;'
        'text-transform:uppercase;letter-spacing:0.05em">Chains</span>',
        unsafe_allow_html=True,
    )
    chain_cols = st.columns(3)
    chain_groups = [
        ["ethereum", "solana", "base"],
        ["bnb", "arbitrum", "polygon"],
        ["optimism", "avalanche", "linea"],
    ]
    chain_defaults = {"ethereum", "bnb", "solana", "base", "arbitrum"}
    selected_chains: list[str] = []
    for col_idx, group in enumerate(chain_groups):
        with chain_cols[col_idx]:
            for chain_key in group:
                label = CHAIN_LABELS[chain_key]
                if st.checkbox(label, value=(chain_key in chain_defaults), key=f"chain_{chain_key}"):
                    selected_chains.append(chain_key)

    timeframe = st.selectbox("Timeframe", ["24h", "7d", "30d"], index=0)
    limit = st.slider("Token limit", 5, 50, 20)
    divergence_only = st.checkbox("Divergence only", value=False)
    include_stables = st.checkbox("Include stablecoins", value=False)

    st.divider()

    scan_btn = st.button("SCAN", type="primary", use_container_width=True)

    st.divider()

    # Auto-scan
    auto_scan = st.toggle("Auto-scan", value=False, key="auto_scan_toggle")
    auto_interval = st.selectbox(
        "Interval (min)",
        [1, 2, 5, 10, 15],
        index=2,
        disabled=not auto_scan,
        key="auto_interval",
    )


# ===========================================================================
# Session State
# ===========================================================================
if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.radar = None
    st.session_state.summary = None
    st.session_state.chains = []
    st.session_state.validations = []
    st.session_state.limit = 20


# ===========================================================================
# Scan Logic
# ===========================================================================
if scan_btn and selected_chains:
    st.session_state.limit = limit
    with st.spinner(f"Scanning {len(selected_chains)} chain(s)..."):
        chain_results, chain_radar = scan_multi_chain(
            selected_chains,
            timeframe=timeframe,
            limit=limit,
            include_stables=include_stables,
        )
        flat = flatten_and_rank(chain_results)
        radar = flatten_radar(chain_radar)

        # New token detection + history
        try:
            db_conn = init_db()
            new_addrs = detect_new_tokens(flat, conn=db_conn)
            for token in flat:
                if token.get("token_address", "").lower() in new_addrs:
                    token["is_new"] = True
            save_scan(flat, selected_chains, timeframe, conn=db_conn)
            st.session_state.validations = validate_signals(flat, lookback_days=7, conn=db_conn)
            db_conn.close()
        except Exception:
            st.session_state.validations = []

        # Telegram alerts
        try:
            if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
                send_divergence_alerts(flat)
                send_scan_summary(summarize(flat, radar), selected_chains)
        except Exception:
            pass

        if divergence_only:
            flat = [r for r in flat if r["phase"] in ("ACCUMULATION", "DISTRIBUTION")]

        st.session_state.results = flat
        st.session_state.radar = radar
        st.session_state.summary = summarize(flat, radar)
        st.session_state.chains = selected_chains

elif scan_btn and not selected_chains:
    st.warning("Select at least one chain.")


# ===========================================================================
# Main Display
# ===========================================================================
if st.session_state.results is not None:
    results = st.session_state.results
    summary = st.session_state.summary
    radar = st.session_state.radar
    validations = st.session_state.get("validations", [])
    scanned_chains = st.session_state.chains

    # Chain Pulse Bar
    _render_chain_pulse(scanned_chains, results)

    # Metric Cards
    _render_metrics(summary, validations)

    st.divider()

    # Two-column: Heatmap | Signal Feed
    col_heatmap, col_feed = st.columns([3, 2])
    with col_heatmap:
        st.markdown(
            '<h3 style="color:#f97316;font-family:JetBrains Mono,monospace;font-size:0.95rem;margin-bottom:8px">'
            'PHASE HEATMAP</h3>',
            unsafe_allow_html=True,
        )
        _render_heatmap(results)

    with col_feed:
        st.markdown(
            '<h3 style="color:#f97316;font-family:JetBrains Mono,monospace;font-size:0.95rem;margin-bottom:8px">'
            'SIGNAL FEED</h3>',
            unsafe_allow_html=True,
        )
        _render_signal_feed(results)

    st.divider()

    # Phase Token Tables
    phase_order = ["ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN"]
    grouped: dict[str, list[dict]] = {p: [] for p in phase_order}
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
        count = len(tokens)

        with st.expander(
            f"{phase} -- {desc} ({count} tokens)",
            expanded=is_div,
        ):
            _render_token_table(tokens, phase)

            # Deep-dive drawers for divergent phases
            if is_div:
                div_tokens = [t for t in tokens if t.get("confidence") in ("HIGH", "MEDIUM")]
                for t in div_tokens[:5]:
                    _render_deep_dive(t)

    st.divider()

    # Signal Performance (Backtesting)
    _render_backtesting(validations)

    # SM Radar
    if radar:
        with st.expander(f"SM RADAR ({len(radar)} tokens)", expanded=False):
            _render_radar(radar)

    # Scan History
    with st.expander("SCAN HISTORY", expanded=False):
        _render_history()

    # Auto-scan
    if auto_scan and st.session_state.results is not None:
        interval_seconds = auto_interval * 60
        st.markdown(
            f'<div style="text-align:center;color:#737373;font-family:JetBrains Mono,monospace;'
            f'font-size:0.72rem;margin-top:16px">Auto-scan in {auto_interval} min...</div>',
            unsafe_allow_html=True,
        )
        time.sleep(interval_seconds)
        st.rerun()

else:
    _render_landing()
