"""Tests for the AI experience fixes: language propagation, intent detection,
knowledge layer, data_status labelling and malformed-input handling."""
import pytest
from unittest.mock import MagicMock, patch

from app.services.gemini_service import (
    gemini_service,
    LANGUAGE_INSTRUCTIONS,
    SYSTEM_INSTRUCTION,
    failure_message,
)
from app.utils.language import SUPPORTED_LANGUAGES


ALL_LANGUAGES = list(SUPPORTED_LANGUAGES.keys())


# ─── P1: every supported language gets an explicit instruction ─────────

def test_every_supported_language_has_instruction():
    assert set(LANGUAGE_INSTRUCTIONS) == set(ALL_LANGUAGES)
    for code in ALL_LANGUAGES:
        assert "ONLY" in LANGUAGE_INSTRUCTIONS[code]


def test_instruction_forbids_english_for_non_english():
    for code in ("hi", "pa", "gu", "mr", "bn"):
        text = LANGUAGE_INSTRUCTIONS[code].lower()
        assert "do not respond in english" in text


@pytest.mark.parametrize("language", ALL_LANGUAGES)
def test_system_instruction_carries_language_rule(client, language):
    fake_response = MagicMock()
    fake_response.text = "jawab"
    fake_client = MagicMock()
    fake_client.models.generate_content = MagicMock(return_value=fake_response)

    with patch.object(type(gemini_service), "_get_client", return_value=fake_client):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "What is the price of onion?", "language": language, "crop": "onion"},
        )
    assert resp.status_code == 200
    sent = fake_client.models.generate_content.call_args.kwargs["config"]["system_instruction"]
    assert SYSTEM_INSTRUCTION in sent
    assert LANGUAGE_INSTRUCTIONS[language] in sent


@pytest.mark.parametrize("language", ALL_LANGUAGES)
def test_prompt_uses_language_name_never_code(client, language):
    fake_response = MagicMock()
    fake_response.text = "jawab"
    fake_client = MagicMock()
    fake_client.models.generate_content = MagicMock(return_value=fake_response)

    with patch.object(type(gemini_service), "_get_client", return_value=fake_client):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "What is the price of onion?", "language": language, "crop": "onion"},
        )
    assert resp.status_code == 200
    prompt = fake_client.models.generate_content.call_args.kwargs["contents"]
    name = SUPPORTED_LANGUAGES[language]
    assert f"Respond in {name}." in prompt
    assert f"Respond in {language}." not in prompt


# ─── P2/P3: intent detection ──────────────────────────────────────────

def test_intent_scheme_detected():
    assert gemini_service.detect_intent("Tell me about PM-KISAN scheme") == "scheme"
    assert gemini_service.detect_intent("Which crop insurance scheme can I get?") == "scheme"
    assert gemini_service.detect_intent("Kya yojana milegi?") == "scheme"
    assert gemini_service.detect_intent("Soil health card kaise milta hai?") == "scheme"


def test_intent_existing_buckets_unchanged():
    assert gemini_service.detect_intent("What is the price of onion?") == "price"
    assert gemini_service.detect_intent("Kahan bechna faydemand hai?") == "market"
    assert gemini_service.detect_intent("Abhi bechu ya ruk jaun?") == "recommendation"
    assert gemini_service.detect_intent("Kitna profit hoga?") == "profit"
    assert gemini_service.detect_intent("Transport kitna lagega?") == "transport"
    assert gemini_service.detect_intent("Mausam kaisa hai?") == "weather"
    assert gemini_service.detect_intent("Hello") == "general"


# ─── P2: honest "no data" reply, localized ────────────────────────────

@pytest.mark.parametrize("language", ALL_LANGUAGES)
def test_no_data_reply_is_localized(client, language):
    from app.services.gemini_service import _t
    resp = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the price of saffron?",
            "language": language,
            "crop": "saffron",
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "price"
    assert data["data_status"] == "UNAVAILABLE"
    assert _t("no_data", language) in data["answer"]


def test_never_says_be_more_specific(client):
    for language in ALL_LANGUAGES:
        resp = client.post(
            "/api/v1/chat",
            json={
                "message": "What is the price of saffron?",
                "language": language,
                "crop": "saffron",
                "latitude": 22.7196,
                "longitude": 75.8577,
            },
        )
        answer = resp.json()["answer"].lower()
        assert "be more specific" not in answer
        assert "data taiyar hai" not in answer


# ─── P6: knowledge layer ──────────────────────────────────────────────

def test_schemes_json_is_well_formed():
    from app.services.knowledge_service import knowledge_service
    schemes = knowledge_service.get_schemes()
    assert len(schemes) >= 5
    for s in schemes:
        assert s["name"]
        assert s["official_url"].startswith("https://")
        assert s["eligibility_summary"]
        assert s["benefits"]
        assert s["application_instructions"]
        assert s["verification"] == "VERIFIED"
        assert s["last_verified"]


def test_faq_and_advisory_json_are_well_formed():
    from app.services.knowledge_service import knowledge_service
    faqs = knowledge_service.get_faq()
    advisories = knowledge_service.get_advisories()
    assert len(faqs) >= 5
    assert len(advisories) >= 3
    for f in faqs:
        assert f["answer"] and f["verification"] in ("VERIFIED", "GENERAL GUIDANCE")
    for a in advisories:
        assert a["guidance"] and a["verification"] in ("VERIFIED", "GENERAL GUIDANCE")


def test_scheme_question_answers_from_knowledge(client):
    resp = client.post(
        "/api/v1/chat",
        json={"message": "Tell me about PM-KISAN scheme", "language": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "scheme"
    assert "scheme" in data["context_used"]
    assert "6,000" in data["answer"] or "6000" in data["answer"]
    assert "pmkisan.gov.in" in data["answer"]


def test_farmo_faq_answered_from_knowledge(client):
    resp = client.post(
        "/api/v1/chat",
        json={"message": "What does Farmo do?", "language": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "general"
    assert "faq" in data["context_used"]
    assert "decide where and when to sell" in data["answer"]


def test_scheme_answer_never_decides_eligibility(client):
    resp = client.post(
        "/api/v1/chat",
        json={"message": "Am I eligible for PM-KISAN?", "language": "en"},
    )
    assert resp.status_code == 200
    answer = resp.json()["answer"].lower()
    assert "you are eligible" not in answer
    assert "you are not eligible" not in answer


# ─── P7/P8: data_status on every answer ───────────────────────────────

def test_market_answer_marked_demo(client):
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
    data = resp.json()
    assert data["data_status"] == "DEMO"
    assert "Status: DEMO" in data["answer"]


def test_weather_answer_has_status_and_never_fabricates(client):
    resp = client.post(
        "/api/v1/chat",
        json={
            "message": "Will it rain today?",
            "language": "en",
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    data = resp.json()
    assert data["intent"] == "weather"
    # Provider is disabled in tests, so the answer must say it is unavailable.
    assert data["data_status"] == "UNAVAILABLE"
    assert data["context_used"] == ["weather_unavailable"]


def test_no_context_answer_marked_unavailable(client):
    resp = client.post("/api/v1/chat", json={"message": "Hello", "language": "en"})
    data = resp.json()
    assert data["data_status"] in ("DEMO", "LIVE", "UNAVAILABLE")


# ─── P5: voice replies ────────────────────────────────────────────────

@pytest.mark.parametrize("language", ALL_LANGUAGES)
def test_failure_message_localized(language):
    msg = failure_message(language)
    assert isinstance(msg, str) and msg
    if language == "en":
        assert "could not process" in msg
    else:
        assert msg != failure_message("en")


def test_voice_pipeline_returns_localized_answer(client):
    import io
    audio_file = io.BytesIO(b"fake-audio")
    audio_file.name = "q.wav"
    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock_ok()
        with patch("app.api.routes.voice.gemini_service") as mock_gem:
            mock_gem.generate_response = _async_return({
                "answer": "नमस्ते, आज का भाव 2400 रुपये है।",
                "language": "hi",
                "intent": "price",
                "context_used": ["current_price"],
                "data_status": "DEMO",
                "source": "fallback",
            })
            with patch("app.api.routes.voice.tts_service") as mock_tts:
                mock_tts.synthesize = _async_return({
                    "audio_base64": None,
                    "audio_format": "mp3",
                    "provider": "unavailable",
                    "error": "Text-to-speech service unavailable.",
                })
                resp = client.post(
                    "/api/v1/voice/pipeline",
                    files={"audio": ("q.wav", audio_file, "audio/wav")},
                    data={"language": "hi", "crop": "onion", "quantity": "5"},
                )
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "hi"
    assert data["answer_text"].startswith("नमस्ते")
    assert data["data_status"] == "DEMO"
    # Language must be forwarded to Gemini.
    assert mock_gem.generate_response.call_args.kwargs["language"] == "hi"


# ─── P10: malformed input returns 422, never 500 ──────────────────────

def test_transcribe_multipart_body_returns_422_not_500(client):
    resp = client.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("q.wav", b"\x00\x01\x02binary", "audio/wav")},
        data={"language": "hi"},
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_transcribe_non_object_body_returns_422(client):
    resp = client.post("/api/v1/voice/transcribe", json=["not", "an", "object"])
    assert resp.status_code == 422


def test_empty_chat_message_still_422(client):
    resp = client.post("/api/v1/chat", json={"message": "", "language": "en"})
    assert resp.status_code == 422


# ─── helpers ──────────────────────────────────────────────────────────

def AsyncMock_ok():
    from unittest.mock import AsyncMock
    return AsyncMock(return_value={
        "transcribed_text": "aaj ka bhav",
        "language": "hi",
        "confidence": 0.9,
        "provider": "groq",
        "error": None,
    })


def _async_return(payload):
    from unittest.mock import AsyncMock
    return AsyncMock(return_value=payload)


# P3: intent detection must work when the question is asked in the user's
# own language, not only in English or romanized transliteration.

NATIVE_INTENT_CASES = [
    ("hi", "आज मंडी में प्याज का भाव क्या है?", "price"),
    ("hi", "कौन सी सरकारी योजना मिलेगी?", "scheme"),
    ("hi", "आज बारिश होगी क्या?", "weather"),
    ("hi", "कब बेचूं, अभी या रुकूं?", "recommendation"),
    ("pa", "ਅੱਜ ਮੰਡੀ ਵਿੱਚ ਪਿਆਜ਼ ਦਾ ਭਾਵ ਕੀ ਹੈ?", "price"),
    ("pa", "ਸਰਕਾਰੀ ਯੋਜਨਾ ਕਿਹੜੀ ਮਿਲੇਗੀ?", "scheme"),
    ("pa", "ਅੱਜ ਵਰਖਾ ਹੋਵੇਗੀ?", "weather"),
    ("gu", "આજના મંડીમાં ડુંગળીના ભાવ શું છે?", "price"),
    ("gu", "સરકારી યોજના મળશે?", "scheme"),
    ("gu", "આજે વરસાદ પડશે?", "weather"),
    ("mr", "आज मंडीत कांद्याचा भाव काय आहे?", "price"),
    ("mr", "सरकारी योजना कोणती मिळेल?", "scheme"),
    ("mr", "आज पाऊस येईल का?", "weather"),
    ("bn", "আজকের মণ্ডিতে পেঁয়াজের দাম কত?", "price"),
    ("bn", "সরকারি সহায়তা পাব?", "scheme"),
    ("bn", "আজ বৃষ্টি হবে?", "weather"),
]


def test_native_script_intent_detection():
    from app.services.gemini_service import gemini_service
    for language, message, expected in NATIVE_INTENT_CASES:
        got = gemini_service.detect_intent(message)
        assert got == expected, (
            f"{language}: {message!r} -> {got}, expected {expected}"
        )


def test_native_intent_reaches_matching_context():
    from app.services.gemini_service import gemini_service
    weather = gemini_service.detect_intent("आज बारिश होगी क्या?")
    scheme = gemini_service.detect_intent("कौन सी सरकारी योजना मिलेगी?")
    assert weather == "weather"
    assert scheme == "scheme"


def test_english_queries_still_detect_same_intents():
    from app.services.gemini_service import gemini_service
    assert gemini_service.detect_intent("What is the price of onion?") == "price"
    assert gemini_service.detect_intent("Which government scheme can I get?") == "scheme"
    assert gemini_service.detect_intent("Will it rain today?") == "weather"


# ── Explicit Gemini failure handling (voice UX) ─────────────────────────────

class _ProviderError(Exception):
    """Stand-in for a google-genai HTTP error that carries a status code."""

    def __init__(self, message: str, code: int = None):
        super().__init__(message)
        if code is not None:
            self.code = code


def _ctx(language: str = "en"):
    return {
        "intent": "price", "language": language, "crop": "onion",
        "quantity": 100, "message": "question", "data_points": [],
    }


async def _generate(language: str, client):
    from app.services.gemini_service import gemini_service
    with patch.object(gemini_service, "build_context", return_value=_ctx(language)), \
         patch.object(gemini_service, "_get_client", return_value=client):
        return await gemini_service.generate_response(
            message="What is the price of onion?",
            language=language, crop="onion", quantity=100,
            farmer_lat=None, farmer_lon=None, db=None,
        )


@pytest.mark.asyncio
async def test_gemini_success_has_no_error_code():
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(
        text="Onion is INR 2405 per quintal."
    )
    result = await _generate("en", client)
    assert result["source"] == "gemini"
    assert result["error_code"] is None
    assert result["error_message"] is None
    assert "Onion is INR 2405" in result["answer"]


@pytest.mark.asyncio
async def test_gemini_429_returns_quota_error_code():
    from app.services.gemini_service import ai_unavailable_message
    client = MagicMock()
    client.models.generate_content.side_effect = _ProviderError(
        "You exceeded your current quota. {'error': {'code': 429}}", code=429
    )
    result = await _generate("en", client)
    assert result["source"] == "fallback"
    assert result["error_code"] == "AI_QUOTA_EXHAUSTED"
    assert result["error_message"] == ai_unavailable_message("en")
    # Never blank, never leaking provider internals.
    assert result["answer"].strip()
    assert "429" not in result["error_message"]
    assert "quota" not in result["error_message"].lower()
    assert "AIza" not in result["error_message"]
    assert "google" not in result["error_message"].lower()


@pytest.mark.asyncio
async def test_gemini_timeout_returns_timeout_error_code():
    client = MagicMock()
    client.models.generate_content.side_effect = TimeoutError("Request timed out.")
    result = await _generate("hi", client)
    assert result["error_code"] == "AI_TIMEOUT"
    assert result["source"] == "fallback"
    assert result["answer"].strip()


@pytest.mark.asyncio
async def test_gemini_other_failure_returns_ai_unavailable():
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("boom")
    result = await _generate("en", client)
    assert result["error_code"] == "AI_UNAVAILABLE"
    assert result["answer"].strip()


@pytest.mark.asyncio
async def test_error_message_is_localized_for_every_language():
    from app.services.gemini_service import ai_unavailable_message
    seen = set()
    for language in ALL_LANGUAGES:
        msg = ai_unavailable_message(language)
        assert msg
        seen.add(msg)
        client = MagicMock()
        client.models.generate_content.side_effect = _ProviderError("{'code': 429}", 429)
        result = await _generate(language, client)
        assert result["error_code"] == "AI_QUOTA_EXHAUSTED"
        assert result["error_message"] == msg
    # Every language gets its own string (no English reused silently).
    assert len(seen) == len(ALL_LANGUAGES)


def test_classify_ai_error_categories():
    from app.services.gemini_service import classify_ai_error
    assert classify_ai_error(_ProviderError("x", 429)) == "AI_QUOTA_EXHAUSTED"
    assert classify_ai_error(
        _ProviderError("RESOURCE_EXHAUSTED: quota")
    ) == "AI_QUOTA_EXHAUSTED"
    assert classify_ai_error(TimeoutError("timed out")) == "AI_TIMEOUT"
    assert classify_ai_error(RuntimeError("boom")) == "AI_UNAVAILABLE"


def _voice_call(client, language, gemini_result=None, gemini_exc=None, tts=None):
    """POST /voice/pipeline with a stubbed STT/Gemini/TTS stack."""
    import io
    from unittest.mock import AsyncMock

    audio = io.BytesIO(b"fake-audio-bytes")
    audio.name = "query.wav"

    stt_payload = {
        "transcribed_text": "What is the price of onion?",
        "language": language,
        "confidence": 0.95,
        "provider": "groq",
        "error": None,
    }
    tts_payload = tts or {
        "audio_base64": "aGVsbG8=",
        "audio_format": "wav",
        "provider": "gemini",
        "error": None,
    }

    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value=stt_payload)
        with patch("app.api.routes.voice.tts_service") as mock_tts:
            mock_tts.synthesize = AsyncMock(return_value=tts_payload)
            with patch("app.api.routes.voice.gemini_service") as mock_gem:
                if gemini_exc is not None:
                    mock_gem.generate_response = AsyncMock(side_effect=gemini_exc)
                else:
                    mock_gem.generate_response = AsyncMock(return_value=gemini_result)
                resp = client.post(
                    "/api/v1/voice/pipeline",
                    files={"audio": ("query.wav", audio, "audio/wav")},
                    data={"language": language, "crop": "onion", "quantity": "100"},
                )
    return resp, mock_stt, mock_tts


def _ok_gemini(language):
    return {
        "answer": "Prices are ready.", "language": language, "intent": "price",
        "context_used": ["current_price"], "data_status": "DEMO",
        "source": "gemini", "error_code": None, "error_message": None,
    }


def _quota_gemini(language, message):
    return {
        "answer": "- Indore Mandi: INR 2405/quintal", "language": language,
        "intent": "price", "context_used": ["current_price"],
        "data_status": "DEMO", "source": "fallback",
        "error_code": "AI_QUOTA_EXHAUSTED", "error_message": message,
    }


def test_voice_endpoint_when_gemini_succeeds(client):
    resp, _, _ = _voice_call(client, "en", gemini_result=_ok_gemini("en"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["error_code"] is None
    assert data["error_message"] is None
    assert data["gemini_source"] == "gemini"
    assert data["answer_text"].strip()
    assert data["language"] == "en"


def test_voice_endpoint_when_gemini_returns_429(client):
    from app.services.gemini_service import ai_unavailable_message
    resp, _, _ = _voice_call(
        client, "en", gemini_result=_quota_gemini("en", ai_unavailable_message("en"))
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error_code"] == "AI_QUOTA_EXHAUSTED"
    assert data["error_message"] == "AI service is temporarily unavailable. Please try again."
    # The screen must never be blank and nothing internal may leak.
    assert data["answer_text"].strip()
    assert "429" not in data["error_message"]
    assert "AIza" not in str(data)


def test_voice_endpoint_when_gemini_raises_429(client):
    resp, _, _ = _voice_call(
        client, "en", gemini_exc=_ProviderError("{'code': 429}", 429)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error_code"] == "AI_QUOTA_EXHAUSTED"
    assert data["answer_text"].strip()
    assert "Traceback" not in str(data)


def test_voice_endpoint_when_gemini_times_out(client):
    resp, _, _ = _voice_call(client, "en", gemini_exc=TimeoutError("timed out"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error_code"] == "AI_TIMEOUT"
    assert data["answer_text"].strip()


@pytest.mark.parametrize("language", ["en", "hi", "pa"])
def test_selected_language_propagates_through_voice(client, language):
    from app.services.gemini_service import ai_unavailable_message
    resp, mock_stt, mock_tts = _voice_call(
        client, language,
        gemini_result=_quota_gemini(language, ai_unavailable_message(language)),
    )
    data = resp.json()
    # Explicit application language, not the language inferred from the audio.
    assert data["language"] == language
    assert data["error_message"] == ai_unavailable_message(language)
    assert mock_stt.transcribe.call_args.kwargs["language"] == language
    assert mock_tts.synthesize.call_args.kwargs["language"] == language


@pytest.mark.parametrize("language", ["en", "hi", "pa"])
def test_tts_receives_selected_language(client, language):
    resp, _, mock_tts = _voice_call(client, language, gemini_result=_ok_gemini(language))
    assert resp.status_code == 200
    assert mock_tts.synthesize.call_args.kwargs["language"] == language
    assert resp.json()["answer_audio_base64"] is not None


def test_voice_pipeline_answer_is_never_blank_on_ai_failure(client):
    from app.services.gemini_service import ai_unavailable_message
    resp, _, _ = _voice_call(
        client, "hi", gemini_result=_quota_gemini("hi", ai_unavailable_message("hi"))
    )
    data = resp.json()
    assert data["success"] is False
    assert data["error_code"] == "AI_QUOTA_EXHAUSTED"
    assert data["answer_text"].strip()
    assert data["transcribed_text"].strip()
