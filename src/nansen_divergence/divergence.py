"""Divergence scoring algorithm and Wyckoff phase classification."""

PHASES = {
    "ACCUMULATION": "Smart Money buying into price weakness",
    "DISTRIBUTION": "Smart Money exiting into price strength",
    "MARKUP": "Trend confirmed — both rising",
    "MARKDOWN": "Capitulation — both falling",
}


def score_divergence(sm_netflow_24h: float, price_change_pct: float, market_cap: float) -> tuple[float, str]:
    """Score the divergence between smart money flow and price movement.

    Returns (strength 0-1, Wyckoff phase name).
    """
    if market_cap <= 0:
        return 0.0, "MARKUP"

    # Normalize smart money flow relative to market cap
    sm_signal = sm_netflow_24h / market_cap  # positive = buying, negative = selling

    # Price direction (already a fraction, e.g. -0.04 = -4%)
    price_signal = price_change_pct

    # Classify into Wyckoff phase
    if sm_signal > 0 and price_signal < 0:
        phase = "ACCUMULATION"
    elif sm_signal < 0 and price_signal > 0:
        phase = "DISTRIBUTION"
    elif sm_signal > 0 and price_signal >= 0:
        phase = "MARKUP"
    else:
        phase = "MARKDOWN"

    # Divergence strength: how strongly the signals disagree
    # Scale by 1000 to normalize the typically small sm_signal values
    strength = min(abs(sm_signal) * abs(price_signal) * 10000, 1.0)

    return round(strength, 4), phase


def is_divergent(phase: str) -> bool:
    """Return True if the phase represents a divergence (accumulation or distribution)."""
    return phase in ("ACCUMULATION", "DISTRIBUTION")
