"""Tests for scan cache layer."""

from api.cache import get_latest_scan, save_cached_scan


def test_save_and_retrieve(tmp_path):
    data = {
        "results": [{"token_symbol": "ETH", "phase": "ACCUMULATION", "divergence_strength": 0.7}],
        "radar": [],
        "summary": {"total_tokens": 1},
        "chains": ["ethereum"],
    }
    save_cached_scan(data, cache_dir=str(tmp_path))
    retrieved = get_latest_scan(cache_dir=str(tmp_path))
    assert retrieved is not None
    assert retrieved["results"][0]["token_symbol"] == "ETH"
    assert "timestamp" in retrieved


def test_no_cache_returns_none(tmp_path):
    assert get_latest_scan(cache_dir=str(tmp_path)) is None
