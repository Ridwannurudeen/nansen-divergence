"""Tests for Telegram alert notifications."""

from unittest.mock import MagicMock, patch

from nansen_divergence.alerts import (
    _format_alert,
    _get_config,
    _send_message,
    send_divergence_alerts,
    send_scan_summary,
)

SAMPLE_TOKEN_HIGH = {
    "chain": "ethereum",
    "token_symbol": "AAVE",
    "price_change": -0.08,
    "market_cap": 1_500_000_000,
    "sm_net_flow": 500_000,
    "market_netflow": -200_000,
    "divergence_strength": 0.65,
    "phase": "ACCUMULATION",
    "confidence": "HIGH",
    "narrative": "5 SM wallets bought $500K -- stealth loading",
}

SAMPLE_TOKEN_LOW = {
    "chain": "bnb",
    "token_symbol": "XYZ",
    "price_change": -0.02,
    "sm_net_flow": 1000,
    "divergence_strength": 0.15,
    "phase": "ACCUMULATION",
    "confidence": "LOW",
    "narrative": "",
}


class TestGetConfig:
    @patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "abc123", "TELEGRAM_CHAT_ID": "456"})
    def test_returns_config(self):
        result = _get_config()
        assert result == ("abc123", "456")

    @patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": "456"}, clear=True)
    def test_missing_token(self):
        assert _get_config() is None

    @patch.dict("os.environ", {}, clear=True)
    def test_no_env_vars(self):
        assert _get_config() is None


class TestSendMessage:
    @patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"})
    @patch("nansen_divergence.alerts.urllib.request.urlopen")
    def test_sends_correct_url(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = _send_message("hello")
        assert result is True

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert "bot" in req.full_url
        assert "tok" in req.full_url
        assert "sendMessage" in req.full_url

    @patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"})
    @patch("nansen_divergence.alerts.urllib.request.urlopen")
    def test_http_error_returns_false(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=400, msg="Bad Request", hdrs=None, fp=None
        )
        result = _send_message("hello")
        assert result is False

    @patch.dict("os.environ", {}, clear=True)
    def test_no_config_returns_false(self):
        result = _send_message("hello")
        assert result is False


class TestFormatAlert:
    def test_contains_phase_and_symbol(self):
        text = _format_alert(SAMPLE_TOKEN_HIGH)
        assert "ACCUMULATION" in text
        assert "AAVE" in text
        assert "ethereum" in text

    def test_contains_strength(self):
        text = _format_alert(SAMPLE_TOKEN_HIGH)
        assert "0.65" in text

    def test_contains_narrative(self):
        text = _format_alert(SAMPLE_TOKEN_HIGH)
        assert "stealth loading" in text


class TestSendDivergenceAlerts:
    @patch("nansen_divergence.alerts._send_message", return_value=True)
    def test_sends_high_med_only(self, mock_send):
        results = [SAMPLE_TOKEN_HIGH, SAMPLE_TOKEN_LOW]
        sent = send_divergence_alerts(results)
        assert sent == 1  # Only HIGH, not LOW
        assert mock_send.call_count == 1

    @patch("nansen_divergence.alerts._send_message", return_value=True)
    def test_caps_at_five(self, mock_send):
        tokens = [
            {**SAMPLE_TOKEN_HIGH, "token_symbol": f"T{i}", "token_address": f"0x{i}"}
            for i in range(10)
        ]
        sent = send_divergence_alerts(tokens)
        assert sent == 5
        assert mock_send.call_count == 5

    @patch("nansen_divergence.alerts._send_message", return_value=True)
    def test_no_divergent_sends_zero(self, mock_send):
        markup = {**SAMPLE_TOKEN_HIGH, "phase": "MARKUP"}
        sent = send_divergence_alerts([markup])
        assert sent == 0
        assert mock_send.call_count == 0

    @patch("nansen_divergence.alerts._send_message", return_value=False)
    def test_failed_sends_not_counted(self, mock_send):
        sent = send_divergence_alerts([SAMPLE_TOKEN_HIGH])
        assert sent == 0


class TestSendScanSummary:
    @patch("nansen_divergence.alerts._send_message", return_value=True)
    def test_sends_summary(self, mock_send):
        summary = {
            "total_tokens": 40,
            "divergence_signals": 8,
            "confidence_high": 3,
            "confidence_medium": 5,
        }
        result = send_scan_summary(summary, ["ethereum", "bnb"])
        assert result is True
        text = mock_send.call_args[0][0]
        assert "ETHEREUM" in text
        assert "40" in text
