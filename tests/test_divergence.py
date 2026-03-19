"""Tests for divergence scoring, stablecoin filter, confidence tiers, and narrative generation."""

from nansen_divergence.divergence import (
    STABLECOINS,
    classify_phase,
    generate_narrative,
    is_divergent,
    is_stablecoin,
    score_divergence,
)


# --- Stablecoin filter ---


class TestStablecoinFilter:
    def test_common_stablecoins_detected(self):
        for sym in ("USDT", "USDC", "DAI", "BUSD", "FDUSD", "PYUSD"):
            assert is_stablecoin(sym), f"{sym} should be stablecoin"

    def test_case_insensitive(self):
        assert is_stablecoin("usdt")
        assert is_stablecoin("Usdc")
        assert is_stablecoin("  DAI  ")

    def test_non_stablecoins(self):
        for sym in ("ETH", "BTC", "AAVE", "LINK", "UNI", "SHIB"):
            assert not is_stablecoin(sym), f"{sym} should NOT be stablecoin"

    def test_stablecoin_set_not_empty(self):
        assert len(STABLECOINS) >= 15


# --- Phase classification ---


class TestPhaseClassification:
    def test_accumulation(self):
        assert classify_phase(sm_flow=1000, price_change=-0.05) == "ACCUMULATION"

    def test_distribution(self):
        assert classify_phase(sm_flow=-1000, price_change=0.05) == "DISTRIBUTION"

    def test_markup(self):
        assert classify_phase(sm_flow=1000, price_change=0.05) == "MARKUP"

    def test_markup_zero_price(self):
        assert classify_phase(sm_flow=1000, price_change=0.0) == "MARKUP"

    def test_markdown(self):
        assert classify_phase(sm_flow=-1000, price_change=-0.05) == "MARKDOWN"

    def test_markdown_zero_flow(self):
        assert classify_phase(sm_flow=0, price_change=-0.05) == "MARKDOWN"

    def test_zero_both(self):
        # sm_flow=0 and price=0 -> MARKUP (>= 0 price branch, but sm_flow not > 0 -> MARKDOWN)
        assert classify_phase(sm_flow=0, price_change=0) == "MARKDOWN"


# --- Scoring ---


class TestScoreDivergence:
    def test_returns_three_tuple(self):
        result = score_divergence(100_000, -0.05, 1_000_000_000)
        assert len(result) == 3
        strength, phase, confidence = result
        assert isinstance(strength, float)
        assert isinstance(phase, str)
        assert isinstance(confidence, str)

    def test_zero_market_cap(self):
        strength, phase, confidence = score_divergence(100, -0.05, 0)
        assert strength == 0.0
        assert phase == "MARKUP"
        assert confidence == "LOW"

    def test_negative_market_cap(self):
        strength, phase, confidence = score_divergence(100, -0.05, -1)
        assert strength == 0.0

    def test_strength_bounded_0_to_1(self):
        # Huge flow, big price move
        strength, _, _ = score_divergence(1_000_000_000, -0.99, 100_000)
        assert 0 <= strength <= 1.0

        # Tiny flow
        strength, _, _ = score_divergence(0.01, -0.001, 1_000_000_000)
        assert 0 <= strength <= 1.0

    def test_strength_not_binary(self):
        """Strength should have smooth distribution, not cluster at 0 or 1."""
        test_cases = [
            (10_000, -0.03, 500_000_000),
            (100_000, -0.05, 1_000_000_000),
            (500_000, -0.10, 2_000_000_000),
            (1_000_000, -0.15, 5_000_000_000),
            (5_000_000, -0.20, 10_000_000_000),
        ]
        strengths = [score_divergence(f, p, m)[0] for f, p, m in test_cases]

        # Should have variety, not all 0 or all 1
        unique = set(strengths)
        assert len(unique) >= 3, f"Strengths too clustered: {strengths}"

        # Should be increasing with larger signals
        assert strengths[-1] > strengths[0], "Larger signals should have higher strength"

    def test_more_wallets_increases_strength(self):
        s1, _, _ = score_divergence(100_000, -0.05, 1_000_000_000, trader_count=0)
        s2, _, _ = score_divergence(100_000, -0.05, 1_000_000_000, trader_count=5)
        s3, _, _ = score_divergence(100_000, -0.05, 1_000_000_000, trader_count=10)
        assert s3 >= s2 >= s1

    def test_conviction_increases_strength(self):
        s1, _, _ = score_divergence(100_000, -0.05, 1_000_000_000, holdings_change=0)
        s2, _, _ = score_divergence(100_000, -0.05, 1_000_000_000, holdings_change=50_000)
        assert s2 >= s1

    def test_conviction_opposing_no_boost(self):
        """Holdings change opposing flow direction should not boost score."""
        s1, _, _ = score_divergence(100_000, -0.05, 1_000_000_000, holdings_change=0)
        s2, _, _ = score_divergence(100_000, -0.05, 1_000_000_000, holdings_change=-50_000)
        assert s2 == s1  # Opposing direction = no conviction boost


# --- Confidence tiers ---


class TestConfidenceTiers:
    def test_high_confidence(self):
        """Strong multi-signal should be HIGH."""
        _, _, conf = score_divergence(
            5_000_000, -0.15, 500_000_000, trader_count=8, holdings_change=200_000
        )
        assert conf == "HIGH"

    def test_low_confidence_weak_signal(self):
        """Weak single signal should be LOW."""
        _, _, conf = score_divergence(100, -0.001, 10_000_000_000, trader_count=0)
        assert conf == "LOW"

    def test_confidence_is_valid_tier(self):
        _, _, conf = score_divergence(50_000, -0.05, 1_000_000_000)
        assert conf in ("HIGH", "MEDIUM", "LOW")


# --- is_divergent ---


class TestIsDivergent:
    def test_accumulation_is_divergent(self):
        assert is_divergent("ACCUMULATION")

    def test_distribution_is_divergent(self):
        assert is_divergent("DISTRIBUTION")

    def test_markup_not_divergent(self):
        assert not is_divergent("MARKUP")

    def test_markdown_not_divergent(self):
        assert not is_divergent("MARKDOWN")


# --- Narrative generation ---


class TestNarrativeGeneration:
    def test_accumulation_narrative(self):
        token = {
            "token_symbol": "AAVE",
            "sm_net_flow": 500_000,
            "sm_trader_count": 5,
            "price_change": -0.08,
            "phase": "ACCUMULATION",
            "sm_buy_volume": 600_000,
            "sm_sell_volume": 100_000,
        }
        narrative = generate_narrative(token)
        assert "AAVE" in narrative
        assert "stealth loading" in narrative
        assert "5 SM wallets" in narrative
        assert "$500K" in narrative

    def test_distribution_narrative(self):
        token = {
            "token_symbol": "SHIB",
            "sm_net_flow": -1_000_000,
            "sm_trader_count": 3,
            "price_change": 0.15,
            "phase": "DISTRIBUTION",
            "sm_buy_volume": 200_000,
            "sm_sell_volume": 1_200_000,
        }
        narrative = generate_narrative(token)
        assert "SHIB" in narrative
        assert "exit liquidity" in narrative
        assert "3 SM wallets" in narrative

    def test_markup_narrative(self):
        token = {
            "token_symbol": "ETH",
            "sm_net_flow": 2_000_000,
            "sm_trader_count": 10,
            "price_change": 0.05,
            "phase": "MARKUP",
        }
        narrative = generate_narrative(token)
        assert "confirming" in narrative

    def test_no_data_empty_narrative(self):
        token = {
            "token_symbol": "XYZ",
            "sm_net_flow": 0,
            "sm_trader_count": 0,
            "price_change": -0.01,
            "phase": "MARKDOWN",
        }
        assert generate_narrative(token) == ""

    def test_singular_wallet(self):
        token = {
            "token_symbol": "UNI",
            "sm_net_flow": 100_000,
            "sm_trader_count": 1,
            "price_change": -0.03,
            "phase": "ACCUMULATION",
        }
        narrative = generate_narrative(token)
        assert "1 SM wallet " in narrative  # singular, no "s"

    def test_million_flow_formatting(self):
        token = {
            "token_symbol": "BTC",
            "sm_net_flow": 5_500_000,
            "sm_trader_count": 2,
            "price_change": -0.10,
            "phase": "ACCUMULATION",
        }
        narrative = generate_narrative(token)
        assert "$5.5M" in narrative
