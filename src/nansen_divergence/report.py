"""Generate standalone HTML reports for scan results."""

import html
from datetime import datetime, timezone

from . import __version__


def _escape(val: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(val))


def _fmt_usd_html(val: float) -> str:
    """Format USD value with abbreviation for HTML."""
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


def _fmt_pct_html(val: float) -> str:
    """Format percentage with sign for HTML."""
    pct = val * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


DEXSCREENER_SLUGS = {
    "ethereum": "ethereum",
    "bnb": "bsc",
    "solana": "solana",
    "base": "base",
    "arbitrum": "arbitrum",
    "polygon": "polygon",
    "optimism": "optimism",
    "avalanche": "avalanche",
    "linea": "linea",
}

PHASE_COLORS = {
    "ACCUMULATION": "#2ea043",
    "DISTRIBUTION": "#f85149",
    "MARKUP": "#58a6ff",
    "MARKDOWN": "#d29922",
}

PHASE_DESCRIPTIONS = {
    "ACCUMULATION": "Smart Money buying into price weakness",
    "DISTRIBUTION": "Smart Money exiting into price strength",
    "MARKUP": "Trend confirmed &mdash; both rising",
    "MARKDOWN": "Capitulation &mdash; both falling",
}

CONFIDENCE_COLORS = {
    "HIGH": "#2ea043",
    "MEDIUM": "#d29922",
    "LOW": "#8b949e",
}


def _build_token_card(token: dict) -> str:
    """Build an HTML card for a single token."""
    symbol = _escape(token.get("token_symbol", "???"))
    chain = _escape(token.get("chain", ""))
    price_chg = token.get("price_change", 0)
    mcap = token.get("market_cap", 0)
    phase = token.get("phase", "MARKUP")
    confidence = token.get("confidence", "LOW")
    strength = token.get("divergence_strength", 0)
    narrative = token.get("narrative", "")
    is_new = token.get("is_new", False)

    sm_flow = token.get("sm_net_flow", 0)
    mkt_flow = token.get("market_netflow", 0)
    display_flow = sm_flow if sm_flow != 0 else mkt_flow

    price_color = "#2ea043" if price_chg > 0 else "#f85149"
    flow_color = "#2ea043" if display_flow > 0 else "#f85149"
    conf_color = CONFIDENCE_COLORS.get(confidence, "#8b949e")
    phase_color = PHASE_COLORS.get(phase, "#8b949e")
    bar_pct = int(strength * 100)

    # DexScreener link
    raw_chain = token.get("chain", "")
    dex_slug = DEXSCREENER_SLUGS.get(raw_chain, raw_chain)
    token_addr = _escape(token.get("token_address", ""))
    dex_link = ""
    if token_addr:
        dex_link = f' <a href="https://dexscreener.com/{dex_slug}/{token_addr}" target="_blank" rel="noopener" class="dex-link" title="View on DexScreener">&#x1F4C8;</a>'

    new_badge = ' <span class="new-badge">NEW</span>' if is_new else ""

    card = f"""<div class="token-card">
  <div class="card-header">
    <span class="symbol">{symbol}{dex_link}{new_badge}</span>
    <span class="chain-badge">{chain}</span>
    <span class="conf-badge" style="background:{conf_color}">{_escape(confidence)}</span>
  </div>
  <div class="card-metrics">
    <div class="metric">
      <span class="label">Price</span>
      <span class="value" style="color:{price_color}">{_escape(_fmt_pct_html(price_chg))}</span>
    </div>
    <div class="metric">
      <span class="label">Mkt Cap</span>
      <span class="value">{_escape(_fmt_usd_html(mcap))}</span>
    </div>
    <div class="metric">
      <span class="label">Net Flow</span>
      <span class="value" style="color:{flow_color}">{_escape(_fmt_usd_html(display_flow))}</span>
    </div>
  </div>
  <div class="strength-bar-container">
    <div class="strength-bar" style="width:{bar_pct}%;background:{phase_color}"></div>
  </div>
  <div class="strength-label">{strength:.2f}</div>"""

    if narrative:
        card += f'\n  <div class="narrative">{_escape(narrative)}</div>'

    card += "\n</div>"
    return card


def _build_radar_row(token: dict) -> str:
    """Build a table row for SM radar."""
    symbol = _escape(token.get("token_symbol", "???"))
    chain = _escape(token.get("chain", ""))
    flow_24 = token.get("sm_net_flow_24h", 0)
    flow_7d = token.get("sm_net_flow_7d", 0)
    traders = token.get("sm_trader_count", 0)
    mcap = token.get("market_cap", 0)

    f24_color = "#2ea043" if flow_24 > 0 else "#f85149"
    f7d_color = "#2ea043" if flow_7d > 0 else "#f85149"

    return f"""<tr>
  <td>{chain}</td>
  <td><strong>{symbol}</strong></td>
  <td style="color:{f24_color}">{_escape(_fmt_usd_html(flow_24))}</td>
  <td style="color:{f7d_color}">{_escape(_fmt_usd_html(flow_7d))}</td>
  <td>{traders}</td>
  <td>{_escape(_fmt_usd_html(mcap))}</td>
</tr>"""


def _build_validation_card(v: dict) -> str:
    """Build a card for a signal validation entry."""
    symbol = _escape(v.get("token_symbol", "???"))
    phase = _escape(v.get("phase", ""))
    signal_price = v.get("signal_price", 0)
    current_price = v.get("current_price", 0)
    pct_change = v.get("price_change_pct", 0)
    days_ago = v.get("days_ago", 0)

    color = "#2ea043" if pct_change > 0 else "#f85149"
    direction = "+" if pct_change > 0 else ""

    return f"""<div class="validation-card">
  <span class="phase-tag">{phase}</span> on <strong>{symbol}</strong>
  {days_ago}d ago at ${signal_price:.2f} &rarr; now ${current_price:.2f}
  <span style="color:{color}">({direction}{pct_change:.1f}%)</span>
</div>"""


def generate_html_report(
    results: list[dict],
    radar: list[dict],
    summary: dict,
    chains: list[str],
    timeframe: str,
    validations: list[dict] | None = None,
) -> str:
    """Generate a standalone HTML report string."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    chain_badges = " ".join(f'<span class="chain-badge">{_escape(c.upper())}</span>' for c in chains)

    # Summary stats
    total = summary.get("total_tokens", 0)
    div_signals = summary.get("divergence_signals", 0)
    sm_pct = summary.get("sm_data_pct", 0)
    high = summary.get("confidence_high", 0)
    med = summary.get("confidence_medium", 0)
    low = summary.get("confidence_low", 0)

    # Group tokens by phase
    phase_order = ["ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN"]
    grouped: dict[str, list[dict]] = {p: [] for p in phase_order}
    for r in results:
        phase = r.get("phase", "MARKUP")
        if phase in grouped:
            grouped[phase].append(r)

    for phase in phase_order:
        grouped[phase].sort(key=lambda x: x.get("divergence_strength", 0), reverse=True)

    # Build phase sections
    phase_sections = ""
    for phase in phase_order:
        tokens = grouped[phase]
        if not tokens:
            continue
        color = PHASE_COLORS[phase]
        desc = PHASE_DESCRIPTIONS[phase]
        cards = "\n".join(_build_token_card(t) for t in tokens)
        phase_sections += f"""
<div class="phase-section">
  <h2 style="color:{color}">{_escape(phase)} <span class="phase-desc">&mdash; {desc}</span></h2>
  <div class="token-grid">{cards}</div>
</div>"""

    # SM Radar
    radar_section = ""
    if radar:
        rows = "\n".join(_build_radar_row(t) for t in radar[:15])
        radar_section = f"""
<div class="phase-section radar-section">
  <h2 style="color:#bc8cff">SMART MONEY RADAR <span class="phase-desc">&mdash; SM activity outside top screener</span></h2>
  <table class="radar-table">
    <thead><tr><th>Chain</th><th>Token</th><th>Flow 24h</th><th>Flow 7d</th><th>Traders</th><th>Mkt Cap</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""

    # Validations
    validation_section = ""
    if validations:
        vcards = "\n".join(_build_validation_card(v) for v in validations)
        validation_section = f"""
<div class="phase-section validation-section">
  <h2 style="color:#58a6ff">SIGNAL VALIDATION <span class="phase-desc">&mdash; past signals vs current prices</span></h2>
  {vcards}
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nansen Divergence Report</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;padding:24px;max-width:1200px;margin:0 auto}}
.header{{text-align:center;padding:32px 0;border-bottom:1px solid #21262d}}
.header h1{{color:#f0f6fc;font-size:28px;margin-bottom:8px}}
.header .subtitle{{color:#8b949e;font-size:14px}}
.chain-badge{{display:inline-block;background:#21262d;color:#58a6ff;padding:2px 8px;border-radius:12px;font-size:12px;margin:2px}}
.stats-bar{{display:flex;justify-content:center;gap:32px;padding:20px 0;border-bottom:1px solid #21262d;flex-wrap:wrap}}
.stat{{text-align:center}}
.stat .num{{font-size:24px;font-weight:bold;color:#f0f6fc}}
.stat .label{{font-size:12px;color:#8b949e}}
.phase-section{{margin:32px 0}}
.phase-section h2{{font-size:20px;margin-bottom:16px}}
.phase-desc{{font-weight:normal;font-size:14px;color:#8b949e}}
.token-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}}
.token-card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:16px}}
.card-header{{display:flex;align-items:center;gap:8px;margin-bottom:12px}}
.symbol{{font-size:18px;font-weight:bold;color:#f0f6fc}}
.conf-badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;color:#fff;font-weight:bold}}
.card-metrics{{display:flex;gap:16px;margin-bottom:12px}}
.metric .label{{display:block;font-size:11px;color:#8b949e}}
.metric .value{{font-size:14px;font-weight:600}}
.strength-bar-container{{background:#21262d;border-radius:4px;height:6px;margin-bottom:4px}}
.strength-bar{{height:6px;border-radius:4px;transition:width .3s}}
.strength-label{{font-size:11px;color:#8b949e}}
.narrative{{font-size:12px;color:#8b949e;font-style:italic;margin-top:8px;border-top:1px solid #21262d;padding-top:8px}}
.radar-table{{width:100%;border-collapse:collapse}}
.radar-table th{{text-align:left;padding:8px;border-bottom:1px solid #21262d;color:#bc8cff;font-size:13px}}
.radar-table td{{padding:8px;border-bottom:1px solid #161b22;font-size:13px}}
.radar-section h2{{color:#bc8cff}}
.validation-card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 16px;margin-bottom:8px;font-size:14px}}
.phase-tag{{display:inline-block;background:#21262d;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:bold}}
.new-badge{{display:inline-block;background:#da3633;color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:bold;margin-left:4px;vertical-align:middle}}
.dex-link{{text-decoration:none;font-size:14px;margin-left:4px;vertical-align:middle}}
.dex-link:hover{{opacity:0.7}}
.footer{{text-align:center;padding:32px 0;border-top:1px solid #21262d;margin-top:32px;color:#8b949e;font-size:12px}}
</style>
</head>
<body>
<div class="header">
  <h1>NANSEN DIVERGENCE SCANNER v{_escape(__version__)}</h1>
  <div class="subtitle">Multi-Chain SM Divergence Detection + Wyckoff Phases</div>
  <div style="margin-top:8px">{chain_badges} <span style="color:#8b949e;font-size:12px;margin-left:8px">Timeframe: {_escape(timeframe)}</span></div>
  <div style="color:#8b949e;font-size:12px;margin-top:4px">{_escape(now)}</div>
</div>

<div class="stats-bar">
  <div class="stat"><div class="num">{total}</div><div class="label">Tokens Scanned</div></div>
  <div class="stat"><div class="num" style="color:#2ea043">{div_signals}</div><div class="label">Divergence Signals</div></div>
  <div class="stat"><div class="num">{sm_pct:.0f}%</div><div class="label">SM Coverage</div></div>
  <div class="stat"><div class="num" style="color:#2ea043">{high}</div><div class="label">HIGH</div></div>
  <div class="stat"><div class="num" style="color:#d29922">{med}</div><div class="label">MED</div></div>
  <div class="stat"><div class="num" style="color:#8b949e">{low}</div><div class="label">LOW</div></div>
</div>

{phase_sections}
{radar_section}
{validation_section}

<div class="footer">
  Nansen Divergence v{_escape(__version__)} &mdash; Built with Nansen CLI &mdash; {_escape(now)}
</div>
</body>
</html>"""
