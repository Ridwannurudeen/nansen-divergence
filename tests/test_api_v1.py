"""Tests for API v1 endpoints."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


def test_v1_performance_returns_stats(client):
    resp = client.get("/api/v1/performance")
    assert resp.status_code == 200
    data = resp.json()
    assert "win_rate" in data
    assert "total_signals" in data
    assert "by_phase" in data
    assert "by_chain" in data


def test_v1_signals_returns_list(client):
    resp = client.get("/api/v1/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert "signals" in data
    assert isinstance(data["signals"], list)
    assert "total" in data


def test_v1_signal_not_found(client):
    resp = client.get("/api/v1/signals/999999")
    assert resp.status_code == 404


def test_v1_performance_by_phase(client):
    resp = client.get("/api/v1/performance/by-phase")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)
