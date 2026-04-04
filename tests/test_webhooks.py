"""Tests for webhook dispatcher."""
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch


def test_sign_payload_produces_valid_hmac():
    from nansen_divergence.webhook_dispatcher import sign_payload
    secret = "test-secret"
    payload = json.dumps({"phase": "ACCUMULATION"}).encode()
    sig = sign_payload(secret, payload)
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert sig == expected


def test_sign_payload_different_secrets_differ():
    from nansen_divergence.webhook_dispatcher import sign_payload
    payload = b'{"test": 1}'
    s1 = sign_payload("secret1", payload)
    s2 = sign_payload("secret2", payload)
    assert s1 != s2


def test_post_webhook_calls_url_on_success():
    from nansen_divergence.webhook_dispatcher import _post_webhook
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        result = _post_webhook("https://example.com/hook", "secret", {"phase": "ACCUMULATION"})
    assert result is True
    assert mock_open.called
    call_args = mock_open.call_args[0][0]
    assert call_args.full_url == "https://example.com/hook"
    # urllib.request.Request normalises header names to title-case internally;
    # the key is stored as "X-nansen-signature" — check case-insensitively.
    headers_lower = {k.lower(): v for k, v in call_args.headers.items()}
    assert "x-nansen-signature" in headers_lower


def test_post_webhook_returns_false_on_error():
    from nansen_divergence.webhook_dispatcher import _post_webhook
    with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
        result = _post_webhook("https://example.com/hook", "secret", {})
    assert result is False


def test_dispatch_signal_filters_by_chain():
    """dispatch_signal skips webhooks whose chain filter doesn't match."""
    import os, tempfile
    from nansen_divergence.history import init_db
    from nansen_divergence.webhook_dispatcher import dispatch_signal

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = init_db(db_path=db_path)
        conn.execute(
            "INSERT INTO webhooks (id, url, secret, filters, created_at) VALUES (?,?,?,?,?)",
            ("w1", "https://example.com", "secret", '{"chain": "solana"}', "2026-01-01")
        )
        conn.commit()
        conn.close()

        with patch("nansen_divergence.webhook_dispatcher._post_webhook", return_value=True) as mock_post:
            fired = dispatch_signal({"chain": "ethereum", "phase": "ACCUMULATION", "strength": 80}, db_path=db_path)
        assert fired == 0
        mock_post.assert_not_called()
    finally:
        os.unlink(db_path)


def test_register_webhook_endpoint():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.post("/api/v1/webhooks/register", json={"url": "https://example.com/hook"})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "secret" in data
    assert len(data["secret"]) == 64


def test_delete_webhook_not_found():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.delete("/api/v1/webhooks/nonexistent-id-xyz")
    assert resp.status_code == 404
