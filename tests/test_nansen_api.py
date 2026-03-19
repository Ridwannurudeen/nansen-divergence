"""Tests for Nansen REST API mode (dual dispatch)."""

import io
import json
import os
from unittest import mock

from nansen_divergence.nansen import _api_post, _get_api_key


class TestGetApiKey:
    def test_returns_key_when_set(self):
        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "test-key-123"}):
            assert _get_api_key() == "test-key-123"

    def test_returns_none_when_empty(self):
        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": ""}):
            assert _get_api_key() is None

    def test_returns_none_when_whitespace(self):
        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "   "}):
            assert _get_api_key() is None

    def test_returns_none_when_missing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            assert _get_api_key() is None

    def test_strips_whitespace(self):
        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "  my-key  "}):
            assert _get_api_key() == "my-key"


class TestApiPost:
    def test_url_construction(self):
        response_data = json.dumps({"data": {"data": []}}).encode()
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "test-key"}):
            with mock.patch("nansen_divergence.nansen.urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
                _api_post("/token-screener", {"chain": "ethereum"})
                req = mock_urlopen.call_args[0][0]
                assert req.full_url == "https://api.nansen.ai/api/v1/token-screener"

    def test_headers_set(self):
        response_data = json.dumps({"ok": True}).encode()
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "my-key-456"}):
            with mock.patch("nansen_divergence.nansen.urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
                _api_post("/test", {"a": 1})
                req = mock_urlopen.call_args[0][0]
                assert req.get_header("Apikey") == "my-key-456"
                assert req.get_header("Content-type") == "application/json"

    def test_returns_parsed_json(self):
        payload = {"data": [{"symbol": "ETH"}]}
        response_data = json.dumps(payload).encode()
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "key"}):
            with mock.patch("nansen_divergence.nansen.urllib.request.urlopen", return_value=mock_resp):
                result = _api_post("/test", {})
                assert result == payload

    def test_http_error_returns_empty(self):
        import urllib.error

        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "key"}):
            exc = urllib.error.HTTPError("url", 403, "Forbidden", {}, io.BytesIO(b"forbidden"))
            with mock.patch("nansen_divergence.nansen.urllib.request.urlopen", side_effect=exc):
                result = _api_post("/test", {})
                assert result == {}

    def test_timeout_returns_empty(self):
        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "key"}):
            with mock.patch("nansen_divergence.nansen.urllib.request.urlopen", side_effect=TimeoutError("timed out")):
                result = _api_post("/test", {})
                assert result == {}

    def test_no_api_key_raises(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            try:
                _api_post("/test", {})
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                assert "NANSEN_API_KEY" in str(e)


class TestDualModeDispatch:
    def test_token_screener_uses_api_when_key_set(self):
        from nansen_divergence.nansen import token_screener

        response = {"data": {"data": [{"symbol": "ETH"}], "pagination": {"is_last_page": True}}}
        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "key"}):
            with mock.patch("nansen_divergence.nansen._api_post", return_value=response) as mock_api:
                result = token_screener("ethereum", pages=1)
                mock_api.assert_called()
                assert len(result) == 1
                assert result[0]["symbol"] == "ETH"

    def test_token_screener_uses_cli_when_no_key(self):
        from nansen_divergence.nansen import token_screener

        cli_response = {"success": True, "data": {"data": [{"symbol": "BTC"}], "pagination": {"is_last_page": True}}}
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("nansen_divergence.nansen._run", return_value=cli_response) as mock_run:
                result = token_screener("ethereum", pages=1)
                mock_run.assert_called()
                assert result[0]["symbol"] == "BTC"

    def test_smart_money_holdings_api_mode(self):
        from nansen_divergence.nansen import smart_money_holdings

        response = {"data": {"data": [{"token": "AAVE"}]}}
        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "key"}):
            with mock.patch("nansen_divergence.nansen._api_post", return_value=response):
                result = smart_money_holdings("ethereum")
                assert len(result) == 1

    def test_flow_intelligence_api_mode(self):
        from nansen_divergence.nansen import flow_intelligence

        response = {"data": {"flows": [1, 2, 3]}}
        with mock.patch.dict(os.environ, {"NANSEN_API_KEY": "key"}):
            with mock.patch("nansen_divergence.nansen._api_post", return_value=response):
                result = flow_intelligence("ethereum", "0xAAA")
                assert "flows" in result
