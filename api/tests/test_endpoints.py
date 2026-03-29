"""Tests for the FastAPI endpoint layer."""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

TIMESTAMP = "2026-03-22T12:00:00+00:00"

SCAN_RESULT = {
    "chain": "ethereum",
    "token_address": "0xABCdef1234567890abcdef1234567890ABCDEF12",
    "token_symbol": "AAVE",
    "phase": "ACCUMULATION",
    "confidence": "HIGH",
    "sm_net_flow": 750_000,
    "sm_buy_volume": 1_200_000,
    "sm_sell_volume": 450_000,
    "sm_trader_count": 18,
    "market_cap": 1_500_000_000,
    "price_usd": 95.20,
    "price_change": -0.08,
    "divergence_strength": 0.72,
    "alpha_score": 3.6,
    "has_sm_data": True,
    "narrative": "stealth loading — big buyers while price dips",
}

SCAN_RESULT_BNB = {
    "chain": "bnb",
    "token_address": "0x1111222233334444555566667777888899990000",
    "token_symbol": "CAKE",
    "phase": "DISTRIBUTION",
    "confidence": "MEDIUM",
    "sm_net_flow": -320_000,
    "sm_buy_volume": 180_000,
    "sm_sell_volume": 500_000,
    "sm_trader_count": 9,
    "market_cap": 400_000_000,
    "price_usd": 2.45,
    "price_change": 0.12,
    "divergence_strength": 0.55,
    "alpha_score": 2.2,
    "has_sm_data": True,
    "narrative": "insiders unloading into retail pump",
}

RADAR_ENTRY = {
    "chain": "ethereum",
    "token_address": "0xDeadBeef00000000000000000000000000000001",
    "token_symbol": "LDO",
    "sm_net_flow_24h": 400_000,
    "sm_net_flow_7d": 2_100_000,
    "sm_trader_count": 12,
    "sm_sectors": ["DeFi", "Liquid Staking"],
    "market_cap": 2_000_000_000,
}

RADAR_ENTRY_2 = {
    "chain": "bnb",
    "token_address": "0xBBBB000000000000000000000000000000000002",
    "token_symbol": "XVS",
    "sm_net_flow_24h": 150_000,
    "sm_net_flow_7d": 800_000,
    "sm_trader_count": 5,
    "sm_sectors": ["DeFi", "Lending"],
    "market_cap": 120_000_000,
}


def _make_scan_data(results=None, radar=None):
    """Build a complete cached scan payload."""
    return {
        "results": results if results is not None else [SCAN_RESULT, SCAN_RESULT_BNB],
        "radar": radar if radar is not None else [RADAR_ENTRY, RADAR_ENTRY_2],
        "summary": {"total_tokens": 2, "divergence_count": 2},
        "chains": ["ethereum", "bnb"],
        "timestamp": TIMESTAMP,
    }


# ---------------------------------------------------------------------------
# Mock the scheduler so the lifespan doesn't fire real scans
# ---------------------------------------------------------------------------

_scheduler_mock = MagicMock()
_scheduler_mock.shutdown = MagicMock()


@pytest.fixture(autouse=True)
def _patch_scheduler():
    with patch("api.main.start_scheduler", return_value=_scheduler_mock):
        yield


@pytest.fixture()
def client():
    from api.main import app
    return TestClient(app)


# ===================================================================
# GET /api/token/{chain}/{address} — server-side deep dive proxy
# ===================================================================

class TestTokenDeepDive:
    def test_token_deep_dive_success(self, client):
        """Proxied deep dive returns upstream data when NANSEN_API_KEY is set."""
        deep_dive_response = {
            "token": "AAVE",
            "chain": "ethereum",
            "flow_summary": {"net_flow_24h": 750_000},
            "top_buyers": [{"entity": "whale_1", "amount": 300_000}],
        }
        with (
            patch.dict(os.environ, {"NANSEN_API_KEY": "test-key-123"}),
            patch(
                "nansen_divergence.deep_dive.deep_dive_token",
                return_value=deep_dive_response,
            ) as mock_dd,
        ):
            resp = client.get("/api/token/ethereum/0xAAA")

        assert resp.status_code == 200
        body = resp.json()
        assert body["token"] == "AAVE"
        assert body["flow_summary"]["net_flow_24h"] == 750_000
        mock_dd.assert_called_once_with("ethereum", "0xAAA", days=7, profile_count=3)

    def test_token_deep_dive_no_key(self, client):
        """Returns 503 when the server has no NANSEN_API_KEY configured."""
        from api.main import _rate_tracker
        _rate_tracker.clear()
        with patch.dict(os.environ, {}, clear=False):
            # Ensure key is absent
            os.environ.pop("NANSEN_API_KEY", None)
            resp = client.get("/api/token/ethereum/0xAAA")

        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()

    def test_token_deep_dive_upstream_error(self, client):
        """Returns 502 when the deep_dive_token call raises an exception."""
        from api.main import _rate_tracker
        _rate_tracker.clear()
        with (
            patch.dict(os.environ, {"NANSEN_API_KEY": "test-key-123"}),
            patch(
                "nansen_divergence.deep_dive.deep_dive_token",
                side_effect=RuntimeError("Nansen API timeout"),
            ),
        ):
            resp = client.get("/api/token/ethereum/0xAAA")

        assert resp.status_code == 502
        assert "Deep dive failed" in resp.json()["detail"]


# ===================================================================
# GET /api/token/{chain}/{address}/summary — cached token summary
# ===================================================================

class TestTokenSummary:
    def test_token_summary_found(self, client):
        """Returns cached result when the token exists in scan results."""
        with patch("api.main.get_latest_scan", return_value=_make_scan_data()):
            addr = SCAN_RESULT["token_address"]
            resp = client.get(f"/api/token/ethereum/{addr}/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["token"]["token_symbol"] == "AAVE"
        assert body["timestamp"] == TIMESTAMP

    def test_token_summary_found_case_insensitive(self, client):
        """Address matching is case-insensitive."""
        with patch("api.main.get_latest_scan", return_value=_make_scan_data()):
            addr_lower = SCAN_RESULT["token_address"].lower()
            resp = client.get(f"/api/token/ethereum/{addr_lower}/summary")

        assert resp.status_code == 200
        assert resp.json()["token"]["token_symbol"] == "AAVE"

    def test_token_summary_from_radar(self, client):
        """Falls back to radar entries when not found in main results."""
        # Provide scan with no matching results but matching radar
        scan = _make_scan_data(results=[], radar=[RADAR_ENTRY])
        with patch("api.main.get_latest_scan", return_value=scan):
            addr = RADAR_ENTRY["token_address"]
            resp = client.get(f"/api/token/ethereum/{addr}/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["source"] == "radar"
        assert body["token"]["token_symbol"] == "LDO"

    def test_token_summary_not_found(self, client):
        """Returns 404 when token address is not in the cached scan."""
        with patch("api.main.get_latest_scan", return_value=_make_scan_data()):
            resp = client.get("/api/token/ethereum/0xNONEXISTENT/summary")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_token_summary_wrong_chain(self, client):
        """Returns 404 when token exists but on a different chain."""
        with patch("api.main.get_latest_scan", return_value=_make_scan_data()):
            addr = SCAN_RESULT["token_address"]  # ethereum token
            resp = client.get(f"/api/token/solana/{addr}/summary")

        assert resp.status_code == 404

    def test_token_summary_no_data(self, client):
        """Returns 404 when there is no cached scan data at all."""
        with patch("api.main.get_latest_scan", return_value=None):
            resp = client.get("/api/token/ethereum/0xAAA/summary")

        assert resp.status_code == 404
        assert "no scan data" in resp.json()["detail"].lower()


# ===================================================================
# GET /api/flows — cross-chain flow aggregation
# ===================================================================

class TestCrossChainFlows:
    def test_flows_with_data(self, client):
        """Aggregates chain momentum and sector breakdowns from cache."""
        with patch("api.main.get_latest_scan", return_value=_make_scan_data()):
            resp = client.get("/api/flows")

        assert resp.status_code == 200
        body = resp.json()

        # Chain aggregation
        assert "ethereum" in body["chains"]
        assert "bnb" in body["chains"]
        eth = body["chains"]["ethereum"]
        assert eth["token_count"] == 1
        assert eth["sm_flow_total"] == SCAN_RESULT["sm_net_flow"]
        assert eth["sm_buy_total"] == SCAN_RESULT["sm_buy_volume"]
        assert eth["sm_sell_total"] == SCAN_RESULT["sm_sell_volume"]
        assert eth["accumulation"] == 1
        assert eth["distribution"] == 0
        assert eth["high_confidence"] == 1
        # momentum_score = (1 - 0) / 1 * 100 = 100.0
        assert eth["momentum_score"] == 100.0

        bnb = body["chains"]["bnb"]
        assert bnb["token_count"] == 1
        assert bnb["distribution"] == 1
        # momentum_score = (0 - 1) / 1 * 100 = -100.0
        assert bnb["momentum_score"] == -100.0

        # Sector aggregation from radar
        assert "DeFi" in body["sectors"]
        defi = body["sectors"]["DeFi"]
        assert defi["token_count"] == 2  # LDO + XVS both have DeFi
        assert "LDO" in defi["tokens"]
        assert "XVS" in defi["tokens"]

        assert "Liquid Staking" in body["sectors"]
        ls = body["sectors"]["Liquid Staking"]
        assert ls["token_count"] == 1
        assert "LDO" in ls["tokens"]

        assert "Lending" in body["sectors"]
        assert body["sectors"]["Lending"]["token_count"] == 1

        assert body["timestamp"] == TIMESTAMP

    def test_flows_no_data(self, client):
        """Returns empty structure when no scan data is cached."""
        with patch("api.main.get_latest_scan", return_value=None):
            resp = client.get("/api/flows")

        assert resp.status_code == 200
        body = resp.json()
        assert body["chains"] == {}
        assert body["sectors"] == {}
        assert body["timestamp"] is None

    def test_flows_empty_results(self, client):
        """Returns empty chains when scan exists but has no results."""
        scan = _make_scan_data(results=[], radar=[])
        with patch("api.main.get_latest_scan", return_value=scan):
            resp = client.get("/api/flows")

        assert resp.status_code == 200
        body = resp.json()
        assert body["chains"] == {}
        assert body["sectors"] == {}
        assert body["timestamp"] == TIMESTAMP


# ===================================================================
# GET /api/history/outcomes — signal outcomes with stats
# ===================================================================

class TestHistoryOutcomes:
    def test_outcomes_with_data(self, client):
        """Returns validations and backtest stats from cached results."""
        mock_validations = [
            {
                "token_symbol": "AAVE",
                "chain": "ethereum",
                "signal_price": 90.0,
                "current_price": 95.20,
                "price_change_pct": 5.78,
                "phase": "ACCUMULATION",
                "outcome": "WIN",
            },
        ]
        mock_stats = {
            "total_signals": 1,
            "wins": 1,
            "losses": 0,
            "win_rate": 100.0,
            "avg_return": 5.78,
            "best_return": 5.78,
            "worst_return": 5.78,
        }
        scan = _make_scan_data()
        with (
            patch("api.main.get_latest_scan", return_value=scan),
            patch("nansen_divergence.history.validate_signals", return_value=mock_validations) as mock_vs,
            patch("nansen_divergence.history.backtest_stats", return_value=mock_stats) as mock_bs,
        ):
            resp = client.get("/api/history/outcomes?days=14")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["outcomes"]) == 1
        assert body["outcomes"][0]["outcome"] == "WIN"
        assert body["stats"]["win_rate"] == 100.0
        assert body["stats"]["total_signals"] == 1

        # Verify correct args passed through
        mock_vs.assert_called_once()
        call_args = mock_vs.call_args
        assert call_args.kwargs.get("lookback_days") == 14 or call_args[1].get("lookback_days") == 14
        mock_bs.assert_called_once_with(mock_validations)

    def test_outcomes_no_scan_data(self, client):
        """Returns empty outcomes when no cached scan exists."""
        with patch("api.main.get_latest_scan", return_value=None):
            resp = client.get("/api/history/outcomes")

        assert resp.status_code == 200
        body = resp.json()
        assert body["outcomes"] == []
        assert body["stats"]["total_signals"] == 0
        assert body["stats"]["win_rate"] == 0.0

    def test_outcomes_empty_results(self, client):
        """Returns empty outcomes when scan has no results."""
        scan = _make_scan_data(results=[])
        with patch("api.main.get_latest_scan", return_value=scan):
            resp = client.get("/api/history/outcomes")

        assert resp.status_code == 200
        body = resp.json()
        assert body["outcomes"] == []
        assert body["stats"]["total_signals"] == 0

    def test_outcomes_default_days(self, client):
        """Default lookback is 30 days when not specified."""
        scan = _make_scan_data()
        with (
            patch("api.main.get_latest_scan", return_value=scan),
            patch("nansen_divergence.history.validate_signals", return_value=[]) as mock_vs,
            patch("nansen_divergence.history.backtest_stats", return_value={
                "total_signals": 0, "wins": 0, "losses": 0,
                "win_rate": 0.0, "avg_return": 0.0, "best_return": 0.0, "worst_return": 0.0,
            }),
        ):
            resp = client.get("/api/history/outcomes")

        assert resp.status_code == 200
        mock_vs.assert_called_once()
        call_args = mock_vs.call_args
        assert call_args.kwargs.get("lookback_days") == 30 or call_args[1].get("lookback_days") == 30
