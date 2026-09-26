"""Tests for 2Factor.in SMS OTP provider.

All HTTP calls to 2factor.in are mocked — no real SMS is sent.
Uses the classic GET API:
  GET /API/V1/{key}/SMS/{phone}/{otp}[/{template}]
  GET /API/V1/{key}/SMS/VERIFY/{session_id}/{otp}
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.twofactor_otp import TwoFactorOTP, _to_e164, _to_local, get_twofactor_provider


# ── Phone normalization ──────────────────────────────────────────────────────


class TestToE164:
    def test_10_digit(self):
        assert _to_e164("9876543210") == "+919876543210"

    def test_with_plus91(self):
        assert _to_e164("+919876543210") == "+919876543210"

    def test_with_91_prefix(self):
        assert _to_e164("919876543210") == "+919876543210"

    def test_with_spaces(self):
        assert _to_e164("98765 43210") == "+919876543210"

    def test_with_dashes(self):
        assert _to_e164("98765-43210") == "+919876543210"

    def test_invalid_short(self):
        with pytest.raises(ValueError):
            _to_e164("123")

    def test_invalid_letters(self):
        with pytest.raises(ValueError):
            _to_e164("abcdefghij")


class TestToLocal:
    def test_10_digit(self):
        assert _to_local("9876543210") == "9876543210"

    def test_e164(self):
        assert _to_local("+919876543210") == "9876543210"

    def test_invalid(self):
        with pytest.raises(ValueError):
            _to_local("123")


# ── Provider configuration ──────────────────────────────────────────────────


class TestTwoFactorConfig:
    def test_not_configured_without_key(self):
        with patch("app.services.twofactor_otp.settings") as mock_settings:
            mock_settings.TWOFACTOR_API_KEY = None
            provider = TwoFactorOTP()
            assert provider.is_configured() is False

    def test_not_configured_with_empty_key(self):
        with patch("app.services.twofactor_otp.settings") as mock_settings:
            mock_settings.TWOFACTOR_API_KEY = "  "
            provider = TwoFactorOTP()
            assert provider.is_configured() is False

    def test_configured_with_key(self):
        with patch("app.services.twofactor_otp.settings") as mock_settings:
            mock_settings.TWOFACTOR_API_KEY = "test-api-key-123"
            provider = TwoFactorOTP()
            assert provider.is_configured() is True


# ── Send OTP (SMS) ──────────────────────────────────────────────────────────


class TestTwoFactorSend:
    def test_send_not_configured(self):
        with patch("app.services.twofactor_otp.settings") as mock_settings:
            mock_settings.TWOFACTOR_API_KEY = None
            provider = TwoFactorOTP()
            result = provider.send("+919876543210", "123456")
            assert result["success"] is False
            assert result["error_code"] == "OTP_PROVIDER_NOT_CONFIGURED"

    def test_send_sms_success_with_template(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Status": "Success",
            "Details": "abc-123-def",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", return_value=mock_response) as mock_get:
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.send("9876543210", "472918")

            assert result["success"] is True
            assert result["provider_reference"] == "abc-123-def"
            assert result["status"] == "sent"

            mock_get.assert_called_once()
            url = mock_get.call_args[0][0]
            assert "/test-key/SMS/9876543210/472918/OTP" in url

    def test_send_sms_success_without_template(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Status": "Success",
            "Details": "sess-xyz",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", return_value=mock_response) as mock_get:
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = ""

            provider = TwoFactorOTP()
            result = provider.send("+919876543210", "654321")

            assert result["success"] is True
            assert result["provider_reference"] == "sess-xyz"
            url = mock_get.call_args[0][0]
            assert "/test-key/SMS/9876543210/654321" in url
            assert "/OTP" not in url

    def test_send_401_invalid_key(self):
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        exc = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", side_effect=exc):
            mock_settings.TWOFACTOR_API_KEY = "bad-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.send("9876543210", "123456")

            assert result["success"] is False
            assert result["error_code"] == "OTP_PROVIDER_NOT_CONFIGURED"

    def test_send_429_rate_limited(self):
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        exc = httpx.HTTPStatusError("429", request=MagicMock(), response=mock_response)

        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", side_effect=exc):
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.send("9876543210", "123456")

            assert result["success"] is False
            assert result["error_code"] == "OTP_RATE_LIMITED"

    def test_send_timeout(self):
        import httpx
        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", side_effect=httpx.TimeoutException("timeout")):
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.send("9876543210", "123456")

            assert result["success"] is False
            assert result["error_code"] == "OTP_SEND_FAILED"

    def test_send_error_response(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Status": "Error", "Details": "Some error"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", return_value=mock_response):
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.send("9876543210", "123456")

            assert result["success"] is False
            assert result["error_code"] == "OTP_SEND_FAILED"

    def test_send_invalid_phone(self):
        with patch("app.services.twofactor_otp.settings") as mock_settings:
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"
            provider = TwoFactorOTP()
            result = provider.send("+91123", "123456")
            assert result["success"] is False
            assert result["error_code"] == "INVALID_PHONE_NUMBER"


# ── Verify OTP ──────────────────────────────────────────────────────────────


class TestTwoFactorVerify:
    def test_verify_not_configured(self):
        with patch("app.services.twofactor_otp.settings") as mock_settings:
            mock_settings.TWOFACTOR_API_KEY = None
            provider = TwoFactorOTP()
            result = provider.verify("+919876543210", "123456", "session-1")
            assert result["success"] is False
            assert result["error_code"] == "OTP_PROVIDER_NOT_CONFIGURED"

    def test_verify_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Status": "Success", "Details": "OTP Matched"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", return_value=mock_response) as mock_get:
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.verify("9876543210", "123456", "session-abc")

            assert result["success"] is True
            assert result["status"] == "verified"
            url = mock_get.call_args[0][0]
            assert "/test-key/SMS/VERIFY/session-abc/123456" in url

    def test_verify_expired(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Status": "Error", "Details": "OTP expired"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", return_value=mock_response):
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.verify("9876543210", "123456", "session-abc")

            assert result["success"] is False
            assert result["error_code"] == "OTP_EXPIRED"

    def test_verify_invalid(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Status": "Error", "Details": "Invalid OTP"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", return_value=mock_response):
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.verify("9876543210", "000000", "session-abc")

            assert result["success"] is False
            assert result["error_code"] == "OTP_VERIFICATION_FAILED"

    def test_verify_max_attempts(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Status": "Error", "Details": "Max attempts reached"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", return_value=mock_response):
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.verify("9876543210", "123456", "session-abc")

            assert result["success"] is False
            assert result["error_code"] == "OTP_MAX_ATTEMPTS"

    def test_verify_timeout(self):
        import httpx
        with patch("app.services.twofactor_otp.settings") as mock_settings, \
             patch("app.services.twofactor_otp.httpx.get", side_effect=httpx.TimeoutException("timeout")):
            mock_settings.TWOFACTOR_API_KEY = "test-key"
            mock_settings.TWOFACTOR_SMS_TEMPLATE = "OTP"

            provider = TwoFactorOTP()
            result = provider.verify("9876543210", "123456", "session-abc")

            assert result["success"] is False
            assert result["error_code"] == "OTP_VERIFICATION_FAILED"


# ── Provider factory ────────────────────────────────────────────────────────


class TestGetProvider:
    def test_returns_two_factor_instance(self):
        provider = get_twofactor_provider()
        assert isinstance(provider, TwoFactorOTP)
