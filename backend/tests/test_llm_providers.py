"""Provider-configurable LLM layer: selection, Groq generation, language
propagation through chat and voice, and credential safety."""

import io
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import settings
from app.services import llm_provider
from app.services.gemini_service import LANGUAGE_INSTRUCTIONS, SYSTEM_INSTRUCTION, classify_ai_error
from app.services.llm_provider import (
    GROQ_CHAT_URL,
    GeminiProvider,
    GroqProvider,
    LLMProviderError,
    build_provider,
    resolve_provider_name,
)
from app.utils.language import SUPPORTED_LANGUAGES, get_language_name

# A stand-in credential so these tests prove the real key never leaves the
# server, without ever reading or printing the configured one.
FAKE_GROQ_KEY = "gsk_test_do_not_leak_0123456789"

EN_ANSWER = "Onion is trading at INR 2405 per quintal at Indore Mandi."
HI_ANSWER = "इंदौर मंडी में प्याज का भाव 2405 रुपये प्रति क्विंटल है।"
PA_ANSWER = "ਇੰਦੌਰ ਮੰਡੀ ਵਿੱਚ ਪਿਆਜ਼ ਦਾ ਭਾਵ 2405 ਰੁਪਏ ਪ੍ਰਤੀ ਕੁਇੰਟਲ ਹੈ।"

ALL_LANGUAGES = list(SUPPORTED_LANGUAGES)


def _ok(text: str):
    return SimpleNamespace(
        status_code=200,
        json=lambda: {"choices": [{"message": {"content": text}}]},
    )


def _status(status: int):
    return SimpleNamespace(status_code=status, json=lambda: {"error": {"message": "boom"}})


def _reply(text: str):
    """Async stand-in for the HTTP seam returning a successful completion."""
    async def _inner(*args, **kwargs):
        return _ok(text)
    return _inner


def _use_groq(monkeypatch, model: str = "qwen/qwen3.8-27b"):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", FAKE_GROQ_KEY)
    monkeypatch.setattr(settings, "GROQ_MODEL", model)


# ─── Provider selection ─────────────────────────────────────────────────

def test_auto_selection_uses_groq_only_when_key_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "")
    monkeypatch.setattr(settings, "GROQ_API_KEY", FAKE_GROQ_KEY)
    assert resolve_provider_name() == "groq"


def test_auto_selection_keeps_gemini_without_groq_key(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    assert resolve_provider_name() == "gemini"


def test_explicit_llm_provider_is_honoured(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GROQ_API_KEY", FAKE_GROQ_KEY)
    assert resolve_provider_name() == "gemini"


def test_unknown_provider_falls_back_to_auto_selection(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "some-vendor")
    monkeypatch.setattr(settings, "GROQ_API_KEY", FAKE_GROQ_KEY)
    assert resolve_provider_name() == "groq"


def test_groq_without_key_falls_back_to_the_configured_gemini(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    provider = build_provider(gemini_client_factory=MagicMock(return_value=MagicMock()))
    assert provider is not None
    assert provider.name == "gemini"
    assert provider.is_configured() is True


def test_no_provider_is_built_when_nothing_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    assert build_provider(gemini_client_factory=MagicMock(return_value=None)) is None


def test_gemini_provider_remains_selectable_and_configured(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GROQ_API_KEY", FAKE_GROQ_KEY)
    provider = build_provider(gemini_client_factory=MagicMock(return_value=MagicMock()))
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"


# ─── Groq provider: success ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_groq_success_returns_answer_and_posts_expected_payload(monkeypatch):
    _use_groq(monkeypatch)
    captured = {}

    async def fake_chat(url, *, headers, payload):
        captured.update(url=url, headers=headers, payload=payload)
        return _ok(EN_ANSWER)

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    answer = await GroqProvider().generate(SYSTEM_INSTRUCTION, "prompt")

    assert answer == EN_ANSWER
    assert captured["url"] == GROQ_CHAT_URL
    assert captured["payload"]["model"] == "qwen/qwen3.8-27b"
    assert captured["payload"]["messages"] == [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": "prompt"},
    ]
    assert captured["payload"]["temperature"] == 0.3
    assert captured["headers"]["Authorization"] == f"Bearer {FAKE_GROQ_KEY}"


@pytest.mark.asyncio
async def test_groq_success_never_returns_a_blank_answer(monkeypatch):
    _use_groq(monkeypatch)
    monkeypatch.setattr(llm_provider, "_chat_completion", _reply("  padded  "))
    assert await GroqProvider().generate("s", "p") == "padded"


# ─── Groq provider: failure ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_groq_http_error_raises_structured_error(monkeypatch):
    _use_groq(monkeypatch)

    async def fake_chat(*a, **k):
        return _status(500)

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    with pytest.raises(LLMProviderError) as excinfo:
        await GroqProvider().generate("s", "p")

    assert excinfo.value.status_code == 500
    assert classify_ai_error(excinfo.value) == "AI_UNAVAILABLE"


@pytest.mark.asyncio
async def test_groq_rate_limit_is_classified_as_quota_exhausted(monkeypatch):
    _use_groq(monkeypatch)

    async def fake_chat(*a, **k):
        return _status(429)

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    with pytest.raises(LLMProviderError) as excinfo:
        await GroqProvider().generate("s", "p")

    assert excinfo.value.status_code == 429
    assert classify_ai_error(excinfo.value) == "AI_QUOTA_EXHAUSTED"


@pytest.mark.asyncio
async def test_groq_timeout_is_classified_as_timeout(monkeypatch):
    _use_groq(monkeypatch)

    async def fake_chat(*a, **k):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    with pytest.raises(LLMProviderError) as excinfo:
        await GroqProvider().generate("s", "p")

    assert classify_ai_error(excinfo.value) == "AI_TIMEOUT"


@pytest.mark.asyncio
async def test_groq_empty_answer_is_rejected(monkeypatch):
    _use_groq(monkeypatch)
    monkeypatch.setattr(llm_provider, "_chat_completion", _reply("   "))

    with pytest.raises(LLMProviderError) as excinfo:
        await GroqProvider().generate("s", "p")

    assert "Empty response" in str(excinfo.value)


@pytest.mark.asyncio
async def test_groq_missing_key_is_reported_not_crashed(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")

    with pytest.raises(LLMProviderError):
        await GroqProvider().generate("s", "p")


# ─── Chat endpoint routed through Groq ──────────────────────────────────

def test_chat_is_answered_by_groq_and_labels_the_source(client, monkeypatch):
    _use_groq(monkeypatch)
    captured = {}

    async def fake_chat(url, *, headers, payload):
        captured.update(payload)
        return _ok(EN_ANSWER)

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "What is the price of onion?", "language": "en", "crop": "onion"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "groq"
    assert data["answer"].startswith(EN_ANSWER)
    assert "Status:" in data["answer"]
    assert data["error_code"] is None
    assert data["error_message"] is None

    system = captured["messages"][0]["content"]
    prompt = captured["messages"][1]["content"]
    assert SYSTEM_INSTRUCTION in system
    assert LANGUAGE_INSTRUCTIONS["en"] in system
    assert "Respond in English." in prompt


def test_chat_groq_failure_returns_localized_error_not_blank(client, monkeypatch):
    _use_groq(monkeypatch)

    async def fake_chat(*a, **k):
        return _status(500)

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "What is the price of onion?", "language": "hi", "crop": "onion"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "fallback"
    assert data["error_code"] == "AI_UNAVAILABLE"
    assert data["error_message"]
    assert data["answer"].strip()


# ─── Selected language reaches the provider and comes back ──────────────

@pytest.mark.parametrize("language", ALL_LANGUAGES)
def test_selected_language_is_propagated_to_groq(client, monkeypatch, language):
    _use_groq(monkeypatch)
    captured = {}

    async def fake_chat(url, *, headers, payload):
        captured.update(payload)
        return _ok("jawab")

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "What is the price of onion?", "language": language, "crop": "onion"},
    )

    assert resp.status_code == 200
    assert resp.json()["language"] == language

    system = captured["messages"][0]["content"]
    prompt = captured["messages"][1]["content"]
    assert LANGUAGE_INSTRUCTIONS[language] in system
    assert f"Respond in {get_language_name(language)}." in prompt
    assert f"Respond in {language}." not in prompt


@pytest.mark.parametrize(("language", "answer"), [("hi", HI_ANSWER), ("pa", PA_ANSWER)])
def test_groq_hindi_and_punjabi_answers_are_preserved(client, monkeypatch, language, answer):
    _use_groq(monkeypatch)

    async def fake_chat(*a, **k):
        return _ok(answer)

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    resp = client.post(
        "/api/v1/chat",
        json={"message": "What is the price of onion?", "language": language, "crop": "onion"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == language
    assert answer in data["answer"]


# ─── Voice: STT -> Groq -> TTS ──────────────────────────────────────────

def _post_pipeline(client, *, language: str, transcribed: str, answer: str,
                   tts_audio: str = "aGVsbG8=", stt_provider: str = "groq"):
    audio_file = io.BytesIO(b"fake-audio")
    audio_file.name = "query.wav"

    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": transcribed,
            "language": language,
            "confidence": 0.95,
            "provider": stt_provider,
            "error": None,
        })
        with patch("app.api.routes.voice.tts_service") as mock_tts:
            mock_tts.synthesize = AsyncMock(return_value={
                "audio_base64": tts_audio,
                "audio_format": "mp3",
                "provider": "gemini",
                "error": None,
            })
            return client.post(
                "/api/v1/voice/pipeline",
                files={"audio": ("query.wav", audio_file, "audio/wav")},
                data={"language": language, "crop": "onion"},
            )


def test_voice_pipeline_runs_stt_then_groq_then_tts(client, monkeypatch):
    _use_groq(monkeypatch)
    captured = {}

    async def fake_chat(url, *, headers, payload):
        captured.update(payload)
        return _ok(PA_ANSWER)

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    resp = _post_pipeline(
        client, language="pa", transcribed="Aaj piyaz da bhav ki hai?", answer=PA_ANSWER
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["gemini_source"] == "groq"
    assert data["stt_provider"] == "groq"
    assert data["tts_provider"] == "gemini"
    assert data["answer_audio_base64"] == "aGVsbG8="
    assert data["answer_text"].startswith(PA_ANSWER)
    assert data["language"] == "pa"
    assert data["success"] is True
    assert data["error_code"] is None
    assert "Respond in Punjabi." in captured["messages"][1]["content"]


def test_voice_pipeline_when_groq_fails_returns_structured_localized_error(client, monkeypatch):
    _use_groq(monkeypatch)

    async def fake_chat(*a, **k):
        return _status(429)

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    resp = _post_pipeline(client, language="hi", transcribed="Pyaz ka bhav kya hai?", answer="")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error_code"] == "AI_QUOTA_EXHAUSTED"
    assert data["error_message"]
    assert data["gemini_source"] == "fallback"
    assert data["answer_text"].strip()
    assert data["answer_audio_base64"]


# ─── Credentials never leave the server ─────────────────────────────────

def test_groq_key_is_never_returned_to_the_client(client, monkeypatch):
    _use_groq(monkeypatch)

    async def fake_chat(*a, **k):
        return _ok(EN_ANSWER)

    monkeypatch.setattr(llm_provider, "_chat_completion", fake_chat)

    chat_resp = client.post(
        "/api/v1/chat",
        json={"message": "What is the price of onion?", "language": "en", "crop": "onion"},
    )
    assert chat_resp.status_code == 200
    assert FAKE_GROQ_KEY not in chat_resp.text

    voice_resp = _post_pipeline(client, language="en", transcribed="price?", answer=EN_ANSWER)
    assert voice_resp.status_code == 200
    assert FAKE_GROQ_KEY not in voice_resp.text

    if settings.GEMINI_API_KEY:
        assert settings.GEMINI_API_KEY not in chat_resp.text


def test_groq_key_is_never_written_to_logs(client, monkeypatch, caplog):
    _use_groq(monkeypatch)

    async def leaky_chat(*a, **k):
        raise httpx.ConnectError(f"connect failed for {FAKE_GROQ_KEY}")

    monkeypatch.setattr(llm_provider, "_chat_completion", leaky_chat)

    with caplog.at_level(logging.ERROR):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "What is the price of onion?", "language": "en", "crop": "onion"},
        )

    assert resp.status_code == 200
    assert FAKE_GROQ_KEY not in caplog.text
    assert FAKE_GROQ_KEY not in resp.text

    if settings.GEMINI_API_KEY:
        assert settings.GEMINI_API_KEY not in caplog.text


def test_frontend_environment_never_receives_groq_credentials():
    # The backend reads the key from its own .env; nothing in the Next.js
    # public namespace may ever carry it.
    from pathlib import Path
    frontend = Path(__file__).resolve().parents[2]
    for pattern in (".env.local", ".env", ".env.production"):
        env_file = frontend / pattern
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("NEXT_PUBLIC_") and "GROQ" in stripped.upper():
                pytest.fail(f"{env_file.name} exposes a GROQ variable to the browser")
