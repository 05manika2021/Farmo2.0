import logging
import base64
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.voice import (
    VoiceTranscribeRequest, VoiceTranscribeResponse,
    VoiceRespondRequest, VoiceRespondResponse,
    VoicePipelineResponse,
)
from app.services.stt_service import stt_service, normalize_language, ALLOWED_AUDIO_TYPES, MAX_AUDIO_SIZE_MB
from app.services.tts_service import tts_service
from app.services.gemini_service import (
    gemini_service,
    failure_message,
    classify_ai_error,
    ai_unavailable_message,
)

logger = logging.getLogger("farmo.voice")

router = APIRouter()


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_audio(request: VoiceTranscribeRequest):
    if request.audio_data:
        try:
            audio_bytes = base64.b64decode(request.audio_data)
        except Exception:
            return VoiceTranscribeResponse(
                transcribed_text="",
                language=request.language,
                confidence=None,
                provider="unavailable",
                error="Invalid base64 audio data.",
            )
        result = await stt_service.transcribe(
            audio_bytes=audio_bytes,
            filename="audio.wav",
            content_type="audio/wav",
            language=request.language,
        )
        return VoiceTranscribeResponse(**result)

    return VoiceTranscribeResponse(
        transcribed_text="",
        language=request.language,
        confidence=None,
        provider="unavailable",
        error="No audio_data provided. Send base64-encoded audio in audio_data field.",
    )


@router.post("/respond", response_model=VoiceRespondResponse)
async def voice_respond(request: VoiceRespondRequest):
    tts_result = await tts_service.synthesize(text=request.text, language=request.language)
    return VoiceRespondResponse(
        audio_base64=tts_result.get("audio_base64"),
        audio_format=tts_result.get("audio_format", "audio/mpeg"),
        text=request.text,
        provider=tts_result.get("provider", "unavailable"),
        status="ok" if tts_result.get("error") is None else tts_result["error"],
        error=tts_result.get("error"),
    )


@router.post("/pipeline", response_model=VoicePipelineResponse)
async def voice_pipeline(
    audio: UploadFile = File(...),
    language: str = Form(default="hi"),
    farmer_id: str = Form(default=None),
    crop: str = Form(default=None),
    quantity: float = Form(default=None),
    latitude: float = Form(default=22.7196),
    longitude: float = Form(default=75.8577),
    db: Session = Depends(get_db),
):
    content_type = audio.content_type or "audio/wav"
    app_language = normalize_language(language)
    if content_type not in ALLOWED_AUDIO_TYPES:
        return VoicePipelineResponse(
            transcribed_text="",
            answer_text="",
            language=app_language,
            intent="general",
            data_status="UNAVAILABLE",
            stt_provider="unavailable",
            tts_provider="unavailable",
            stt_error=f"Unsupported audio type: {content_type}.",
        )

    audio_bytes = await audio.read()
    size_mb = len(audio_bytes) / (1024 * 1024)
    if size_mb > MAX_AUDIO_SIZE_MB:
        return VoicePipelineResponse(
            transcribed_text="",
            answer_text="",
            language=app_language,
            intent="general",
            data_status="UNAVAILABLE",
            stt_provider="unavailable",
            tts_provider="unavailable",
            stt_error=f"Audio file too large ({size_mb:.1f}MB). Maximum: {MAX_AUDIO_SIZE_MB}MB.",
        )

    stt_result = await stt_service.transcribe(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.wav",
        content_type=content_type,
        language=app_language,
    )

    if stt_result.get("error"):
        return VoicePipelineResponse(
            transcribed_text="",
            answer_text="",
            language=app_language,
            intent="general",
            data_status="UNAVAILABLE",
            stt_provider=stt_result.get("provider", "unavailable"),
            tts_provider="unavailable",
            stt_error=stt_result["error"],
        )

    transcribed_text = stt_result["transcribed_text"]

    try:
        gemini_result = await gemini_service.generate_response(
            message=transcribed_text,
            language=app_language,
            crop=crop,
            quantity=quantity,
            farmer_lat=latitude,
            farmer_lon=longitude,
            db=db,
        )
    except Exception as e:
        # Log only the safe classification, never the raw provider message.
        error_code = classify_ai_error(e)
        logger.error(
            "Gemini error in voice pipeline [%s] (%s)", error_code, type(e).__name__
        )
        gemini_result = {
            "answer": failure_message(app_language),
            "language": app_language,
            "intent": "general",
            "context_used": [],
            "data_status": "UNAVAILABLE",
            "source": "fallback",
            "error_code": error_code,
            "error_message": ai_unavailable_message(app_language),
        }

    answer_text = gemini_result["answer"]
    intent = gemini_result["intent"]
    # Explicit AI-failure signal for the frontend. The answer is never blank:
    # when Gemini cannot generate we still return verified local data.
    error_code = gemini_result.get("error_code")
    error_message = gemini_result.get("error_message")
    success = error_code is None

    tts_result = await tts_service.synthesize(text=answer_text, language=app_language)

    return VoicePipelineResponse(
        transcribed_text=transcribed_text,
        answer_text=answer_text,
        answer_audio_base64=tts_result.get("audio_base64"),
        answer_audio_format=tts_result.get("audio_format", "audio/mpeg"),
        language=app_language,
        intent=intent,
        context_used=gemini_result.get("context_used", []),
        data_status=gemini_result.get("data_status", "DEMO"),
        stt_provider=stt_result.get("provider", "unavailable"),
        tts_provider=tts_result.get("provider", "unavailable"),
        gemini_source=gemini_result.get("source", "fallback"),
        stt_error=stt_result.get("error"),
        tts_error=tts_result.get("error"),
        success=success,
        error_code=error_code,
        error_message=error_message,
    )
