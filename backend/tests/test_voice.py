import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
import base64


# === STT TESTS ===

@pytest.mark.asyncio
async def test_stt_success():
    from app.services.stt_service import STTService
    mock_resp = MagicMock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = lambda: {"text": "Mere paas 5 quintal pyaaz hai", "language": "hindi"}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    svc = STTService()
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = "openai"
        s.OPENAI_API_KEY = "test-key"
        with patch("app.services.stt_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.transcribe(b"fake-audio", "test.wav", "audio/wav", "hi")
    assert result["transcribed_text"] == "Mere paas 5 quintal pyaaz hai"
    assert result["provider"] == "openai"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_stt_api_failure():
    from app.services.stt_service import STTService
    svc = STTService()
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = "openai"
        s.OPENAI_API_KEY = "test-key"
        with patch("app.services.stt_service.httpx.AsyncClient") as cls:
            mc = AsyncMock()
            mc.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mc.__aenter__ = AsyncMock(return_value=mc)
            mc.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mc
            result = await svc.transcribe(b"fake", "t.wav", "audio/wav", "hi")
    assert result["transcribed_text"] == ""
    assert result["error"] is not None
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
async def test_stt_missing_credentials():
    from app.services.stt_service import STTService
    svc = STTService()
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = "openai"
        s.OPENAI_API_KEY = None
        result = await svc.transcribe(b"fake", "t.wav", "audio/wav", "hi")
    assert result["error"] is not None
    assert "key not configured" in result["error"].lower()


@pytest.mark.asyncio
async def test_stt_no_provider():
    from app.services.stt_service import STTService
    svc = STTService()
    with patch("app.services.stt_service.settings") as s:
        s.STT_PROVIDER = None
        result = await svc.transcribe(b"fake", "t.wav", "audio/wav", "hi")
    assert result["error"] is not None
    assert "not configured" in result["error"].lower()


@pytest.mark.asyncio
async def test_stt_unsupported_audio_type():
    from app.services.stt_service import STTService
    svc = STTService()
    result = await svc.transcribe(b"fake", "t.txt", "text/plain", "hi")
    assert result["error"] is not None
    assert "unsupported" in result["error"].lower()


@pytest.mark.asyncio
async def test_stt_file_too_large():
    from app.services.stt_service import STTService
    svc = STTService()
    result = await svc.transcribe(b"x" * (26 * 1024 * 1024), "big.wav", "audio/wav", "hi")
    assert result["error"] is not None
    assert "too large" in result["error"].lower()


# === TTS TESTS ===

@pytest.mark.asyncio
async def test_tts_success():
    from app.services.tts_service import TTSService
    fake_audio = b"fake-mp3-bytes"
    mock_resp = MagicMock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.content = fake_audio
    mc = AsyncMock()
    mc.post = AsyncMock(return_value=mock_resp)
    mc.__aenter__ = AsyncMock(return_value=mc)
    mc.__aexit__ = AsyncMock(return_value=False)
    svc = TTSService()
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = "openai"
        s.OPENAI_API_KEY = "test-key"
        s.OPENAI_TTS_MODEL = "tts-1"
        with patch("app.services.tts_service.httpx.AsyncClient", return_value=mc):
            result = await svc.synthesize("Hello farmer", "en")
    assert result["audio_base64"] is not None
    decoded = base64.b64decode(result["audio_base64"])
    assert decoded == fake_audio
    assert result["provider"] == "openai"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_tts_api_failure():
    from app.services.tts_service import TTSService
    svc = TTSService()
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = "openai"
        s.OPENAI_API_KEY = "test-key"
        s.OPENAI_TTS_MODEL = "tts-1"
        with patch("app.services.tts_service.httpx.AsyncClient") as cls:
            mc = AsyncMock()
            mc.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mc.__aenter__ = AsyncMock(return_value=mc)
            mc.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mc
            result = await svc.synthesize("Hello", "en")
    assert result["audio_base64"] is None
    assert result["error"] is not None
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
async def test_tts_missing_credentials():
    from app.services.tts_service import TTSService
    svc = TTSService()
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = "openai"
        s.OPENAI_API_KEY = None
        result = await svc.synthesize("Hello", "en")
    assert result["audio_base64"] is None
    assert result["error"] is not None
    assert "key not configured" in result["error"].lower()


@pytest.mark.asyncio
async def test_tts_no_provider():
    from app.services.tts_service import TTSService
    svc = TTSService()
    with patch("app.services.tts_service.settings") as s:
        s.TTS_PROVIDER = None
        result = await svc.synthesize("Hello", "en")
    assert result["audio_base64"] is None
    assert result["error"] is not None
    assert "not configured" in result["error"].lower()


# === ROUTE TESTS ===

def test_transcribe_route_no_audio(client):
    resp = client.post("/api/v1/voice/transcribe", json={"language": "hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["transcribed_text"] == ""
    assert data["error"] is not None


def test_transcribe_route_with_base64(client):
    fake_audio = base64.b64encode(b"fake-audio").decode()
    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "test query",
            "language": "hi",
            "confidence": 0.9,
            "provider": "openai",
            "error": None,
        })
        resp = client.post("/api/v1/voice/transcribe", json={
            "audio_data": fake_audio,
            "language": "hi",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["transcribed_text"] == "test query"
    assert data["provider"] == "openai"


def test_respond_route(client):
    with patch("app.api.routes.voice.tts_service") as mock_tts:
        mock_tts.synthesize = AsyncMock(return_value={
            "audio_base64": "dGVzdA==",
            "audio_format": "mp3",
            "provider": "openai",
            "error": None,
        })
        resp = client.post("/api/v1/voice/respond", json={
            "text": "Aapka net profit 5000 hai",
            "language": "hi",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["audio_base64"] == "dGVzdA=="
    assert data["text"] == "Aapka net profit 5000 hai"
    assert data["provider"] == "openai"


def test_pipeline_unsupported_audio_type(client):
    import io
    audio_file = io.BytesIO(b"not-really-audio")
    audio_file.name = "test.txt"
    resp = client.post(
        "/api/v1/voice/pipeline",
        files={"audio": ("test.txt", audio_file, "text/plain")},
        data={"language": "hi"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stt_error"] is not None
    assert "unsupported" in data["stt_error"].lower()


def test_pipeline_stt_failure(client):
    import io
    audio_file = io.BytesIO(b"fake-audio")
    audio_file.name = "test.wav"
    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "",
            "language": "hi",
            "confidence": None,
            "provider": "unavailable",
            "error": "STT failed",
        })
        resp = client.post(
            "/api/v1/voice/pipeline",
            files={"audio": ("test.wav", audio_file, "audio/wav")},
            data={"language": "hi"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stt_error"] == "STT failed"
    assert data["answer_text"] == ""


def test_pipeline_hindi_query(client):
    import io
    audio_file = io.BytesIO(b"fake-audio")
    audio_file.name = "query.wav"
    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "Onion ka bhav kya hai",
            "language": "hi",
            "confidence": 0.95,
            "provider": "openai",
            "error": None,
        })
        with patch("app.api.routes.voice.tts_service") as mock_tts:
            mock_tts.synthesize = AsyncMock(return_value={
                "audio_base64": "aGRhdGE=",
                "audio_format": "mp3",
                "provider": "openai",
                "error": None,
            })
            resp = client.post(
                "/api/v1/voice/pipeline",
                files={"audio": ("query.wav", audio_file, "audio/wav")},
                data={"language": "hi", "crop": "onion"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["transcribed_text"] == "Onion ka bhav kya hai"
    assert data["language"] == "hi"
    assert data["intent"] == "price"
    assert len(data["answer_text"]) > 0


def test_pipeline_english_query(client):
    import io
    audio_file = io.BytesIO(b"fake-audio")
    audio_file.name = "query.wav"
    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "Where should I sell my onion?",
            "language": "en",
            "confidence": 0.95,
            "provider": "openai",
            "error": None,
        })
        with patch("app.api.routes.voice.tts_service") as mock_tts:
            mock_tts.synthesize = AsyncMock(return_value={
                "audio_base64": "ZW5nbGlzaA==",
                "audio_format": "mp3",
                "provider": "openai",
                "error": None,
            })
            resp = client.post(
                "/api/v1/voice/pipeline",
                files={"audio": ("query.wav", audio_file, "audio/wav")},
                data={"language": "en", "crop": "onion"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["transcribed_text"] == "Where should I sell my onion?"
    assert data["language"] == "en"
    assert len(data["answer_text"]) > 0


def test_pipeline_market_query(client):
    import io
    audio_file = io.BytesIO(b"fake-audio")
    audio_file.name = "q.wav"
    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "Kahan bechna zyada faydemand hai?",
            "language": "hi",
            "confidence": 0.9,
            "provider": "openai",
            "error": None,
        })
        with patch("app.api.routes.voice.tts_service") as mock_tts:
            mock_tts.synthesize = AsyncMock(return_value={
                "audio_base64": None,
                "audio_format": "mp3",
                "provider": "unavailable",
                "error": "TTS not configured",
            })
            resp = client.post(
                "/api/v1/voice/pipeline",
                files={"audio": ("q.wav", audio_file, "audio/wav")},
                data={"language": "hi", "crop": "onion", "quantity": "5"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] in ("market", "recommendation")
    assert len(data["answer_text"]) > 0
    assert data["tts_error"] == "TTS not configured"


def test_pipeline_profit_query(client):
    import io
    audio_file = io.BytesIO(b"fake-audio")
    audio_file.name = "q.wav"
    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "Kitna profit hoga?",
            "language": "hi",
            "confidence": 0.9,
            "provider": "openai",
            "error": None,
        })
        with patch("app.api.routes.voice.tts_service") as mock_tts:
            mock_tts.synthesize = AsyncMock(return_value={
                "audio_base64": None,
                "audio_format": "mp3",
                "provider": "unavailable",
                "error": None,
            })
            resp = client.post(
                "/api/v1/voice/pipeline",
                files={"audio": ("q.wav", audio_file, "audio/wav")},
                data={"language": "hi", "crop": "onion", "quantity": "5"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "profit"
    assert len(data["answer_text"]) > 0


def test_pipeline_gemini_failure_fallback(client):
    import io
    audio_file = io.BytesIO(b"fake-audio")
    audio_file.name = "q.wav"
    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "Hello",
            "language": "en",
            "confidence": 0.9,
            "provider": "openai",
            "error": None,
        })
        with patch("app.api.routes.voice.gemini_service") as mock_gem:
            mock_gem.generate_response = AsyncMock(side_effect=Exception("Gemini crashed"))
            with patch("app.api.routes.voice.tts_service") as mock_tts:
                mock_tts.synthesize = AsyncMock(return_value={
                    "audio_base64": None,
                    "audio_format": "mp3",
                    "provider": "unavailable",
                    "error": None,
                })
                resp = client.post(
                    "/api/v1/voice/pipeline",
                    files={"audio": ("q.wav", audio_file, "audio/wav")},
                    data={"language": "en", "crop": "onion"},
                )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer_text"] != ""


def test_pipeline_missing_provider_credentials(client):
    import io
    audio_file = io.BytesIO(b"fake-audio")
    audio_file.name = "q.wav"
    with patch("app.api.routes.voice.stt_service") as mock_stt:
        mock_stt.transcribe = AsyncMock(return_value={
            "transcribed_text": "",
            "language": "hi",
            "confidence": None,
            "provider": "unavailable",
            "error": "STT provider not configured",
        })
        resp = client.post(
            "/api/v1/voice/pipeline",
            files={"audio": ("q.wav", audio_file, "audio/wav")},
            data={"language": "hi"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stt_error"] is not None
    assert data["answer_text"] == ""
