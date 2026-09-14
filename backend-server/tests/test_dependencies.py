import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.dependencies import get_current_admin, get_current_user
from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
)
from app.db import SessionLocal
from app.models.entities import User

TEST_EMAIL = "dependencies_test@voltguard.com"


def _cleanup() -> None:
    db = SessionLocal()
    db.query(User).filter(User.email == TEST_EMAIL).delete()
    db.commit()
    db.close()


def test_malformed_token_returns_401() -> None:
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token="esto-no-es-un-jwt-valido", db=db)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "No se pudieron validar las credenciales"
    finally:
        db.close()


def test_token_for_nonexistent_user_returns_401() -> None:
    # Token válido (bien firmado), pero para un id de usuario que no existe
    # en la base — cubre la rama donde el JWT pasa la verificación de firma
    # pero el usuario referenciado ya no está (p. ej. fue eliminado).
    token = create_access_token(subject="999999", role="admin")
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db)
        assert exc_info.value.status_code == 401
    finally:
        db.close()


def test_token_without_sub_claim_returns_401() -> None:
    # JWT válido (bien firmado) pero sin el campo "sub" — cubre la
    # validación defensiva para un token malformado que aun así pasa la
    # verificación de firma. create_access_token siempre incluye "sub",
    # así que este caso solo ocurriría con un token construido a mano
    # o por un bug futuro.
    token = jwt.encode({"role": "admin"}, SECRET_KEY, algorithm=ALGORITHM)
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db)
        assert exc_info.value.status_code == 401
    finally:
        db.close()


def test_normal_user_rejected_by_get_current_admin() -> None:
    _cleanup()
    db = SessionLocal()
    try:
        user = User(
            email=TEST_EMAIL,
            hashed_password=get_password_hash("password123"),
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(current_user=user)
        assert exc_info.value.status_code == 403
    finally:
        db.close()
        _cleanup()
