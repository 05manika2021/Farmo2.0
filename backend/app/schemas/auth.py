from pydantic import BaseModel, Field
from typing import Optional


class SendOTPRequest(BaseModel):
    phone: str = Field(..., description="Indian phone number (10 digits or +91...)")


class VerifyOTPRequest(BaseModel):
    phone: str = Field(..., description="Indian phone number")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")


class ResendOTPRequest(BaseModel):
    phone: str = Field(..., description="Indian phone number")


class OTPResponse(BaseModel):
    success: bool
    message: str
    error_code: Optional[str] = None
    demo_mode: bool = False
    demo_otp: Optional[str] = None


class TokenResponse(BaseModel):
    success: bool
    message: str = "OTP verified successfully"
    access_token: str
    token_type: str = "bearer"
    farmer_id: Optional[int] = None
    error_code: Optional[str] = None


class AuthMeResponse(BaseModel):
    farmer_id: int
    phone: str
    name: Optional[str] = None
    language: Optional[str] = None
    village: Optional[str] = None
