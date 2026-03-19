"""Tests for HTML report generation."""

from nansen_divergence.report import (
    DEXSCREENER_SLUGS,
    _build_radar_row,
    _build_token_card,
    _build_validation_card,
    _escape,
    _fmt_usd_html,
    generate_html_report,
)

SAMPLE_TOKEN = {
    "chain": "ethereum",
    "token_address": "0xAAA",
    "token_symbol": "AAVE",
    "price_usd": 95.20,
    "price_change": -0.08,
    "market_cap": 1_500_000_000,
    "market_netflow": -200_000,
    "sm_net_flow": 500_000,
    "sm_trader_count": 5,
    "divergence_strength": 0.65,
    "phase": "ACCUMULATION",
    "confidence": "HIGH",
    "narrative": "5 SM wallets bought $500K of AAVE while price dropped 8.0% -- stealth loading",
    "has_sm_data": True,
}

SAMPLE_DISTRIBUTION = {
    "chain": "bnb",
    "token_address": "0xBBB",
    "token_symbol": "SHIB",
    "price_usd": 0.00001,
    "price_change": 0.15,
    "market_cap": 500_000_000,
    "market_netflow": 100_000,
    "sm_net_flow": -1_000_000,
    "sm_trader_count": 3,
    "divergence_strength": 0.45,
    "phase": "DISTRIBUTION",
    "confidence": "MEDIUM",
    "narrative": "3 SM wallets dumped $1.0M into a 15.0% rally -- exit liquidity",
    "has_sm_data": True,
}

SAMPLE_MARKUP = {
    "chain": "solana",
    "token_address": "0xCCC",
    "token_symbol": "SOL",
    "price_usd": 150.0,
    "price_change": 0.05,
    "market_cap": 60_000_000_000,
    "market_netflow": 5_000_000,
    "sm_net_flow": 2_000_000,
    "divergence_strength": 0.30,
    "phase": "MARKUP",
    "confidence": "MEDIUM",
    "narrative": "",
    "has_sm_data": True,
}

SAMPLE_MARKDOWN = {
    "chain": "base",
    "token_address": "0xDDD",
    "token_symbol": "DEGEN",
    "price_usd": 0.001,
    "price_change": -0.20,
    "market_cap": 10_000_000,
    "market_netflow": -50_000,
    "sm_net_flow": -100_000,
    "divergence_strength": 0.20,
    "phase": "MARKDOWN",
    "confidence": "LOW",
    "narrative": "",
    "has_sm_data": True,
}

SAMPLE_SUMMARY = {
    "total_tokens": 40,
    "with_sm_data": 28,
    "sm_data_pct": 70.0,
    "sm_radar_tokens": 12,
    "divergence_signals": 8,
    "accumulation": 5,
    "distribution": 3,
    "confidence_high": 3,
    "confidence_medium": 5,
    "confidence_low": 32,
}

SAMPLE_RADAR = [
    {
        "chain": "ethereum",
        "token_symbol": "PEPE",
        "token_address": "0xPEPE",
        "sm_net_flow_24h": 800_000,
        "sm_net_flow_7d": 2_000_000,
        "sm_trader_count": 12,
        "market_cap": 3_000_000_000,
    },
]


class TestGenerateHtmlReport:
    def test_returns_string(self):
        html = generate_html_report([], [], SAMPLE_SUMMARY, ["ethereum"], "24h")
        assert isinstance(html, str)

    def test_contains_doctype(self):
        html = generate_html_report([], [], SAMPLE_SUMMARY, ["ethereum"], "24h")
        assert "<!DOCTYPE html>" in html

    def test_dark_theme_css(self):
        html = generate_html_report([], [], SAMPLE_SUMMARY, ["ethereum"], "24h")
        assert "#0d1117" in html

    def test_contains_all_four_phases(self):
        results = [SAMPLE_TOKEN, SAMPLE_DISTRIBUTION, SAMPLE_MARKUP, SAMPLE_MARKDOWN]
        html = generate_html_report(results, [], SAMPLE_SUMMARY, ["ethereum", "bnb"], "24h")
        assert "ACCUMULATION" in html
        assert "DISTRIBUTION" in html
        assert "MARKUP" in html
        assert "MARKDOWN" in html

    def test_contains_summary_stats(self):
        html = generate_html_report([], [], SAMPLE_SUMMARY, ["ethereum"], "24h")
        assert "40" in html  # total tokens
        assert "8" in html  # divergence signals
        assert "70%" in html  # SM coverage

    def test_contains_token_data(self):
        html = generate_html_report([SAMPLE_TOKEN], [], SAMPLE_SUMMARY, ["ethereum"], "24h")
        assert "AAVE" in html
        assert "ethereum" in html

    def test_sm_radar_section(self):
        html = generate_html_report([], SAMPLE_RADAR, SAMPLE_SUMMARY, ["ethereum"], "24h")
        assert "SMART MONEY RADAR" in html
        assert "PEPE" in html

    def test_empty_results(self):
        html = generate_html_report([], [], SAMPLE_SUMMARY, [], "24h")
        assert "<!DOCTYPE html>" in html
        assert "Nansen Divergence" in html

    def test_xss_escaping(self):
        malicious = {
            **SAMPLE_TOKEN,
            "token_symbol": '<script>alert("xss")</script>',
            "narrative": '<img onerror="hack()" src=x>',
        }
        html = generate_html_report([malicious], [], SAMPLE_SUMMARY, ["ethereum"], "24h")
        assert "<script>" not in html
        assert 'onerror="hack()"' not in html
        assert "&lt;script&gt;" in html

    def test_validation_section(self):
        validations = [
            {
                "token_symbol": "AAVE",
                "phase": "ACCUMULATION",
                "signal_price": 95.20,
                "current_price": 101.50,
                "price_change_pct": 6.6,
                "days_ago": 2,
            }
        ]
        html = generate_html_report([], [], SAMPLE_SUMMARY, ["ethereum"], "24h", validations=validations)
        assert "SIGNAL VALIDATION" in html
        assert "AAVE" in html
        assert "6.6%" in html

    def test_version_in_report(self):
        from nansen_divergence import __version__
        html = generate_html_report([], [], SAMPLE_SUMMARY, ["ethereum"], "24h")
        assert __version__ in html

    def test_chain_badges_displayed(self):
        html = generate_html_report([], [], SAMPLE_SUMMARY, ["ethereum", "bnb", "solana"], "24h")
        assert "ETHEREUM" in html
        assert "BNB" in html
        assert "SOLANA" in html


class TestHelpers:
    def test_escape_html(self):
        assert _escape("<script>") == "&lt;script&gt;"
        assert _escape('"hello"') == "&quot;hello&quot;"

    def test_fmt_usd_html_millions(self):
        assert _fmt_usd_html(5_500_000) == "+$5.5M"

    def test_fmt_usd_html_thousands(self):
        assert _fmt_usd_html(-50_000) == "-$50.0K"

    def test_fmt_usd_html_zero(self):
        assert _fmt_usd_html(0) == "$0.00"

    def test_build_token_card_contains_data(self):
        card = _build_token_card(SAMPLE_TOKEN)
        assert "AAVE" in card
        assert "ethereum" in card
        assert "HIGH" in card
        assert "0.65" in card

    def test_build_radar_row_contains_data(self):
        row = _build_radar_row(SAMPLE_RADAR[0])
        assert "PEPE" in row
        assert "ethereum" in row

    def test_build_validation_card(self):
        v = {
            "token_symbol": "ETH",
            "phase": "ACCUMULATION",
            "signal_price": 2000.0,
            "current_price": 2200.0,
            "price_change_pct": 10.0,
            "days_ago": 3,
        }
        card = _build_validation_card(v)
        assert "ETH" in card
        assert "ACCUMULATION" in card
        assert "10.0%" in card

    def test_dexscreener_link_in_card(self):
        card = _build_token_card(SAMPLE_TOKEN)
        assert "dexscreener.com/ethereum/0xAAA" in card
        assert 'target="_blank"' in card
        assert "dex-link" in card

    def test_dexscreener_bnb_slug(self):
        token = {**SAMPLE_DISTRIBUTION}
        card = _build_token_card(token)
        assert "dexscreener.com/bsc/0xBBB" in card

    def test_new_badge_css_class(self):
        html = generate_html_report([], [], SAMPLE_SUMMARY, ["ethereum"], "24h")
        assert "new-badge" in html

    def test_new_badge_displayed(self):
        token = {**SAMPLE_TOKEN, "is_new": True}
        card = _build_token_card(token)
        assert "new-badge" in card
        assert "NEW" in card

    def test_no_new_badge_when_not_new(self):
        card = _build_token_card(SAMPLE_TOKEN)
        assert "new-badge" not in card

    def test_dexscreener_slugs_all_chains(self):
        expected = {"ethereum", "bnb", "solana", "base", "arbitrum", "polygon", "optimism", "avalanche", "linea"}
        assert set(DEXSCREENER_SLUGS.keys()) == expected
