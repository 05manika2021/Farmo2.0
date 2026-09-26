import logging
import base64
import struct
from typing import Optional
import httpx
from app.core.config import settings
from app.services.stt_service import normalize_language

logger = logging.getLogger("farmo.tts")

GEMINI_TTS_LANGUAGE_CODES = {
    "en": "en-IN",
    "hi": "hi-IN",
    "pa": "pa-IN",
    "gu": "gu-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
}

GEMINI_TTS_VOICE = "Kore"

# PCM parameters returned by Gemini TTS models
GEMINI_TTS_SAMPLE_RATE = 24000
GEMINI_TTS_CHANNELS = 1
GEMINI_TTS_SAMPLE_WIDTH = 2


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = GEMINI_TTS_SAMPLE_RATE) -> bytes:
    """Wrap raw PCM16 mono audio in a RIFF/WAV header so browsers can play it."""
    byte_rate = sample_rate * GEMINI_TTS_CHANNELS * GEMINI_TTS_SAMPLE_WIDTH
    block_align = GEMINI_TTS_CHANNELS * GEMINI_TTS_SAMPLE_WIDTH
    data_size = len(pcm_bytes)
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    header += b"fmt " + struct.pack(
        "<IHHIIHH", 16, 1, GEMINI_TTS_CHANNELS, sample_rate, byte_rate,
        block_align, GEMINI_TTS_SAMPLE_WIDTH * 8,
    )
    header += b"data" + struct.pack("<I", data_size)
    return header + pcm_bytes


class TTSService:
    """Text-to-Speech abstraction. Supports Gemini TTS and OpenAI TTS APIs."""

    VOICE_MAP = {
        "hi": "alloy",
        "en": "alloy",
    }

    async def synthesize(self, text: str, language: str = "hi") -> dict:
        lang = normalize_language(language)
        provider = (settings.TTS_PROVIDER or "").lower()
        if provider == "gemini":
            return await self._synthesize_gemini(text, lang)
        if provider == "openai":
            return await self._synthesize_openai(text, lang)

        return self._error_response(
            "TTS provider not configured. Set TTS_PROVIDER=gemini (and GEMINI_API_KEY) "
            "or TTS_PROVIDER=openai (and OPENAI_API_KEY) in .env.",
            lang,
        )

    async def _synthesize_gemini(self, text: str, language: str) -> dict:
        if not settings.GEMINI_API_KEY:
            return self._error_response("GEMINI_API_KEY not configured.", language)

        try:
            audio_bytes = await self._call_gemini_tts(text, language)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            return {
                "audio_base64": audio_b64,
                "audio_format": "audio/wav",
                "provider": "gemini",
                "error": None,
            }
        except Exception:
            logger.error("TTS Gemini unexpected error", exc_info=True)
            return self._error_response("Text-to-speech service unavailable.", language)

    async def _call_gemini_tts(self, text: str, language: str) -> bytes:
        """Call Gemini TTS and return playable WAV bytes.

        Runs the synchronous google-genai client in a worker thread so the
        event loop is not blocked.
        """
        import asyncio
        from google import genai
        from google.genai import types

        def _generate() -> bytes:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.generate_content(
                model=settings.GEMINI_TTS_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        language_code=GEMINI_TTS_LANGUAGE_CODES.get(language, "hi-IN"),
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=GEMINI_TTS_VOICE,
                            )
                        ),
                    ),
                ),
            )
            part = response.candidates[0].content.parts[0]
            if part.inline_data is None or not part.inline_data.data:
                raise RuntimeError("Gemini TTS returned no audio data")
            data = bytes(part.inline_data.data)
            mime = (part.inline_data.mime_type or "").lower()
            if data[:4] == b"RIFF" or "wav" in mime:
                return data
            return pcm_to_wav(data)

        return await asyncio.to_thread(_generate)

    async def _synthesize_openai(self, text: str, language: str) -> dict:
        if not settings.OPENAI_API_KEY:
            return self._error_response("OPENAI_API_KEY not configured.", language)

        try:
            voice = self.VOICE_MAP.get(language, "alloy")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.OPENAI_TTS_MODEL,
                        "input": text,
                        "voice": voice,
                        "response_format": "mp3",
                    },
                )
                response.raise_for_status()
                audio_bytes = response.content

            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            return {
                "audio_base64": audio_b64,
                "audio_format": "audio/mpeg",
                "provider": "openai",
                "error": None,
            }

        except httpx.TimeoutException:
            logger.warning("TTS OpenAI API timeout")
            return self._error_response("Text-to-speech timed out. Please try again.", language)
        except httpx.HTTPStatusError as e:
            logger.warning(f"TTS OpenAI API error: {e.response.status_code}")
            return self._error_response(f"Text-to-speech API error: {e.response.status_code}", language)
        except Exception:
            logger.error("TTS unexpected error", exc_info=True)
            return self._error_response("Text-to-speech service unavailable.", language)

    def _error_response(self, error: str, language: Optional[str] = None) -> dict:
        return {
            "audio_base64": None,
            "audio_format": "audio/mpeg",
            "provider": "unavailable",
            "error": error,
        }


tts_service = TTSService()
