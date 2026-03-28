"""Divergence scoring algorithm, Wyckoff phase classification, and narrative generation."""

import math

PHASES = {
    "ACCUMULATION": "Smart Money buying into price weakness",
    "DISTRIBUTION": "Smart Money exiting into price strength",
    "MARKUP": "Trend confirmed — both rising",
    "MARKDOWN": "Capitulation — both falling",
}

STABLECOINS = {
    "USDT",
    "USDC",
    "DAI",
    "BUSD",
    "FDUSD",
    "PYUSD",
    "USDE",
    "CRVUSD",
    "GHO",
    "TUSD",
    "FRAX",
    "LUSD",
    "SUSD",
    "MIM",
    "UST",
    "USDP",
    "GUSD",
    "HUSD",
    "USDD",
    "DOLA",
    "USD+",
    "EUSD",
    "CUSD",
    "USDB",
    "USDe",
}


def is_stablecoin(symbol: str) -> bool:
    """Return True if the token symbol matches a known stablecoin."""
    return symbol.upper().strip() in STABLECOINS


def classify_phase(sm_flow: float, price_change: float) -> str:
    """Classify into Wyckoff phase based on flow direction vs price direction."""
    if sm_flow > 0 and price_change < 0:
        return "ACCUMULATION"
    elif sm_flow < 0 and price_change > 0:
        return "DISTRIBUTION"
    elif sm_flow > 0 and price_change >= 0:
        return "MARKUP"
    else:
        return "MARKDOWN"


def score_divergence(
    sm_net_flow: float,
    price_change_pct: float,
    market_cap: float,
    trader_count: int = 0,
    holdings_change: float = 0.0,
) -> tuple[float, str, str]:
    """Score the divergence between smart money flow and price movement.

    Returns (strength 0-1, Wyckoff phase, confidence HIGH/MEDIUM/LOW).

    Multi-factor scoring:
      - flow_score:       log-scaled |flow| relative to market cap
      - price_score:      price movement magnitude (10% move = 0.5)
      - diversity_score:  number of distinct SM wallets
      - conviction_score: holdings change agreeing with flow direction
    """
    if market_cap <= 0:
        return 0.0, "MARKUP", "LOW"

    phase = classify_phase(sm_net_flow, price_change_pct)

    # Flow score: log-scaled magnitude relative to market cap
    abs_flow = abs(sm_net_flow)
    if abs_flow > 0 and market_cap > 1:
        flow_score = math.log10(abs_flow + 1) / math.log10(market_cap)
        flow_score = min(flow_score, 1.0)
    else:
        flow_score = 0.0

    # Price score: movement magnitude (10% = 0.5, 20% = 1.0)
    price_score = min(abs(price_change_pct) * 5, 1.0)

    # Diversity score: more wallets = stronger signal
    diversity_score = min(trader_count / 10, 1.0) if trader_count > 0 else 0.0

    # Conviction score: holdings change direction agrees with flow
    conviction_score = 0.0
    if holdings_change != 0:
        if (holdings_change > 0 and sm_net_flow > 0) or (holdings_change < 0 and sm_net_flow < 0):
            conviction_score = min(abs(holdings_change) / (market_cap * 0.001 + 1), 1.0)

    # Weighted composite: 40% flow + 25% price + 20% diversity + 15% conviction
    strength = 0.40 * flow_score + 0.25 * price_score + 0.20 * diversity_score + 0.15 * conviction_score
    strength = round(min(strength, 1.0), 4)

    # Confidence tier based on signal count and strength
    signal_count = sum(
        [
            flow_score > 0.05,
            price_score > 0.05,
            diversity_score > 0.05,
            conviction_score > 0.05,
        ]
    )

    if signal_count >= 3 and strength >= 0.4:
        confidence = "HIGH"
    elif signal_count >= 2 and strength >= 0.2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return strength, phase, confidence


def is_divergent(phase: str) -> bool:
    """Return True if the phase represents a divergence (accumulation or distribution)."""
    return phase in ("ACCUMULATION", "DISTRIBUTION")


def generate_narrative(token: dict) -> str:
    """Generate a one-line narrative explaining the divergence signal.

    token dict expected keys: token_symbol, sm_net_flow, sm_trader_count,
    price_change, phase, sm_buy_volume, sm_sell_volume, market_netflow
    """
    symbol = token.get("token_symbol", "???")
    flow = token.get("sm_net_flow", 0)
    traders = token.get("sm_trader_count", 0)
    market_nf = token.get("market_netflow", 0)
    price_chg = token.get("price_change", 0)
    phase = token.get("phase", "")

    # Use SM flow if available, fall back to market netflow
    has_sm = flow != 0 or traders > 0
    effective_flow = flow if flow != 0 else market_nf
    abs_flow = abs(effective_flow)
    pct = abs(price_chg * 100)
    is_volume_proxy = token.get("signal_source") == "volume_proxy"

    if abs_flow == 0:
        # Price-only narrative when no flow data available
        if phase == "ACCUMULATION":
            return f"{symbol} dropped {pct:.1f}% — divergence score signals hidden buying pressure"
        elif phase == "DISTRIBUTION":
            return f"{symbol} rallied {pct:.1f}% — divergence score signals distribution risk"
        elif phase == "MARKUP":
            return f"{symbol} up {pct:.1f}% with confirmed momentum"
        elif phase == "MARKDOWN":
            return f"{symbol} down {pct:.1f}% under selling pressure"
        return ""

    # Format flow amount
    if abs_flow >= 1_000_000:
        flow_str = f"${abs_flow / 1_000_000:.1f}M"
    elif abs_flow >= 1_000:
        flow_str = f"${abs_flow / 1_000:.0f}K"
    else:
        flow_str = f"${abs_flow:.0f}"

    if is_volume_proxy:
        vol_ratio = token.get("vol_mcap_ratio", 0)
        if vol_ratio > 0.10:
            source = "Extreme volume activity"
        elif vol_ratio > 0.05:
            source = "High volume analysis"
        else:
            source = "Volume analysis"
    elif has_sm:
        source = f"{traders} SM wallet{'s' if traders != 1 else ''}"
    else:
        source = "Market netflow"

    if is_volume_proxy:
        if phase == "ACCUMULATION":
            return (f"{source}: {flow_str} buy pressure into {symbol} "
                    f"despite {pct:.1f}% price drop — accumulation pattern")
        elif phase == "DISTRIBUTION":
            return f"{source}: {flow_str} sell pressure from {symbol} into {pct:.1f}% rally — distribution pattern"
        elif phase == "MARKUP":
            return f"{source}: {flow_str} net buying in {symbol} confirming {pct:.1f}% uptrend"
        elif phase == "MARKDOWN":
            return f"{source}: {flow_str} net selling in {symbol} accelerating {pct:.1f}% decline"
    else:
        if phase == "ACCUMULATION":
            return f"{source} shows {flow_str} inflow into {symbol} while price dropped {pct:.1f}% -- stealth loading"
        elif phase == "DISTRIBUTION":
            return f"{source} shows {flow_str} outflow from {symbol} into a {pct:.1f}% rally -- exit liquidity"
        elif phase == "MARKUP":
            return f"{source} shows {flow_str} inflow into {symbol} confirming {pct:.1f}% uptrend"
        elif phase == "MARKDOWN":
            return f"{source} shows {flow_str} outflow from {symbol} accelerating {pct:.1f}% decline"
    return ""


def alpha_score(strength: float) -> int:
    """Convert divergence strength (0-1) to Alpha Score (0-100)."""
    return max(0, min(100, round(strength * 100)))
