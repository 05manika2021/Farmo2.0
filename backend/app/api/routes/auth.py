from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.auth import (
    SendOTPRequest, VerifyOTPRequest, ResendOTPRequest,
    OTPResponse, TokenResponse, AuthMeResponse,
)
from app.services.otp_service import send_otp, verify_otp, resend_otp
from app.core.dependencies import get_current_user
from app.db.models import Farmer

router = APIRouter()


@router.post("/send-otp", response_model=OTPResponse)
async def send_otp_endpoint(request: SendOTPRequest, db: Session = Depends(get_db)):
    result = send_otp(request.phone, db)
    if not result["success"]:
        error_code = result.get("error_code", "OTP_SEND_FAILED")
        status_code = _error_to_status(error_code)
        raise HTTPException(
            status_code=status_code,
            detail={"error_code": error_code, "message": result["message"]},
        )
    return OTPResponse(**result)


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    result = verify_otp(request.phone, request.otp, db)
    if not result["success"]:
        error_code = result.get("error_code", "OTP_VERIFICATION_FAILED")
        status_code = _error_to_status(error_code)
        raise HTTPException(
            status_code=status_code,
            detail={"error_code": error_code, "message": result["message"]},
        )
    return TokenResponse(**result)


@router.post("/resend-otp", response_model=OTPResponse)
async def resend_otp_endpoint(request: ResendOTPRequest, db: Session = Depends(get_db)):
    result = resend_otp(request.phone, db)
    if not result["success"]:
        error_code = result.get("error_code", "OTP_SEND_FAILED")
        status_code = _error_to_status(error_code)
        raise HTTPException(
            status_code=status_code,
            detail={"error_code": error_code, "message": result["message"]},
        )
    return OTPResponse(**result)


@router.get("/me", response_model=AuthMeResponse)
async def get_current_user_info(
    current_user: Farmer = Depends(get_current_user),
):
    return AuthMeResponse(
        farmer_id=current_user.id,
        phone=current_user.phone,
        name=current_user.name,
        language=current_user.language,
        village=current_user.village,
    )


def _error_to_status(error_code: str) -> int:
    mapping = {
        "INVALID_PHONE_NUMBER": 400,
        "OTP_SEND_FAILED": 502,
        "OTP_RATE_LIMITED": 429,
        "OTP_PROVIDER_NOT_CONFIGURED": 503,
        "INVALID_OTP": 401,
        "OTP_EXPIRED": 401,
        "OTP_MAX_ATTEMPTS": 429,
        "OTP_NOT_FOUND": 401,
        "OTP_VERIFICATION_FAILED": 401,
    }
    return mapping.get(error_code, 400)
