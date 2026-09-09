from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_user():
    payload = {
        "email": "admin@voltguard.com",
        "password": "superpassword123",
        "role": "admin"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    
    # Si el usuario ya existe por pruebas anteriores, aceptamos el 400
    assert response.status_code in [201, 400]
    
    if response.status_code == 201:
        data = response.json()
        assert data["email"] == "admin@voltguard.com"
        assert data["role"] == "admin"


def test_login_user():
    # Usamos form-data porque OAuth2 lo requiere
    payload = {
        "username": "admin@voltguard.com",
        "password": "superpassword123"
    }
    response = client.post("/api/v1/auth/login", data=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"