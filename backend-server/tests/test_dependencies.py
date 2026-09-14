from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def test_malformed_token_returns_401():
    headers = {"Authorization": "Bearer esto-no-es-un-jwt-valido"}
    response = client.get("/api/v1/admin/dashboard/metrics", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "No se pudieron validar las credenciales"


def test_token_for_nonexistent_user_returns_401():
    # Token válido (bien firmado), pero para un id de usuario que no existe
    # en la base — cubre la rama donde el JWT pasa la verificación de firma
    # pero el usuario referenciado ya no está (p. ej. fue eliminado).
    token = create_access_token(subject="999999", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/admin/dashboard/metrics", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "No se pudieron validar las credenciales"


def test_token_without_sub_claim_returns_401():
    # JWT válido (bien firmado) pero sin el campo "sub" — cubre la
    # validación defensiva para un token malformado que aun así pasa la
    # verificación de firma. create_access_token siempre incluye "sub",
    # así que este caso solo ocurriría con un token construido a mano
    # o por un bug futuro.
    from jose import jwt

    from app.core.security import ALGORITHM, SECRET_KEY

    token = jwt.encode({"role": "admin"}, SECRET_KEY, algorithm=ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/admin/dashboard/metrics", headers=headers)
    assert response.status_code == 401


def test_missing_token_returns_401():
    response = client.get("/api/v1/admin/dashboard/metrics")
    assert response.status_code == 401
