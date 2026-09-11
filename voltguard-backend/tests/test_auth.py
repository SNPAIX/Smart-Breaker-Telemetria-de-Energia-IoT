from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.entities import User

client = TestClient(app)

TEST_EMAIL = "admin_auth_test@voltguard.com"
TEST_PASSWORD = "superpassword123"


def _cleanup_test_user() -> None:
    """Las pruebas corren contra una base Postgres persistente (no hay
    rollback automático entre corridas de pytest), así que garantizamos un
    estado limpio antes de cada prueba en vez de tolerar lo que haya
    quedado de una ejecución anterior. Sin esto, correr la suite dos veces
    seguidas da resultados distintos (la segunda vez el usuario ya existe
    y el camino "registro exitoso" nunca se ejecuta)."""
    db = SessionLocal()
    db.query(User).filter(User.email == TEST_EMAIL).delete()
    db.commit()
    db.close()


def test_register_user():
    _cleanup_test_user()
    payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD, "role": "admin"}
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == TEST_EMAIL
    assert data["role"] == "admin"


def test_register_duplicate_email_returns_400():
    _cleanup_test_user()
    payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD, "role": "admin"}
    client.post("/api/v1/auth/register", json=payload)  # primera vez: se crea

    response = client.post("/api/v1/auth/register", json=payload)  # segunda: duplicado
    assert response.status_code == 400


def test_login_user():
    _cleanup_test_user()
    client.post(
        "/api/v1/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "role": "admin"},
    )

    # Usamos form-data porque OAuth2 lo requiere
    response = client.post(
        "/api/v1/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401():
    _cleanup_test_user()
    client.post(
        "/api/v1/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "role": "admin"},
    )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": TEST_EMAIL, "password": "contraseña-incorrecta"},
    )
    assert response.status_code == 401


def test_login_unknown_email_returns_401():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "no-existe@voltguard.com", "password": "lo-que-sea"},
    )
    assert response.status_code == 401
