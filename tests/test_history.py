"""Tests for signal history storage and validation."""

import os
import tempfile

from nansen_divergence.history import (
    clear_history,
    detect_new_tokens,
    get_recent_signals,
    get_scan_history,
    get_signal_streaks,
    get_sparkline_data,
    get_token_history,
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


class TestGetTokenHistory:
    def test_returns_history(self):
        conn = _temp_db()
        save_scan([_make_token(chain="ethereum", address="0xA")], ["ethereum"], "24h", conn=conn)
        save_scan([_make_token(chain="ethereum", address="0xA", strength=0.8)], ["ethereum"], "24h", conn=conn)
        history = get_token_history("ethereum", "0xA", days=7, conn=conn)
        assert len(history) == 2
        assert history[0]["divergence_strength"] == 0.65
        assert history[1]["divergence_strength"] == 0.8
        conn.close()

    def test_empty_for_unknown_token(self):
        conn = _temp_db()
        save_scan([_make_token()], ["ethereum"], "24h", conn=conn)
        history = get_token_history("ethereum", "0xUNKNOWN", days=7, conn=conn)
        assert history == []
        conn.close()

    def test_case_insensitive_address(self):
        conn = _temp_db()
        save_scan([_make_token(address="0xAbCdEf")], ["ethereum"], "24h", conn=conn)
        history = get_token_history("ethereum", "0xabcdef", days=7, conn=conn)
        assert len(history) == 1
        conn.close()


class TestGetSparklineData:
    def test_returns_sparklines(self):
        conn = _temp_db()
        save_scan([_make_token(address="0xA", strength=0.5)], ["ethereum"], "24h", conn=conn)
        save_scan([_make_token(address="0xA", strength=0.7)], ["ethereum"], "24h", conn=conn)
        sparklines = get_sparkline_data(days=7, points=10, conn=conn)
        assert "0xA".lower() in sparklines or "0xa" in sparklines
        vals = sparklines.get("0xa", sparklines.get("0xA".lower(), []))
        assert len(vals) == 2
        assert vals[0] == 0.5
        assert vals[1] == 0.7
        conn.close()

    def test_limits_points(self):
        conn = _temp_db()
        for i in range(5):
            save_scan([_make_token(address="0xA", strength=i * 0.1)], ["ethereum"], "24h", conn=conn)
        sparklines = get_sparkline_data(days=7, points=3, conn=conn)
        vals = sparklines.get("0xa", [])
        assert len(vals) == 3
        # Should be the last 3 values
        assert vals[0] == 0.2
        conn.close()

    def test_empty_db(self):
        conn = _temp_db()
        sparklines = get_sparkline_data(days=7, conn=conn)
        assert sparklines == {}
        conn.close()


class TestGetSignalStreaks:
    def test_detects_streak(self):
        conn = _temp_db()
        save_scan([_make_token(address="0xA", phase="ACCUMULATION")], ["ethereum"], "24h", conn=conn)
        save_scan([_make_token(address="0xA", phase="ACCUMULATION")], ["ethereum"], "24h", conn=conn)
        save_scan([_make_token(address="0xA", phase="ACCUMULATION")], ["ethereum"], "24h", conn=conn)
        streaks = get_signal_streaks(days=14, conn=conn)
        assert "0xa" in streaks
        assert streaks["0xa"]["phase"] == "ACCUMULATION"
        assert streaks["0xa"]["streak"] == 3
        conn.close()

    def test_no_streak_for_single_scan(self):
        conn = _temp_db()
        save_scan([_make_token(address="0xA")], ["ethereum"], "24h", conn=conn)
        streaks = get_signal_streaks(days=14, conn=conn)
        assert "0xa" not in streaks
        conn.close()

    def test_streak_breaks_on_phase_change(self):
        conn = _temp_db()
        save_scan([_make_token(address="0xA", phase="DISTRIBUTION")], ["ethereum"], "24h", conn=conn)
        save_scan([_make_token(address="0xA", phase="ACCUMULATION")], ["ethereum"], "24h", conn=conn)
        save_scan([_make_token(address="0xA", phase="ACCUMULATION")], ["ethereum"], "24h", conn=conn)
        streaks = get_signal_streaks(days=14, conn=conn)
        assert "0xa" in streaks
        assert streaks["0xa"]["streak"] == 2
        assert streaks["0xa"]["phase"] == "ACCUMULATION"
        conn.close()


def test_signals_table_has_outcome_columns():
    import tempfile, os
    from nansen_divergence.history import init_db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        conn = init_db(db_path=db_path)
        cursor = conn.execute("PRAGMA table_info(signals)")
        cols = {row["name"] for row in cursor.fetchall()}
        assert "price_at_emission" in cols
        assert "price_24h" in cols
        assert "price_72h" in cols
        assert "price_7d" in cols
        assert "return_24h" in cols
        assert "return_72h" in cols
        assert "return_7d" in cols
        assert "outcome_correct" in cols
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_wallet_scores_table_exists():
    import tempfile, os
    from nansen_divergence.history import init_db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        conn = init_db(db_path=db_path)
        conn.execute("INSERT INTO wallet_scores (address, chain) VALUES ('0xabc', 'ethereum')")
        conn.commit()
        row = conn.execute("SELECT address FROM wallet_scores").fetchone()
        assert row[0] == '0xabc'
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_webhooks_table_exists():
    import tempfile, os
    from nansen_divergence.history import init_db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        conn = init_db(db_path=db_path)
        conn.execute("INSERT INTO webhooks (id, url, secret, created_at) VALUES ('1', 'http://x.com', 'secret', '2026-01-01')")
        conn.commit()
        row = conn.execute("SELECT url FROM webhooks").fetchone()
        assert row[0] == 'http://x.com'
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_get_performance_stats_empty():
    import tempfile, os
    from nansen_divergence.history import init_db, get_performance_stats
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        conn = init_db(db_path=db_path)
        stats = get_performance_stats(conn=conn)
        assert stats["total_signals"] == 0
        assert stats["win_rate"] == 0.0
        assert "by_phase" in stats
        assert "by_chain" in stats
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_get_performance_stats_with_outcomes():
    import tempfile, os
    from nansen_divergence.history import init_db, save_scan, get_performance_stats
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        conn = init_db(db_path=db_path)
        results = [
            {"chain": "ethereum", "token_address": "0x1", "token_symbol": "A",
             "price_usd": 100.0, "price_change": -8.0, "market_cap": 1e6,
             "sm_net_flow": 50000, "divergence_strength": 0.8, "phase": "ACCUMULATION",
             "confidence": "HIGH", "narrative": "x", "has_sm_data": 1},
            {"chain": "ethereum", "token_address": "0x2", "token_symbol": "B",
             "price_usd": 200.0, "price_change": -5.0, "market_cap": 1e6,
             "sm_net_flow": 30000, "divergence_strength": 0.6, "phase": "ACCUMULATION",
             "confidence": "MEDIUM", "narrative": "y", "has_sm_data": 1},
        ]
        save_scan(results, ["ethereum"], "24h", conn=conn)
        conn.execute("UPDATE signals SET return_72h=20.0, outcome_correct=1 WHERE token_symbol='A'")
        conn.execute("UPDATE signals SET return_72h=-10.0, outcome_correct=0 WHERE token_symbol='B'")
        conn.commit()
        stats = get_performance_stats(conn=conn)
        assert stats["resolved"] == 2
        assert stats["wins"] == 1
        assert stats["losses"] == 1
        assert stats["win_rate"] == 0.5
        assert stats["avg_return_on_wins"] == 20.0
        assert "ACCUMULATION" in stats["by_phase"]
        assert "ethereum" in stats["by_chain"]
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_save_scan_records_price_at_emission():
    import tempfile, os
    from nansen_divergence.history import init_db, save_scan
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        conn = init_db(db_path=db_path)
        results = [{
            "chain": "ethereum",
            "token_address": "0xabc",
            "token_symbol": "TKN",
            "price_usd": 42.5,
            "price_change": -8.0,
            "market_cap": 1000000,
            "sm_net_flow": 50000,
            "divergence_strength": 0.75,
            "phase": "ACCUMULATION",
            "confidence": "HIGH",
            "narrative": "test",
            "has_sm_data": 1,
        }]
        save_scan(results, ["ethereum"], "24h", conn=conn)
        row = conn.execute("SELECT price_at_emission FROM signals WHERE token_symbol='TKN'").fetchone()
        assert row is not None
        assert row["price_at_emission"] == 42.5
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)
