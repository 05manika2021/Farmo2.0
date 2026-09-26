import logging
from typing import Optional
import httpx
from app.core.config import settings
from app.utils.language import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, is_supported_language

logger = logging.getLogger("farmo.stt")

ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/webm", "audio/ogg",
    "audio/flac", "audio/x-flac",
}
MAX_AUDIO_SIZE_MB = 25

GROQ_TRANSCRIPTIONS_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"


def normalize_language(language: Optional[str], fallback: Optional[str] = None) -> str:
    """Resolve a requested language to a supported 2-letter code.

    Selected app language has priority; STT_LANGUAGE (or DEFAULT_LANGUAGE)
    is the fallback when the requested value is missing or unsupported.
    """
    for candidate in (language, fallback, settings.STT_LANGUAGE, DEFAULT_LANGUAGE):
        if not candidate:
            continue
        code = candidate.strip().lower().split("-")[0]
        if is_supported_language(code):
            return code
    return DEFAULT_LANGUAGE


class STTService:
    """Speech-to-Text abstraction. Supports Groq Whisper and OpenAI Whisper APIs."""

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        language: str = "hi",
    ) -> dict:
        if content_type not in ALLOWED_AUDIO_TYPES:
            return self._error_response(
                f"Unsupported audio type: {content_type}. "
                f"Allowed: {', '.join(sorted(ALLOWED_AUDIO_TYPES))}",
                language,
            )

        size_mb = len(audio_bytes) / (1024 * 1024)
        if size_mb > MAX_AUDIO_SIZE_MB:
            return self._error_response(
                f"Audio file too large ({size_mb:.1f}MB). Maximum: {MAX_AUDIO_SIZE_MB}MB.",
                language,
            )

        lang = normalize_language(language)
        provider = (settings.STT_PROVIDER or "").lower()
        if provider == "groq":
            return await self._transcribe_groq(audio_bytes, filename, content_type, lang)
        if provider == "openai":
            return await self._transcribe_openai(audio_bytes, filename, content_type, lang)

        return self._error_response(
            "STT provider not configured. Set STT_PROVIDER=groq (and GROQ_API_KEY) "
            "or STT_PROVIDER=openai (and OPENAI_API_KEY) in .env.",
            lang,
        )

    async def _transcribe_groq(
        self, audio_bytes: bytes, filename: str, content_type: str, language: str
    ) -> dict:
        if not settings.GROQ_API_KEY:
            return self._error_response("GROQ_API_KEY not configured.", language)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    GROQ_TRANSCRIPTIONS_URL,
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                    files={"file": (filename, audio_bytes, content_type)},
                    data={
                        "model": settings.GROQ_STT_MODEL,
                        "language": language,
                        "response_format": "verbose_json",
                    },
                )
                response.raise_for_status()
                data = response.json()

            return {
                "transcribed_text": data.get("text", ""),
                "language": language,
                "confidence": None,
                "provider": "groq",
                "error": None,
            }

        except httpx.TimeoutException:
            logger.warning("STT Groq API timeout")
            return self._error_response("Speech recognition timed out. Please try again.", language)
        except httpx.HTTPStatusError as e:
            logger.warning(f"STT Groq API error: {e.response.status_code}")
            return self._error_response(f"Speech recognition API error: {e.response.status_code}", language)
        except Exception:
            logger.error("STT unexpected error", exc_info=True)
            return self._error_response("Speech recognition service unavailable.", language)

    async def _transcribe_openai(
        self, audio_bytes: bytes, filename: str, content_type: str, language: str
    ) -> dict:
        if not settings.OPENAI_API_KEY:
            return self._error_response("OPENAI_API_KEY not configured.", language)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    OPENAI_TRANSCRIPTIONS_URL,
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    files={"file": (filename, audio_bytes, content_type)},
                    data={
                        "model": "whisper-1",
                        "language": language,
                        "response_format": "verbose_json",
                    },
                )
                response.raise_for_status()
                data = response.json()

            return {
                "transcribed_text": data.get("text", ""),
                "language": data.get("language", language),
                "confidence": None,
                "provider": "openai",
                "error": None,
            }

        except httpx.TimeoutException:
            logger.warning("STT OpenAI API timeout")
            return self._error_response("Speech recognition timed out. Please try again.", language)
        except httpx.HTTPStatusError as e:
            logger.warning(f"STT OpenAI API error: {e.response.status_code}")
            return self._error_response(f"Speech recognition API error: {e.response.status_code}", language)
        except Exception:
            logger.error("STT unexpected error", exc_info=True)
            return self._error_response("Speech recognition service unavailable.", language)

    def _error_response(self, error: str, language: Optional[str] = None) -> dict:
        return {
            "transcribed_text": "",
            "language": normalize_language(language),
            "confidence": None,
            "provider": "unavailable",
            "error": error,
        }


stt_service = STTService()
