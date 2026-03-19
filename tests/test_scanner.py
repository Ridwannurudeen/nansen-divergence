"""Tests for scanner data aggregation: dex-trade aggregation and holdings matching."""

from nansen_divergence.scanner import aggregate_sm_trades, match_holdings


# --- DEX trade aggregation (swap-pair format) ---


class TestAggregateSmTradesSwapPair:
    """Tests using the real Nansen dex-trades API swap-pair format."""

    def test_buy_when_token_is_bought(self):
        trades = [
            {
                "token_bought_address": "0xAAA",
                "token_sold_address": "0xBNB",
                "trade_value_usd": 1000,
                "trader_address": "w1",
                "trader_address_label": "whale",
            },
        ]
        result = aggregate_sm_trades(trades, {"0xaaa"})

        assert "0xaaa" in result
        data = result["0xaaa"]
        assert data["buy_volume"] == 1000
        assert data["sell_volume"] == 0
        assert data["net_flow"] == 1000
        assert data["trader_count"] == 1

    def test_sell_when_token_is_sold(self):
        trades = [
            {
                "token_bought_address": "0xBNB",
                "token_sold_address": "0xAAA",
                "trade_value_usd": 5000,
                "trader_address": "w1",
            },
        ]
        result = aggregate_sm_trades(trades, {"0xaaa"})

        data = result["0xaaa"]
        assert data["sell_volume"] == 5000
        assert data["net_flow"] == -5000

    def test_both_sides_match_targets(self):
        """A swap between two target tokens creates a buy for one and sell for the other."""
        trades = [
            {
                "token_bought_address": "0xAAA",
                "token_sold_address": "0xBBB",
                "trade_value_usd": 2000,
                "trader_address": "w1",
            },
        ]
        result = aggregate_sm_trades(trades, {"0xaaa", "0xbbb"})

        assert result["0xaaa"]["buy_volume"] == 2000
        assert result["0xaaa"]["net_flow"] == 2000
        assert result["0xbbb"]["sell_volume"] == 2000
        assert result["0xbbb"]["net_flow"] == -2000

    def test_multiple_trades_same_token(self):
        trades = [
            {"token_bought_address": "0xAAA", "token_sold_address": "0xBNB", "trade_value_usd": 1000, "trader_address": "w1"},
            {"token_bought_address": "0xAAA", "token_sold_address": "0xUSDT", "trade_value_usd": 2000, "trader_address": "w2"},
            {"token_bought_address": "0xETH", "token_sold_address": "0xAAA", "trade_value_usd": 500, "trader_address": "w3"},
        ]
        result = aggregate_sm_trades(trades, {"0xaaa"})

        data = result["0xaaa"]
        assert data["buy_volume"] == 3000  # 1000 + 2000
        assert data["sell_volume"] == 500
        assert data["net_flow"] == 2500  # 3000 - 500
        assert data["trader_count"] == 3

    def test_case_insensitive_addresses(self):
        trades = [
            {"token_bought_address": "0xAbC", "token_sold_address": "0xBNB", "trade_value_usd": 500, "trader_address": "w1"},
            {"token_bought_address": "0xABC", "token_sold_address": "0xBNB", "trade_value_usd": 300, "trader_address": "w2"},
        ]
        result = aggregate_sm_trades(trades, {"0xabc"})

        data = result["0xabc"]
        assert data["buy_volume"] == 800
        assert data["trader_count"] == 2

    def test_unrelated_tokens_filtered(self):
        trades = [
            {"token_bought_address": "0xZZZ", "token_sold_address": "0xYYY", "trade_value_usd": 9999, "trader_address": "w1"},
        ]
        result = aggregate_sm_trades(trades, {"0xaaa"})
        assert result == {}

    def test_same_wallet_counted_once(self):
        trades = [
            {"token_bought_address": "0xAAA", "token_sold_address": "0xBNB", "trade_value_usd": 1000, "trader_address": "w1"},
            {"token_bought_address": "0xAAA", "token_sold_address": "0xBNB", "trade_value_usd": 2000, "trader_address": "w1"},
        ]
        result = aggregate_sm_trades(trades, {"0xaaa"})

        data = result["0xaaa"]
        assert data["buy_volume"] == 3000
        assert data["trader_count"] == 1  # same wallet

    def test_wallet_labels_collected(self):
        trades = [
            {"token_bought_address": "0xAAA", "token_sold_address": "0xBNB", "trade_value_usd": 100, "trader_address": "w1", "trader_address_label": "whale"},
            {"token_bought_address": "0xAAA", "token_sold_address": "0xBNB", "trade_value_usd": 200, "trader_address": "w2", "trader_address_label": "fund"},
        ]
        result = aggregate_sm_trades(trades, {"0xaaa"})

        data = result["0xaaa"]
        assert "whale" in data["wallet_labels"]
        assert "fund" in data["wallet_labels"]

    def test_empty_trades(self):
        assert aggregate_sm_trades([], {"0xaaa"}) == {}

    def test_empty_targets(self):
        trades = [
            {"token_bought_address": "0xAAA", "token_sold_address": "0xBNB", "trade_value_usd": 100, "trader_address": "w1"},
        ]
        assert aggregate_sm_trades(trades, set()) == {}


# --- DEX trade aggregation (simple format fallback) ---


class TestAggregateSmTradesSimpleFormat:
    """Tests using the simple format fallback (token_address + side)."""

    def test_basic_buy(self):
        trades = [
            {"token_address": "0xAAA", "side": "buy", "amount_usd": 1000, "wallet_address": "w1", "label": "whale"},
        ]
        result = aggregate_sm_trades(trades, {"0xaaa"})

        data = result["0xaaa"]
        assert data["buy_volume"] == 1000
        assert data["net_flow"] == 1000

    def test_basic_sell(self):
        trades = [
            {"token_address": "0xAAA", "side": "sell", "amount_usd": 500, "wallet_address": "w1"},
        ]
        result = aggregate_sm_trades(trades, {"0xaaa"})

        data = result["0xaaa"]
        assert data["sell_volume"] == 500
        assert data["net_flow"] == -500

    def test_swap_buy_sell_sides(self):
        trades = [
            {"token_address": "0xAAA", "side": "swap_buy", "amount_usd": 800, "wallet_address": "w1"},
            {"token_address": "0xAAA", "side": "swap_sell", "amount_usd": 300, "wallet_address": "w2"},
        ]
        result = aggregate_sm_trades(trades, {"0xaaa"})

        data = result["0xaaa"]
        assert data["buy_volume"] == 800
        assert data["sell_volume"] == 300
        assert data["net_flow"] == 500


# --- Holdings matching ---


class TestMatchHoldings:
    def test_basic_match_real_fields(self):
        """Test with actual Nansen API field names."""
        holdings = [
            {"token_address": "0xAAA", "value_usd": 50000, "balance_24h_percent_change": 10.0},
        ]
        result = match_holdings(holdings, {"0xaaa"})

        assert "0xaaa" in result
        assert result["0xaaa"]["holdings_value"] == 50000
        # 10% of 50000 = 5000
        assert result["0xaaa"]["holdings_change"] == 5000

    def test_zero_percent_change(self):
        holdings = [
            {"token_address": "0xAAA", "value_usd": 100000, "balance_24h_percent_change": 0},
        ]
        result = match_holdings(holdings, {"0xaaa"})

        assert result["0xaaa"]["holdings_value"] == 100000
        assert result["0xaaa"]["holdings_change"] == 0

    def test_negative_percent_change(self):
        holdings = [
            {"token_address": "0xAAA", "value_usd": 20000, "balance_24h_percent_change": -5.0},
        ]
        result = match_holdings(holdings, {"0xaaa"})

        # -5% of 20000 = -1000
        assert result["0xaaa"]["holdings_change"] == -1000

    def test_unmatched_filtered(self):
        holdings = [
            {"token_address": "0xAAA", "value_usd": 50000, "balance_24h_percent_change": 1.0},
            {"token_address": "0xZZZ", "value_usd": 99999, "balance_24h_percent_change": 50.0},
        ]
        result = match_holdings(holdings, {"0xaaa"})

        assert "0xaaa" in result
        assert "0xzzz" not in result

    def test_case_insensitive(self):
        holdings = [
            {"token_address": "0xAbCdEf", "value_usd": 10000, "balance_24h_percent_change": 2.0},
        ]
        result = match_holdings(holdings, {"0xabcdef"})

        assert "0xabcdef" in result

    def test_empty_holdings(self):
        assert match_holdings([], {"0xaaa"}) == {}

    def test_fallback_balance_usd_field(self):
        """Fallback to balance_usd if value_usd not present."""
        holdings = [
            {"token_address": "0xAAA", "balance_usd": 25000, "balance_change_24h_usd": 2500},
        ]
        result = match_holdings(holdings, {"0xaaa"})

        assert result["0xaaa"]["holdings_value"] == 25000
        assert result["0xaaa"]["holdings_change"] == 2500

    def test_small_percent_change(self):
        """Small percentage like 0.27% should compute correctly."""
        holdings = [
            {"token_address": "0xAAA", "value_usd": 17458.75, "balance_24h_percent_change": 0.272},
        ]
        result = match_holdings(holdings, {"0xaaa"})

        # 0.272% of 17458.75 = ~47.49
        assert abs(result["0xaaa"]["holdings_change"] - 47.49) < 1
