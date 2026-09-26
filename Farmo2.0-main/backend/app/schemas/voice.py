from pydantic import BaseModel, Field
from typing import Optional


class VoiceTranscribeRequest(BaseModel):
    audio_data: Optional[str] = None
    audio_url: Optional[str] = None
    language: str = Field(default="hi")


class VoiceTranscribeResponse(BaseModel):
    transcribed_text: str
    language: str
    confidence: Optional[float] = None
    provider: str = "unconfigured"
    error: Optional[str] = None


class VoiceRespondRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: str = Field(default="hi")


class VoiceRespondResponse(BaseModel):
    audio_base64: Optional[str] = None
    audio_format: str = "mp3"
    text: str
    provider: str = "unconfigured"
    status: str = "unconfigured"
    error: Optional[str] = None


class VoicePipelineResponse(BaseModel):
    transcribed_text: str
    answer_text: str
    answer_audio_base64: Optional[str] = None
    answer_audio_format: str = "mp3"
    language: str
    intent: str
    context_used: list[str] = []
    data_status: str = "DEMO"
    stt_provider: str = "unavailable"
    tts_provider: str = "unavailable"
    gemini_source: str = "fallback"
    stt_error: Optional[str] = None
    tts_error: Optional[str] = None
