"""Tests for wallet_tracker."""


def test_build_tokentx_url_ethereum():
    from nansen_divergence.wallet_tracker import build_tokentx_url
    url = build_tokentx_url("ethereum", "0xabc123")
    assert "api.etherscan.io" in url
    assert "0xabc123" in url
    assert "tokentx" in url


def test_build_tokentx_url_bnb():
    from nansen_divergence.wallet_tracker import build_tokentx_url
    url = build_tokentx_url("bnb", "0xdef456")
    assert "bscscan.com" in url
    assert "0xdef456" in url


def test_build_tokentx_url_unknown_chain_defaults_to_etherscan():
    from nansen_divergence.wallet_tracker import build_tokentx_url
    url = build_tokentx_url("unknown_chain", "0xabc")
    assert "etherscan.io" in url


def test_score_wallet_empty():
    from nansen_divergence.wallet_tracker import score_wallet
    result = score_wallet([])
    assert result["win_rate"] == 0.0
    assert result["trade_count"] == 0
    assert result["label"] == "Unknown"
    assert result["score"] == 0.0


def test_score_wallet_all_wins_accumulator():
    from nansen_divergence.wallet_tracker import score_wallet
    trades = [
        {"bought_at": 100.0, "price_72h": 130.0},
        {"bought_at": 200.0, "price_72h": 260.0},
        {"bought_at": 50.0, "price_72h": 70.0},
        {"bought_at": 150.0, "price_72h": 200.0},
        {"bought_at": 80.0, "price_72h": 110.0},
    ]
    result = score_wallet(trades)
    assert result["win_rate"] == 1.0
    assert result["avg_return"] > 0
    assert result["label"] == "Accumulator"
    assert result["score"] > 80


def test_score_wallet_mixed_results_trader():
    from nansen_divergence.wallet_tracker import score_wallet
    trades = [
        {"bought_at": 100.0, "price_72h": 90.0},
        {"bought_at": 200.0, "price_72h": 210.0},
    ]
    result = score_wallet(trades)
    assert result["win_rate"] == 0.5
    assert result["label"] == "Trader"


def test_fetch_recent_buyers_returns_empty_on_api_error():
    from unittest.mock import patch
    from nansen_divergence.wallet_tracker import fetch_recent_buyers
    with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
        result = fetch_recent_buyers("ethereum", "0xabc")
    assert result == []


def test_unsupported_chain_returns_empty():
    from nansen_divergence.wallet_tracker import enrich_token_with_wallets
    result = enrich_token_with_wallets("solana", "SomeAddress123")
    assert result == []
