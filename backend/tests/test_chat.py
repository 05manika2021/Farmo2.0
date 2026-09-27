import pytest
from app.services.gemini_service import gemini_service


def test_gemini_not_configured():
    assert gemini_service.is_configured() is False


def test_intent_detection_price():
    assert gemini_service.detect_intent("What is the price of onion?") == "price"
    assert gemini_service.detect_intent("Aaj ka bhav kya hai?") == "price"
    assert gemini_service.detect_intent("Onion ka rate kitna hai?") == "price"


def test_intent_detection_market():
    assert gemini_service.detect_intent("Kahan bechna zyada faydemand hai?") == "market"
    assert gemini_service.detect_intent("Which market should I sell?") == "market"
    assert gemini_service.detect_intent("Pass ki mandi kaunsi hai?") == "market"


def test_intent_detection_recommendation():
    assert gemini_service.detect_intent("Abhi bechu ya ruk jaun?") == "recommendation"
    assert gemini_service.detect_intent("Should I sell now or wait?") == "recommendation"
    assert gemini_service.detect_intent("Kab bechna chahiye?") == "recommendation"


def test_intent_detection_profit():
    assert gemini_service.detect_intent("Kitna profit hoga?") == "profit"
    assert gemini_service.detect_intent("How much will I earn?") == "profit"
    assert gemini_service.detect_intent("Expected income kya hai?") == "profit"


def test_intent_detection_transport():
    assert gemini_service.detect_intent("Transport kitna lagega?") == "transport"
    assert gemini_service.detect_intent("Truck bhada kitna hai?") == "transport"
    assert gemini_service.detect_intent("Transport kharcha batao") == "transport"


def test_intent_detection_weather():
    assert gemini_service.detect_intent("Mausam kaisa hai?") == "weather"
    assert gemini_service.detect_intent("Is it going to rain?") == "weather"


def test_intent_detection_general():
    assert gemini_service.detect_intent("Hello") == "general"
    assert gemini_service.detect_intent("Namaste") == "general"


def test_chat_price_query_fallback(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the price of onion?",
            "language": "en",
            "crop": "onion",
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "en"
    assert data["intent"] == "price"
    assert len(data["answer"]) > 0
    assert "DEMO" in data["data_status"]
    assert data["source"] == "fallback"


def test_chat_market_query_fallback(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Kahan bechna zyada faydemand hai?",
            "language": "hi",
            "crop": "onion",
            "quantity": 5,
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "hi"
    assert data["intent"] == "market"
    assert len(data["answer"]) > 0
    assert len(data["context_used"]) > 0


def test_chat_recommendation_query_fallback(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Abhi bechu ya ruk jaun?",
            "language": "hi",
            "crop": "onion",
            "quantity": 5,
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "recommendation"
    # Accept the native-script Hindi label as well as the older romanised form.
    answer_lower = data["answer"].lower()
    assert any(
        token in answer_lower
        for token in ("recommendation", "salah", "सलाह", "सल्ला", "সলাহ")
    )


def test_chat_profit_query_fallback(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "How much will I earn from onion?",
            "language": "en",
            "crop": "onion",
            "quantity": 5,
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "profit"
    assert "INR" in data["answer"] or "profit" in data["answer"].lower()


def test_chat_hindi_response(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Onion ka bhav kya hai?",
            "language": "hi",
            "crop": "onion",
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "hi"


def test_chat_english_response(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the price of onion?",
            "language": "en",
            "crop": "onion",
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "en"


def test_chat_general_query(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Hello, what is Farmo?",
            "language": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "general"
    assert len(data["answer"]) > 0


def test_chat_different_crops(client):
    for crop in ["onion", "tomato", "potato"]:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": f"What is the price of {crop}?",
                "language": "en",
                "crop": crop,
                "latitude": 22.7196,
                "longitude": 75.8577,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "price"


def test_chat_context_used_populated(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Where should I sell my onion?",
            "language": "en",
            "crop": "onion",
            "quantity": 5,
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    data = response.json()
    assert len(data["context_used"]) > 0
    assert "market_comparison" in data["context_used"]


def test_chat_no_crop_still_works(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "What is Farmo?",
            "language": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "general"


def test_chat_empty_message_rejected(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "",
            "language": "en",
        },
    )
    assert response.status_code == 422
