import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("farmo.twilio")


def _get_client():
    """Lazy-load Twilio client to avoid import errors when not configured."""
    try:
        from twilio.rest import Client
    except ImportError:
        raise RuntimeError(
            "twilio package not installed. Run: pip install twilio"
        )
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials not configured")
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def to_e164(phone: str) -> str:
    """Convert Indian phone number to E.164 format: +91XXXXXXXXXX."""
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if cleaned.startswith("+91"):
        return cleaned
    if cleaned.startswith("91") and len(cleaned) == 12:
        return f"+{cleaned}"
    if len(cleaned) == 10 and cleaned.isdigit():
        return f"+91{cleaned}"
    raise ValueError(f"Invalid Indian phone number: {phone}")


def is_twilio_configured() -> bool:
    """Check if Twilio Verify is properly configured."""
    return bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_VERIFY_SERVICE_SID
    )


def send_verification(phone: str) -> dict:
    """
    Send OTP via Twilio Verify.
    Returns {"success": True} or {"success": False, "error_code": "..."}.
    """
    if not is_twilio_configured():
        return {"success": False, "error_code": "OTP_PROVIDER_NOT_CONFIGURED"}

    e164_phone = to_e164(phone)
    client = _get_client()

    try:
        verification = client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verifications.create(to=e164_phone, channel="sms")

        logger.info(f"Twilio verification sent to {e164_phone}, status: {verification.status}")
        return {"success": True}

    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"Twilio send verification failed: {e}")

        if "not a valid phone number" in error_str or "invalid" in error_str:
            return {"success": False, "error_code": "INVALID_PHONE_NUMBER"}
        if "rate limit" in error_str or "too many" in error_str:
            return {"success": False, "error_code": "OTP_RATE_LIMITED"}
        if "not configured" in error_str or "missing" in error_str:
            return {"success": False, "error_code": "OTP_PROVIDER_NOT_CONFIGURED"}

        return {"success": False, "error_code": "OTP_SEND_FAILED"}


def check_verification(phone: str, code: str) -> dict:
    """
    Check OTP via Twilio Verify.
    Returns {"success": True, "status": "approved"} or
            {"success": False, "error_code": "...", "status": "..."}.
    """
    if not is_twilio_configured():
        return {"success": False, "error_code": "OTP_PROVIDER_NOT_CONFIGURED"}

    e164_phone = to_e164(phone)
    client = _get_client()

    try:
        verification_check = client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verification_checks.create(to=e164_phone, code=code)

        status = verification_check.status
        logger.info(f"Twilio verification check for {e164_phone}: {status}")

        if status == "approved":
            return {"success": True, "status": "approved"}
        elif status == "pending":
            return {"success": False, "error_code": "OTP_VERIFICATION_FAILED", "status": status}
        elif status == "expired":
            return {"success": False, "error_code": "OTP_EXPIRED", "status": status}
        elif status == "max_attempts_reached":
            return {"success": False, "error_code": "OTP_MAX_ATTEMPTS", "status": status}
        else:
            return {"success": False, "error_code": "OTP_VERIFICATION_FAILED", "status": status}

    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"Twilio verification check failed: {e}")

        if "not a valid phone number" in error_str or "invalid" in error_str:
            return {"success": False, "error_code": "INVALID_PHONE_NUMBER"}
        if "expired" in error_str:
            return {"success": False, "error_code": "OTP_EXPIRED"}
        if "max" in error_str and "attempt" in error_str:
            return {"success": False, "error_code": "OTP_MAX_ATTEMPTS"}

        return {"success": False, "error_code": "OTP_VERIFICATION_FAILED"}
