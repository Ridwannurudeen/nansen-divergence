"""Tests for Alpha Score conversion and backtesting stats."""

from nansen_divergence.divergence import alpha_score
from nansen_divergence.history import backtest_stats


def test_alpha_score_converts_strength_to_0_100():
    assert alpha_score(0.0) == 0
    assert alpha_score(0.5) == 50
    assert alpha_score(1.0) == 100


def test_alpha_score_rounds_to_int():
    assert alpha_score(0.123) == 12
    assert alpha_score(0.876) == 88


def test_alpha_score_clamps():
    assert alpha_score(-0.5) == 0
    assert alpha_score(1.5) == 100


def test_backtest_stats_empty():
    result = backtest_stats([])
    assert result["total_signals"] == 0
    assert result["win_rate"] == 0.0
    assert result["avg_return"] == 0.0


def test_backtest_stats_mixed():
    validations = [
        {"phase": "ACCUMULATION", "price_change_pct": 15.0},
        {"phase": "ACCUMULATION", "price_change_pct": -5.0},
        {"phase": "DISTRIBUTION", "price_change_pct": -10.0},
        {"phase": "DISTRIBUTION", "price_change_pct": 3.0},
    ]
    result = backtest_stats(validations)
    assert result["total_signals"] == 4
    assert result["win_rate"] == 50.0
    assert result["wins"] == 2
    assert result["losses"] == 2


def test_backtest_stats_best_worst():
    validations = [
        {"phase": "ACCUMULATION", "price_change_pct": 25.0},
        {"phase": "ACCUMULATION", "price_change_pct": 5.0},
        {"phase": "ACCUMULATION", "price_change_pct": -10.0},
    ]
    result = backtest_stats(validations)
    assert result["best_return"] == 25.0
    assert result["worst_return"] == -10.0
