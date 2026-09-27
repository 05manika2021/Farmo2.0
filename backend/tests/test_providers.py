"""Mocked tests for the four configured providers:
Gemini (chat + TTS), Groq (STT), 2Factor (SMS OTP), MapTiler (geocoding).

No test in this file performs a real network call.
"""

import base64
import io
import logging
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
import pytest

from app.services.stt_service import normalize_language
from app.utils.language import SUPPORTED_LANGUAGES


LANGUAGE_CODES = list(SUPPORTED_LANGUAGES.keys())


# ─── normalize_language / selected-language priority ──────────────────

def test_normalize_requested_language_wins():
    assert normalize_language("pa") == "pa"
    assert normalize_language("bn", fallback="en") == "bn"
    assert normalize_language("gu-IN") == "gu"


def test_normalize_falls_back_when_unsupported():
    with patch("app.services.stt_service.settings") as s:
        s.STT_LANGUAGE = "hi"
        assert normalize_language("xx") == "hi"
        assert normalize_language("xx", fallback="mr") == "mr"
        assert normalize_language(None) == "hi"
        s.STT_LANGUAGE = "kl"  # unsupported → DEFAULT_LANGUAGE
        assert normalize_language(None) == "hi"


# ─── Groq STT ─────────────────────────────────────────────────────────

def _groq_mock(text="Mere paas 5 quintal pyaaz hai", status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"text": text, "language": "hindi"})
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


@pytest.mark.asyncio
async def test_stt_groq_success():
    from app.services.stt_service import STTService, GROQ_TRANSCRIPTIONS_URL
    mc = _groq_mock()
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = "groq"
        s.GROQ_API_KEY = "gsk_test_key"
        s.GROQ_STT_MODEL = "whisper-large-v3-turbo"
        s.STT_LANGUAGE = "hi"
        with patch("app.services.stt_service.httpx.AsyncClient", return_value=mc):
            result = await STTService().transcribe(
                b"fake-audio", "q.wav", "audio/wav", "hi"
            )
    assert result["error"] is None
    assert result["provider"] == "groq"
    assert result["transcribed_text"] == "Mere paas 5 quintal pyaaz hai"
    assert result["language"] == "hi"

    args, kwargs = mc.post.call_args
    assert args[0] == GROQ_TRANSCRIPTIONS_URL
    assert kwargs["headers"]["Authorization"] == "Bearer gsk_test_key"
    assert kwargs["data"]["model"] == "whisper-large-v3-turbo"
    assert kwargs["data"]["language"] == "hi"
    assert kwargs["data"]["response_format"] == "verbose_json"
    assert kwargs["files"]["file"][0] == "q.wav"


@pytest.mark.asyncio
@pytest.mark.parametrize("lang", LANGUAGE_CODES)
async def test_stt_groq_sends_supported_language(lang):
    from app.services.stt_service import STTService
    mc = _groq_mock(text=f"query in {lang}")
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = "groq"
        s.GROQ_API_KEY = "gsk_test_key"
        s.GROQ_STT_MODEL = "whisper-large-v3-turbo"
        s.STT_LANGUAGE = "hi"
        with patch("app.services.stt_service.httpx.AsyncClient", return_value=mc):
            result = await STTService().transcribe(b"a", "q.wav", "audio/wav", lang)
    assert result["error"] is None
    assert result["language"] == lang
    assert mc.post.call_args.kwargs["data"]["language"] == lang


@pytest.mark.asyncio
async def test_stt_groq_unsupported_language_falls_back():
    from app.services.stt_service import STTService
    mc = _groq_mock()
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = "groq"
        s.GROQ_API_KEY = "gsk_test_key"
        s.GROQ_STT_MODEL = "whisper-large-v3-turbo"
        s.STT_LANGUAGE = "mr"
        with patch("app.services.stt_service.httpx.AsyncClient", return_value=mc):
            result = await STTService().transcribe(b"a", "q.wav", "audio/wav", "xx")
    assert result["error"] is None
    assert result["language"] == "mr"
    assert mc.post.call_args.kwargs["data"]["language"] == "mr"


@pytest.mark.asyncio
async def test_stt_groq_missing_key():
    from app.services.stt_service import STTService
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = "groq"
        s.GROQ_API_KEY = None
        result = await STTService().transcribe(b"a", "q.wav", "audio/wav", "hi")
    assert result["error"] is not None
    assert "groq_api_key not configured" in result["error"].lower()
    assert result["provider"] == "unavailable"


@pytest.mark.asyncio
async def test_stt_groq_timeout():
    from app.services.stt_service import STTService
    mc = AsyncMock()
    mc.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mc.__aenter__ = AsyncMock(return_value=mc)
    mc.__aexit__ = AsyncMock(return_value=False)
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = "groq"
        s.GROQ_API_KEY = "gsk_test_key"
        s.GROQ_STT_MODEL = "whisper-large-v3-turbo"
        with patch("app.services.stt_service.httpx.AsyncClient", return_value=mc):
            result = await STTService().transcribe(b"a", "q.wav", "audio/wav", "hi")
    assert result["error"] is not None
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
async def test_stt_groq_http_error_no_key_in_response():
    from app.services.stt_service import STTService
    resp = MagicMock()
    resp.status_code = 401
    err = httpx.HTTPStatusError(
        "401 Unauthorized for url: https://api.groq.com/...key=gsk_secret",
        request=MagicMock(),
        response=resp,
    )
    resp.raise_for_status = MagicMock(side_effect=err)
    mc = AsyncMock()
    mc.post = AsyncMock(return_value=resp)
    mc.__aenter__ = AsyncMock(return_value=mc)
    mc.__aexit__ = AsyncMock(return_value=False)
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = "groq"
        s.GROQ_API_KEY = "gsk_secret"
        s.GROQ_STT_MODEL = "whisper-large-v3-turbo"
        with patch("app.services.stt_service.httpx.AsyncClient", return_value=mc):
            result = await STTService().transcribe(b"a", "q.wav", "audio/wav", "hi")
    assert result["error"] is not None
    assert "401" in result["error"]
    assert "gsk_secret" not in result["error"]


# ─── Gemini TTS ───────────────────────────────────────────────────────

def _gemini_tts_response(data: bytes, mime: str):
    part = MagicMock()
    part.inline_data.data = data
    part.inline_data.mime_type = mime
    candidate = MagicMock()
    candidate.content.parts = [part]
    response = MagicMock()
    response.candidates = [candidate]
    return response


@pytest.mark.asyncio
async def test_tts_gemini_pcm_wrapped_as_wav():
    from app.services.tts_service import TTSService
    pcm = b"\x01\x02" * 480
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = "gemini"
        s.GEMINI_API_KEY = "fake-gemini-key"
        s.GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
        with patch("google.genai.Client") as cls:
            cls.return_value.models.generate_content = MagicMock(
                return_value=_gemini_tts_response(pcm, "audio/L16;rate=24000")
            )
            result = await TTSService().synthesize("Namaste kisan ji", "hi")
    assert result["error"] is None
    assert result["provider"] == "gemini"
    assert result["audio_format"] == "audio/wav"
    decoded = base64.b64decode(result["audio_base64"])
    assert decoded[:4] == b"RIFF"
    assert decoded[8:12] == b"WAVE"
    assert decoded[44:] == pcm

    kwargs = cls.return_value.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-2.5-flash-preview-tts"
    assert kwargs["config"].response_modalities == ["AUDIO"]
    speech = kwargs["config"].speech_config
    assert speech.language_code == "hi-IN"
    assert speech.voice_config.prebuilt_voice_config.voice_name == "Kore"


@pytest.mark.asyncio
async def test_tts_gemini_wav_passthrough():
    from app.services.tts_service import TTSService
    wav = b"RIFF$\x00\x00\x00WAVEfmt " + b"\x00" * 30
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = "gemini"
        s.GEMINI_API_KEY = "fake-gemini-key"
        s.GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
        with patch("google.genai.Client") as cls:
            cls.return_value.models.generate_content = MagicMock(
                return_value=_gemini_tts_response(wav, "audio/wav")
            )
            result = await TTSService().synthesize("Hello", "en")
    assert result["error"] is None
    decoded = base64.b64decode(result["audio_base64"])
    assert decoded == wav


@pytest.mark.asyncio
@pytest.mark.parametrize("lang,expected_code", [
    ("en", "en-IN"), ("hi", "hi-IN"), ("pa", "pa-IN"),
    ("gu", "gu-IN"), ("mr", "mr-IN"), ("bn", "bn-IN"),
])
async def test_tts_gemini_language_code_per_language(lang, expected_code):
    from app.services.tts_service import TTSService
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = "gemini"
        s.GEMINI_API_KEY = "fake-gemini-key"
        s.GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
        with patch("google.genai.Client") as cls:
            cls.return_value.models.generate_content = MagicMock(
                return_value=_gemini_tts_response(b"RIFF", "audio/wav")
            )
            await TTSService().synthesize("Test", lang)
    speech = cls.return_value.models.generate_content.call_args.kwargs["config"].speech_config
    assert speech.language_code == expected_code


@pytest.mark.asyncio
async def test_tts_gemini_missing_key():
    from app.services.tts_service import TTSService
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = "gemini"
        s.GEMINI_API_KEY = None
        result = await TTSService().synthesize("Hello", "hi")
    assert result["audio_base64"] is None
    assert result["error"] is not None
    assert "gemini_api_key not configured" in result["error"].lower()
    assert result["provider"] == "unavailable"


@pytest.mark.asyncio
async def test_tts_gemini_no_audio_data():
    from app.services.tts_service import TTSService
    response = MagicMock()
    part = MagicMock()
    part.inline_data = None
    response.candidates = [MagicMock(content=MagicMock(parts=[part]))]
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = "gemini"
        s.GEMINI_API_KEY = "fake-gemini-key"
        s.GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
        with patch("google.genai.Client") as cls:
            cls.return_value.models.generate_content = MagicMock(return_value=response)
            result = await TTSService().synthesize("Hello", "hi")
    assert result["audio_base64"] is None
    assert result["error"] is not None
    assert "fake-gemini-key" not in str(result["error"])


@pytest.mark.asyncio
async def test_tts_gemini_client_exception_unavailable():
    from app.services.tts_service import TTSService
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = "gemini"
        s.GEMINI_API_KEY = "fake-gemini-key"
        s.GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
        with patch("google.genai.Client") as cls:
            cls.return_value.models.generate_content = MagicMock(
                side_effect=RuntimeError("boom fake-gemini-key")
            )
            result = await TTSService().synthesize("Hello", "hi")
    assert result["audio_base64"] is None
    assert result["error"] is not None
    assert "unavailable" in result["error"].lower()
    assert "fake-gemini-key" not in str(result["error"])


@pytest.mark.asyncio
async def test_tts_no_provider():
    from app.services.tts_service import TTSService
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = None
        result = await TTSService().synthesize("Hello", "hi")
    assert result["error"] is not None
    assert "not configured" in result["error"].lower()


# ─── Voice pipeline: selected language wins for STT + Gemini + TTS ───

@pytest.mark.parametrize("lang", LANGUAGE_CODES)
def test_pipeline_language_priority_for_all_languages(client, lang):
    with patch("app.api.routes.voice.stt_service") as mock_stt, \
         patch("app.api.routes.voice.gemini_service") as mock_gem, \
         patch("app.api.routes.voice.tts_service") as mock_tts:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "Onion ka bhav kya hai",
            "language": "en",  # STT-detected language must NOT win
            "confidence": 0.9,
            "provider": "groq",
            "error": None,
        })
        mock_gem.generate_response = AsyncMock(return_value={
            "answer": "Onion ka bhav 2400 rupaye prati quintal hai.",
            "language": lang,
            "intent": "price",
            "context_used": ["price"],
            "data_status": "LIVE",
            "source": "gemini",
        })
        mock_tts.synthesize = AsyncMock(return_value={
            "audio_base64": "dGVzdA==",
            "audio_format": "wav",
            "provider": "gemini",
            "error": None,
        })
        audio = io.BytesIO(b"fake-audio")
        audio.name = "q.wav"
        resp = client.post(
            "/api/v1/voice/pipeline",
            files={"audio": ("q.wav", audio, "audio/wav")},
            data={"language": lang, "crop": "Wheat", "quantity": "5"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == lang
    assert mock_stt.transcribe.call_args.kwargs["language"] == lang
    assert mock_gem.generate_response.call_args.kwargs["language"] == lang
    assert mock_gem.generate_response.call_args.kwargs["crop"] == "Wheat"
    assert mock_tts.synthesize.call_args.kwargs["language"] == lang
    assert data["tts_provider"] == "gemini"


def test_pipeline_unsupported_language_falls_back(client):
    with patch("app.services.stt_service.settings") as s, \
         patch("app.api.routes.voice.stt_service") as mock_stt, \
         patch("app.api.routes.voice.gemini_service") as mock_gem, \
         patch("app.api.routes.voice.tts_service") as mock_tts:
        s.STT_LANGUAGE = "mr"
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "Kasa aahai?",
            "language": "mr",
            "confidence": 0.9,
            "provider": "groq",
            "error": None,
        })
        mock_gem.generate_response = AsyncMock(return_value={
            "answer": "Bhav 2400 ahe.",
            "language": "mr",
            "intent": "price",
            "context_used": [],
            "data_status": "DEMO",
            "source": "fallback",
        })
        mock_tts.synthesize = AsyncMock(return_value={
            "audio_base64": None,
            "audio_format": "wav",
            "provider": "gemini",
            "error": None,
        })
        audio = io.BytesIO(b"fake-audio")
        audio.name = "q.wav"
        resp = client.post(
            "/api/v1/voice/pipeline",
            files={"audio": ("q.wav", audio, "audio/wav")},
            data={"language": "zz"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "mr"
    assert mock_stt.transcribe.call_args.kwargs["language"] == "mr"


# ─── Gemini chat: system instruction + answer used ────────────────────

def test_chat_uses_system_instruction_and_returns_answer(client):
    fake_response = MagicMock()
    fake_response.text = "Onion ka bhaav aaj 2400 rupaye prati quintal hai."
    fake_client = MagicMock()
    fake_client.models.generate_content = MagicMock(return_value=fake_response)

    from app.services.gemini_service import gemini_service, SYSTEM_INSTRUCTION
    with patch.object(type(gemini_service), "_get_client", return_value=fake_client):
        resp = client.post(
            "/api/v1/chat",
            json={
                "message": "What is the price of onion?",
                "language": "en",
                "crop": "onion",
                "latitude": 22.7196,
                "longitude": 75.8577,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    # P8: every answer carries its data status after the answer body.
    assert data["answer"].startswith("Onion ka bhaav aaj 2400 rupaye prati quintal hai.")
    assert "Status:" in data["answer"]
    assert data["source"] == "gemini"

    kwargs = fake_client.models.generate_content.call_args.kwargs
    sent_system = kwargs["config"]["system_instruction"]
    # Safety rules must still be present, and P1 adds an explicit language rule.
    assert SYSTEM_INSTRUCTION in sent_system
    assert "English" in sent_system
    assert kwargs["config"]["temperature"] == 0.3
    assert "Respond in English." in kwargs["contents"]


def test_chat_prompt_uses_language_name_not_code(client):
    fake_response = MagicMock()
    fake_response.text = "Jawab"
    fake_client = MagicMock()
    fake_client.models.generate_content = MagicMock(return_value=fake_response)

    from app.services.gemini_service import gemini_service
    with patch.object(type(gemini_service), "_get_client", return_value=fake_client):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "Onion ka bhav kya hai?", "language": "bn", "crop": "onion"},
        )
    assert resp.status_code == 200
    prompt = fake_client.models.generate_content.call_args.kwargs["contents"]
    assert "Respond in Bengali." in prompt
    assert "Respond in bn." not in prompt


# ─── 2Factor: no API key / OTP ever reaches logs or responses ─────────

LEAK_KEY = "leak-me-api-key-0123456789"
LEAK_OTP = "842913"
LEAK_PHONE = "9876543210"


def _leaky_http_error():
    url = f"https://2factor.in/API/V1/{LEAK_KEY}/SMS/{LEAK_PHONE}/{LEAK_OTP}/OTP"
    req = httpx.Request("GET", url)
    resp = httpx.Response(400, request=req, text="Bad Request")
    return httpx.HTTPStatusError(
        f"400 Bad Request for url: {url}",
        request=req,
        response=resp,
    )


def test_twofactor_exception_does_not_leak_key_or_otp(caplog):
    from app.services.twofactor_otp import TwoFactorOTP
    with patch("app.services.twofactor_otp.settings") as s, \
         patch("app.services.twofactor_otp.httpx.get", side_effect=_leaky_http_error()):
        s.TWOFACTOR_API_KEY = LEAK_KEY
        s.TWOFACTOR_SMS_TEMPLATE = "OTP"
        with caplog.at_level(logging.DEBUG, logger="farmo.twofactor"):
            result = TwoFactorOTP().send(LEAK_PHONE, LEAK_OTP)

    assert result["success"] is False
    assert LEAK_KEY not in str(result)
    assert LEAK_OTP not in str(result)

    log_text = caplog.text
    assert LEAK_KEY not in log_text
    assert LEAK_OTP not in log_text
    assert "***" in log_text


def test_twofactor_response_body_never_contains_key_or_otp(caplog):
    from app.services.twofactor_otp import TwoFactorOTP
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Status": "Success", "Details": "sess-abc-123"}
    mock_response.raise_for_status = MagicMock()
    with patch("app.services.twofactor_otp.settings") as s, \
         patch("app.services.twofactor_otp.httpx.get", return_value=mock_response):
        s.TWOFACTOR_API_KEY = LEAK_KEY
        s.TWOFACTOR_SMS_TEMPLATE = "OTP"
        with caplog.at_level(logging.DEBUG, logger="farmo.twofactor"):
            result = TwoFactorOTP().send(LEAK_PHONE, LEAK_OTP)

    assert result["success"] is True
    body = str(result)
    assert LEAK_KEY not in body
    assert LEAK_OTP not in body
    assert LEAK_KEY not in caplog.text
    assert LEAK_OTP not in caplog.text


def test_twofactor_error_response_no_key_or_otp():
    from app.services.twofactor_otp import TwoFactorOTP
    with patch("app.services.twofactor_otp.settings") as s:
        s.TWOFACTOR_API_KEY = LEAK_KEY
        result = TwoFactorOTP().send("bad-phone", LEAK_OTP)
    assert result["success"] is False
    assert LEAK_KEY not in str(result)
    assert LEAK_OTP not in str(result)
