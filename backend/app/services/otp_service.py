import random
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.db.models import OTPRecord, Farmer
from app.core.config import settings
from app.core.security import validate_indian_phone, normalize_indian_phone, create_access_token
from app.services.twofactor_otp import get_twofactor_provider, _to_e164


def _provider_configured() -> bool:
    return get_twofactor_provider().is_configured()


def generate_otp() -> str:
    """Generate a 6-digit OTP. In demo mode returns the fixed demo OTP."""
    if settings.DEMO_MODE:
        return settings.DEMO_OTP
    return "".join(random.choices(string.digits, k=6))


def send_otp(phone: str, db: Session) -> dict:
    cleaned = normalize_indian_phone(phone)
    if not validate_indian_phone(cleaned):
        return {"success": False, "error_code": "INVALID_PHONE_NUMBER", "message": "Invalid Indian phone number format"}

    now = datetime.now(timezone.utc)
    recent_otp = (
        db.query(OTPRecord)
        .filter(
            OTPRecord.phone == cleaned,
            OTPRecord.created_at > now - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS),
        )
        .first()
    )
    if recent_otp:
        remaining = settings.OTP_RESEND_COOLDOWN_SECONDS - int(
            (now - recent_otp.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        )
        if remaining > 0:
            return {
                "success": False,
                "error_code": "OTP_RATE_LIMITED",
                "message": f"Please wait {remaining} seconds before requesting a new OTP",
            }

    otp_code = generate_otp()
    expires_at = now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS)

    if settings.DEMO_MODE or not _provider_configured():
        otp_record = OTPRecord(
            phone=cleaned,
            otp_code=otp_code,
            created_at=now,
            expires_at=expires_at,
            is_used=False,
            attempts=0,
        )
        db.add(otp_record)
        db.commit()

        response = {
            "success": True,
            "message": "Demo OTP generated" if settings.DEMO_MODE else "OTP sent successfully",
            "demo_mode": settings.DEMO_MODE,
        }
        if settings.DEMO_MODE:
            response["demo_otp"] = otp_code
        return response
    else:
        provider = get_twofactor_provider()
        e164 = _to_e164(cleaned)
        result = provider.send(e164, otp_code)
        if not result["success"]:
            return {
                "success": False,
                "error_code": result.get("error_code", "OTP_SEND_FAILED"),
                "message": "Failed to send OTP. Please try again.",
            }

        session_id = result.get("provider_reference", "")
        otp_record = OTPRecord(
            phone=cleaned,
            otp_code=f"2f:{session_id}",
            created_at=now,
            expires_at=expires_at,
            is_used=False,
            attempts=0,
        )
        db.add(otp_record)
        db.commit()

        return {
            "success": True,
            "message": "OTP sent successfully",
            "demo_mode": False,
        }


def verify_otp(phone: str, otp: str, db: Session) -> dict:
    cleaned = normalize_indian_phone(phone)
    if not validate_indian_phone(cleaned):
        return {"success": False, "error_code": "INVALID_PHONE_NUMBER", "message": "Invalid phone number"}

    if len(otp) != 6 or not otp.isdigit():
        return {"success": False, "error_code": "INVALID_OTP", "message": "OTP must be 6 digits"}

    now = datetime.now(timezone.utc)
    otp_record = (
        db.query(OTPRecord)
        .filter(
            OTPRecord.phone == cleaned,
            OTPRecord.is_used == False,
        )
        .order_by(OTPRecord.created_at.desc())
        .first()
    )

    if not otp_record:
        return {"success": False, "error_code": "OTP_NOT_FOUND", "message": "No OTP found. Please request a new one."}

    if otp_record.expires_at.replace(tzinfo=timezone.utc) < now:
        return {"success": False, "error_code": "OTP_EXPIRED", "message": "OTP has expired. Please request a new one."}

    if otp_record.attempts >= 5:
        return {"success": False, "error_code": "OTP_MAX_ATTEMPTS", "message": "Too many attempts. Please request a new OTP."}

    is_demo_record = not otp_record.otp_code.startswith("2f:")

    if settings.DEMO_MODE or not _provider_configured() or is_demo_record:
        if otp_record.otp_code != otp:
            otp_record.attempts += 1
            db.commit()
            return {"success": False, "error_code": "INVALID_OTP", "message": "Invalid OTP"}
    else:
        session_id = otp_record.otp_code.replace("2f:", "", 1)
        provider = get_twofactor_provider()
        e164 = _to_e164(cleaned)
        twilio_result = provider.verify(e164, otp, session_id)
        if not twilio_result["success"]:
            otp_record.attempts += 1
            db.commit()
            error_code = twilio_result.get("error_code", "OTP_VERIFICATION_FAILED")
            if error_code == "OTP_EXPIRED":
                return {"success": False, "error_code": "OTP_EXPIRED", "message": "OTP has expired. Please request a new one."}
            if error_code == "OTP_MAX_ATTEMPTS":
                return {"success": False, "error_code": "OTP_MAX_ATTEMPTS", "message": "Too many attempts. Please request a new OTP."}
            return {"success": False, "error_code": "INVALID_OTP", "message": "Invalid OTP"}

    otp_record.is_used = True
    db.commit()

    farmer = db.query(Farmer).filter(Farmer.phone == cleaned).first()
    if not farmer:
        farmer = Farmer(
            name=f"Farmer_{cleaned[-4:]}",
            phone=cleaned,
            language="hi",
        )
        db.add(farmer)
        db.commit()
        db.refresh(farmer)

    token = create_access_token(data={"sub": str(farmer.id)})
    return {
        "success": True,
        "message": "OTP verified successfully",
        "access_token": token,
        "farmer_id": farmer.id,
    }


def resend_otp(phone: str, db: Session) -> dict:
    return send_otp(phone, db)
