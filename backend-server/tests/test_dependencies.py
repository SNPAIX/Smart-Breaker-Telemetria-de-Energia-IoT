import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.dependencies import (
    get_current_admin,
    get_current_site_member,
    get_current_user,
)
from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
)
from app.db import SessionLocal
from app.models.entities import Site, SiteMember, User

TEST_EMAIL = "dependencies_test@voltguard.com"
TEST_EMAIL_OUTSIDER = "dependencies_test_outsider@voltguard.com"
TEST_SITE_NAME = "Sitio de pruebas (dependencies_test)"


def _cleanup() -> None:
    # Deletes en bloque (no vía ORM) no disparan cascada, así que se borran
    # las membresías explícitamente antes que Site/User.
    db = SessionLocal()
    site = db.query(Site).filter(Site.name == TEST_SITE_NAME).first()
    if site:
        db.query(SiteMember).filter(SiteMember.site_id == site.id).delete()
        db.commit()
        db.delete(site)
        db.commit()
    db.query(User).filter(User.email.in_([TEST_EMAIL, TEST_EMAIL_OUTSIDER])).delete(
        synchronize_session=False
    )
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


def test_site_member_is_accepted_and_outsider_is_rejected() -> None:
    _cleanup()
    db = SessionLocal()
    try:
        member = User(
            email=TEST_EMAIL, hashed_password=get_password_hash("password123"), role="user"
        )
        outsider = User(
            email=TEST_EMAIL_OUTSIDER,
            hashed_password=get_password_hash("password123"),
            role="user",
        )
        db.add_all([member, outsider])
        db.commit()
        db.refresh(member)
        db.refresh(outsider)

        site = Site(name=TEST_SITE_NAME, kind="taller")
        db.add(site)
        db.commit()
        db.refresh(site)

        db.add(SiteMember(site_id=site.id, user_id=member.id, role="owner"))
        db.commit()

        membership = get_current_site_member(site_id=site.id, current_user=member, db=db)
        assert membership.role == "owner"
        assert membership.site_id == site.id

        with pytest.raises(HTTPException) as exc_info:
            get_current_site_member(site_id=site.id, current_user=outsider, db=db)
        assert exc_info.value.status_code == 403
    finally:
        db.close()
        _cleanup()
