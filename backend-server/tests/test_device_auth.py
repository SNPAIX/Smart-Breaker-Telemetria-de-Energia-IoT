from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_device
from app.db import SessionLocal
from app.models.entities import Device
from app.services.device_auth import issue_device_credential

TEST_PUBLIC_ID = "VG-DEVICE-AUTH-TEST"


def _cleanup() -> None:
    # db.delete(device) (vía ORM, no delete en bloque) para que la cascada
    # de Device.credential borre también el DeviceCredential asociado.
    db = SessionLocal()
    device = db.query(Device).filter(Device.public_id == TEST_PUBLIC_ID).first()
    if device:
        db.delete(device)
        db.commit()
    db.close()


def _make_device(db: Session) -> tuple[Device, str]:
    device = Device(public_id=TEST_PUBLIC_ID, name="Dispositivo de prueba")
    db.add(device)
    db.commit()
    db.refresh(device)
    plain_secret = issue_device_credential(device)
    db.commit()
    db.refresh(device)
    return device, plain_secret


def test_issue_device_credential_stores_only_the_hash() -> None:
    _cleanup()
    db = SessionLocal()
    try:
        device, plain_secret = _make_device(db)
        assert device.credential is not None
        assert device.credential.secret_hash != plain_secret
    finally:
        db.close()
        _cleanup()


def test_valid_device_credentials_are_accepted() -> None:
    _cleanup()
    db = SessionLocal()
    try:
        _device, plain_secret = _make_device(db)
        authenticated = get_current_device(
            authorization=f"Device {TEST_PUBLIC_ID}:{plain_secret}", db=db
        )
        assert authenticated.public_id == TEST_PUBLIC_ID
    finally:
        db.close()
        _cleanup()


def test_wrong_secret_is_rejected() -> None:
    _cleanup()
    db = SessionLocal()
    try:
        _make_device(db)
        with pytest.raises(HTTPException) as exc_info:
            get_current_device(authorization=f"Device {TEST_PUBLIC_ID}:secreto-incorrecto", db=db)
        assert exc_info.value.status_code == 401
    finally:
        db.close()
        _cleanup()


def test_revoked_credential_is_rejected_even_with_correct_secret() -> None:
    _cleanup()
    db = SessionLocal()
    try:
        device, plain_secret = _make_device(db)
        assert device.credential is not None
        device.credential.revoked_at = datetime.now(UTC)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            get_current_device(authorization=f"Device {TEST_PUBLIC_ID}:{plain_secret}", db=db)
        assert exc_info.value.status_code == 401
    finally:
        db.close()
        _cleanup()


def test_unknown_device_is_rejected() -> None:
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc_info:
            get_current_device(authorization="Device NO-EXISTE:cualquier-secreto", db=db)
        assert exc_info.value.status_code == 401
    finally:
        db.close()


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer algo",  # esquema incorrecto (JWT de usuario, no de dispositivo)
        "Device sin-dos-puntos",  # falta el separador public_id:secret
        "Device :secreto-sin-public-id",
        "Device public-id-sin-secreto:",
    ],
)
def test_malformed_authorization_header_is_rejected(authorization: str) -> None:
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc_info:
            get_current_device(authorization=authorization, db=db)
        assert exc_info.value.status_code == 401
    finally:
        db.close()
