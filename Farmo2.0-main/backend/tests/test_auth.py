import pytest


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "farmo-backend"


def test_send_otp_valid_phone(client):
    response = client.post(
        "/api/v1/auth/send-otp",
        json={"phone": "9876543210"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["demo_mode"] is True
    assert data["demo_otp"] == "123456"


def test_send_otp_invalid_phone(client):
    response = client.post(
        "/api/v1/auth/send-otp",
        json={"phone": "123"},
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"]["error_code"] == "INVALID_PHONE_NUMBER"


def test_send_otp_with_prefix(client):
    response = client.post(
        "/api/v1/auth/send-otp",
        json={"phone": "+919876543301"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_send_otp_with_91_prefix(client):
    response = client.post(
        "/api/v1/auth/send-otp",
        json={"phone": "919876543302"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_verify_otp_success(client):
    client.post("/api/v1/auth/send-otp", json={"phone": "9876543210"})
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "9876543210", "otp": "123456"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data
    assert data["farmer_id"] is not None


def test_verify_otp_invalid(client):
    client.post("/api/v1/auth/send-otp", json={"phone": "9876543211"})
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "9876543211", "otp": "000000"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["error_code"] == "INVALID_OTP"


def test_auth_me_with_token(client):
    client.post("/api/v1/auth/send-otp", json={"phone": "9876543212"})
    verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "9876543212", "otp": "123456"},
    )
    token = verify.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "9876543212"


def test_farmer_profile_update(client):
    client.post("/api/v1/auth/send-otp", json={"phone": "9876543213"})
    verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "9876543213", "otp": "123456"},
    )
    token = verify.json()["access_token"]
    farmer_id = verify.json()["farmer_id"]

    response = client.put(
        f"/api/v1/farmers/{farmer_id}",
        json={
            "name": "Ramesh Kumar",
            "age": 35,
            "language": "hi",
            "village": "Indore",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ramesh Kumar"
    assert data["age"] == 35
    assert data["village"] == "Indore"


def test_add_farmer_crop(client):
    client.post("/api/v1/auth/send-otp", json={"phone": "9876543214"})
    verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "9876543214", "otp": "123456"},
    )
    token = verify.json()["access_token"]
    farmer_id = verify.json()["farmer_id"]

    response = client.post(
        f"/api/v1/farmers/{farmer_id}/crops",
        json={"crop_name": "onion", "quantity": 5, "quantity_unit": "quintal"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["crop_name"] == "onion"
    assert data["quantity"] == 5


def test_resend_otp_success(client):
    response = client.post(
        "/api/v1/auth/resend-otp",
        json={"phone": "9876543303"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_verify_otp_without_sending(client):
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "9876543299", "otp": "123456"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["error_code"] == "OTP_NOT_FOUND"
