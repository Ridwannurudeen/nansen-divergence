"""Tests for signal history storage and validation."""

import os
import tempfile

from nansen_divergence.history import (
    clear_history,
    detect_new_tokens,
    get_recent_signals,
    get_scan_history,
    init_db,
    save_scan,
    validate_signals,
)


def _make_token(
    symbol="AAVE",
    chain="ethereum",
    address="0xAAA",
    price=95.20,
    price_change=-0.08,
    mcap=1_500_000_000,
    sm_flow=500_000,
    strength=0.65,
    phase="ACCUMULATION",
    confidence="HIGH",
    narrative="stealth loading",
):
    return {
        "chain": chain,
        "token_address": address,
        "token_symbol": symbol,
        "price_usd": price,
        "price_change": price_change,
        "market_cap": mcap,
        "sm_net_flow": sm_flow,
        "divergence_strength": strength,
        "phase": phase,
        "confidence": confidence,
        "narrative": narrative,
        "has_sm_data": True,
    }


def _temp_db():
    """Create a temporary database and return the connection."""
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test_history.db")
    return init_db(db_path)


class TestInitDb:
    def test_creates_tables(self):
        conn = _temp_db()
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t["name"] for t in tables}
        assert "scans" in table_names
        assert "signals" in table_names
        conn.close()

    def test_idempotent(self):
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test.db")
        conn1 = init_db(db_path)
        conn1.close()
        conn2 = init_db(db_path)
        tables = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert len(tables) >= 2
        conn2.close()


class TestSaveScan:
    def test_returns_scan_id(self):
        conn = _temp_db()
        scan_id = save_scan([_make_token()], ["ethereum"], "24h", conn=conn)
        assert isinstance(scan_id, int)
        assert scan_id > 0
        conn.close()

    def test_saves_scan_metadata(self):
        conn = _temp_db()
        save_scan([_make_token(), _make_token(symbol="ETH")], ["ethereum", "bnb"], "24h", conn=conn)
        row = conn.execute("SELECT * FROM scans WHERE id=1").fetchone()
        assert row["token_count"] == 2
        assert row["timeframe"] == "24h"
        conn.close()

    def test_saves_signals(self):
        conn = _temp_db()
        save_scan([_make_token()], ["ethereum"], "24h", conn=conn)
        signals = conn.execute("SELECT * FROM signals").fetchall()
        assert len(signals) == 1
        assert signals[0]["token_symbol"] == "AAVE"
        assert signals[0]["phase"] == "ACCUMULATION"
        conn.close()

    def test_saves_multiple_tokens(self):
        conn = _temp_db()
        tokens = [
            _make_token(symbol="AAVE", address="0xA"),
            _make_token(symbol="SHIB", address="0xB", phase="DISTRIBUTION"),
            _make_token(symbol="ETH", address="0xC", phase="MARKUP"),
        ]
        save_scan(tokens, ["ethereum"], "24h", conn=conn)
        count = conn.execute("SELECT COUNT(*) as c FROM signals").fetchone()["c"]
        assert count == 3
        conn.close()

    def test_empty_results(self):
        conn = _temp_db()
        scan_id = save_scan([], ["ethereum"], "24h", conn=conn)
        assert scan_id > 0
        row = conn.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
        assert row["token_count"] == 0
        assert row["divergence_count"] == 0
        conn.close()

    def test_divergence_count(self):
        conn = _temp_db()
        tokens = [
            _make_token(phase="ACCUMULATION"),
            _make_token(phase="DISTRIBUTION", symbol="X", address="0xX"),
            _make_token(phase="MARKUP", symbol="Y", address="0xY"),
        ]
        save_scan(tokens, ["ethereum"], "24h", conn=conn)
        row = conn.execute("SELECT * FROM scans WHERE id=1").fetchone()
        assert row["divergence_count"] == 2
        conn.close()


class TestValidateSignals:
    def test_validates_price_delta(self):
        conn = _temp_db()
        save_scan([_make_token(price=95.20)], ["ethereum"], "24h", conn=conn)
        current = [_make_token(price=101.50)]
        validations = validate_signals(current, lookback_days=7, conn=conn)
        assert len(validations) == 1
        v = validations[0]
        assert v["token_symbol"] == "AAVE"
        assert v["signal_price"] == 95.20
        assert v["current_price"] == 101.50
        assert abs(v["price_change_pct"] - 6.6) < 0.5
        conn.close()

    def test_no_match_different_token(self):
        conn = _temp_db()
        save_scan([_make_token()], ["ethereum"], "24h", conn=conn)
        current = [_make_token(symbol="XYZ", address="0xZZZ")]
        validations = validate_signals(current, lookback_days=7, conn=conn)
        assert len(validations) == 0
        conn.close()

    def test_only_high_med_divergent(self):
        conn = _temp_db()
        tokens = [
            _make_token(symbol="A", address="0xA", confidence="HIGH", phase="ACCUMULATION"),
            _make_token(symbol="B", address="0xB", confidence="LOW", phase="ACCUMULATION"),
            _make_token(symbol="C", address="0xC", confidence="MEDIUM", phase="MARKUP"),
        ]
        save_scan(tokens, ["ethereum"], "24h", conn=conn)
        current = [
            _make_token(symbol="A", address="0xA", price=100),
            _make_token(symbol="B", address="0xB", price=100),
            _make_token(symbol="C", address="0xC", price=100),
        ]
        validations = validate_signals(current, lookback_days=7, conn=conn)
        # Only A should be validated (HIGH + ACCUMULATION)
        symbols = [v["token_symbol"] for v in validations]
        assert "A" in symbols
        assert "B" not in symbols  # LOW confidence excluded
        assert "C" not in symbols  # MARKUP not divergent
        conn.close()

    def test_multiple_signals_deduplication(self):
        conn = _temp_db()
        save_scan([_make_token(price=90.0)], ["ethereum"], "24h", conn=conn)
        save_scan([_make_token(price=95.0)], ["ethereum"], "24h", conn=conn)
        current = [_make_token(price=100.0)]
        validations = validate_signals(current, lookback_days=7, conn=conn)
        # Should deduplicate by address — only most recent signal
        assert len(validations) == 1
        conn.close()

    def test_empty_history(self):
        conn = _temp_db()
        current = [_make_token()]
        validations = validate_signals(current, lookback_days=7, conn=conn)
        assert len(validations) == 0
        conn.close()

    def test_zero_signal_price_skipped(self):
        conn = _temp_db()
        save_scan([_make_token(price=0)], ["ethereum"], "24h", conn=conn)
        current = [_make_token(price=100)]
        validations = validate_signals(current, lookback_days=7, conn=conn)
        assert len(validations) == 0
        conn.close()


class TestGetRecentSignals:
    def test_returns_signals(self):
        conn = _temp_db()
        save_scan([_make_token()], ["ethereum"], "24h", conn=conn)
        signals = get_recent_signals(days=7, conn=conn)
        assert len(signals) == 1
        assert signals[0]["token_symbol"] == "AAVE"
        conn.close()

    def test_filter_by_phase(self):
        conn = _temp_db()
        tokens = [
            _make_token(symbol="A", address="0xA", phase="ACCUMULATION"),
            _make_token(symbol="B", address="0xB", phase="DISTRIBUTION"),
        ]
        save_scan(tokens, ["ethereum"], "24h", conn=conn)
        signals = get_recent_signals(days=7, phase="ACCUMULATION", conn=conn)
        assert all(s["phase"] == "ACCUMULATION" for s in signals)
        conn.close()

    def test_empty_db(self):
        conn = _temp_db()
        signals = get_recent_signals(days=7, conn=conn)
        assert signals == []
        conn.close()


class TestGetScanHistory:
    def test_returns_scans(self):
        conn = _temp_db()
        save_scan([_make_token()], ["ethereum"], "24h", conn=conn)
        save_scan([_make_token()], ["bnb"], "24h", conn=conn)
        scans = get_scan_history(limit=20, conn=conn)
        assert len(scans) == 2
        conn.close()

    def test_respects_limit(self):
        conn = _temp_db()
        for i in range(5):
            save_scan([_make_token()], ["ethereum"], "24h", conn=conn)
        scans = get_scan_history(limit=3, conn=conn)
        assert len(scans) == 3
        conn.close()


class TestDetectNewTokens:
    def test_empty_db_all_new(self):
        conn = _temp_db()
        tokens = [
            _make_token(symbol="A", address="0xA"),
            _make_token(symbol="B", address="0xB"),
        ]
        new = detect_new_tokens(tokens, conn=conn)
        assert new == {"0xa", "0xb"}
        conn.close()

    def test_existing_tokens_excluded(self):
        conn = _temp_db()
        save_scan([_make_token(symbol="OLD", address="0xOLD")], ["ethereum"], "24h", conn=conn)
        current = [
            _make_token(symbol="OLD", address="0xOLD"),
            _make_token(symbol="NEW", address="0xNEW"),
        ]
        new = detect_new_tokens(current, conn=conn)
        assert "0xnew" in new
        assert "0xold" not in new
        conn.close()

    def test_case_insensitive(self):
        conn = _temp_db()
        save_scan([_make_token(address="0xAbC")], ["ethereum"], "24h", conn=conn)
        current = [_make_token(address="0xabc")]
        new = detect_new_tokens(current, conn=conn)
        assert len(new) == 0
        conn.close()

    def test_empty_results(self):
        conn = _temp_db()
        new = detect_new_tokens([], conn=conn)
        assert new == set()
        conn.close()


class TestClearHistory:
    def test_clears_all(self):
        conn = _temp_db()
        save_scan([_make_token()], ["ethereum"], "24h", conn=conn)
        clear_history(conn=conn)
        scans = conn.execute("SELECT COUNT(*) as c FROM scans").fetchone()["c"]
        signals = conn.execute("SELECT COUNT(*) as c FROM signals").fetchone()["c"]
        assert scans == 0
        assert signals == 0
        conn.close()

    def test_clear_empty_db(self):
        conn = _temp_db()
        clear_history(conn=conn)  # Should not raise
        conn.close()
