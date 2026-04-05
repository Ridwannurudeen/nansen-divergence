"""Tests for outcome_tracker."""
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest


def _make_db_with_signal(phase="ACCUMULATION", hours_ago=25):
    """Helper: create temp DB with one signal past the 24h window."""
    from nansen_divergence.history import init_db
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = f.name
    f.close()
    conn = init_db(db_path=db_path)
    scan_time = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    conn.execute(
        "INSERT INTO scans (timestamp, chains, timeframe, token_count, divergence_count) VALUES (?,?,?,?,?)",
        (scan_time, "ethereum", "24h", 1, 1)
    )
    scan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """INSERT INTO signals
           (scan_id, scan_timestamp, chain, token_address, token_symbol,
            price_usd, price_change, market_cap, sm_net_flow,
            divergence_strength, phase, confidence, narrative, has_sm_data,
            price_at_emission)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (scan_id, scan_time, "ethereum", "0xabc", "TKN",
         100.0, -8.0, 1_000_000, 50_000,
         0.75, phase, "HIGH", "test", 1, 100.0)
    )
    conn.commit()
    return conn, db_path


def test_fill_24h_outcome_correct_accumulation():
    conn, db_path = _make_db_with_signal("ACCUMULATION", hours_ago=25)
    try:
        with patch("nansen_divergence.outcome_tracker.fetch_price", return_value=115.0):
            from nansen_divergence.outcome_tracker import fill_outcomes
            filled = fill_outcomes(conn=conn, db_path=db_path)
        assert filled >= 1
        row = conn.execute("SELECT price_24h, return_24h FROM signals WHERE token_symbol='TKN'").fetchone()
        assert row["price_24h"] == 115.0
        assert abs(row["return_24h"] - 15.0) < 0.01
    finally:
        conn.close()
        os.unlink(db_path)


def test_fill_72h_outcome_correct_sets_outcome_correct():
    conn, db_path = _make_db_with_signal("ACCUMULATION", hours_ago=73)
    try:
        with patch("nansen_divergence.outcome_tracker.fetch_price", return_value=120.0):
            from nansen_divergence.outcome_tracker import fill_outcomes
            fill_outcomes(conn=conn, db_path=db_path)
        row = conn.execute("SELECT outcome_correct FROM signals WHERE token_symbol='TKN'").fetchone()
        assert row["outcome_correct"] == 1
    finally:
        conn.close()
        os.unlink(db_path)


def test_distribution_price_down_is_correct():
    conn, db_path = _make_db_with_signal("DISTRIBUTION", hours_ago=73)
    try:
        with patch("nansen_divergence.outcome_tracker.fetch_price", return_value=85.0):
            from nansen_divergence.outcome_tracker import fill_outcomes
            fill_outcomes(conn=conn, db_path=db_path)
        row = conn.execute("SELECT outcome_correct FROM signals WHERE token_symbol='TKN'").fetchone()
        assert row["outcome_correct"] == 1
    finally:
        conn.close()
        os.unlink(db_path)


def test_signal_too_recent_not_filled():
    conn, db_path = _make_db_with_signal("ACCUMULATION", hours_ago=1)
    try:
        with patch("nansen_divergence.outcome_tracker.fetch_price", return_value=115.0):
            from nansen_divergence.outcome_tracker import fill_outcomes
            filled = fill_outcomes(conn=conn, db_path=db_path)
        assert filled == 0
        row = conn.execute("SELECT price_24h FROM signals WHERE token_symbol='TKN'").fetchone()
        assert row["price_24h"] is None
    finally:
        conn.close()
        os.unlink(db_path)
