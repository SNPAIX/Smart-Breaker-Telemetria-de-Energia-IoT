from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.security import ALGORITHM, SECRET_KEY, verify_password
from app.db import get_db
from app.models.entities import Device, SiteMember, User
from app.services.devices import is_user_authorized_for_device

# Le indica a FastAPI y Swagger UI dónde se obtienen los tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilegios insuficientes. Se requiere rol de administrador."
        )
    return current_user


def get_current_site_member(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteMember:
    """Confirma que el usuario autenticado pertenece al sitio `site_id` y
    devuelve su membresía (con el `role` dentro de ese sitio). Pensada para
    usarse en rutas con `{site_id}` en el path (etapa 6, /api/v1/app/*):
    FastAPI resuelve `site_id` como parámetro de ruta también dentro de una
    dependencia, sin necesidad de repetirlo en la firma del endpoint."""
    membership = (
        db.query(SiteMember)
        .filter(SiteMember.site_id == site_id, SiteMember.user_id == current_user.id)
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no pertenece a este sitio.",
        )
    return membership


def get_authorized_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Device:
    """Confirma que el dispositivo `device_id` existe, está vinculado a un
    sitio, y que el usuario autenticado tiene membresía en ese sitio.

    Responde 404 tanto si el dispositivo no existe como si no está
    autorizado — a propósito, para no revelarle a un usuario sin acceso
    si un `device_id` ajeno existe o no."""
    not_found = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Dispositivo no encontrado.",
    )

    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None or device.site_id is None:
        raise not_found

    if not is_user_authorized_for_device(db, current_user.id, device_id):
        raise not_found

    return device


def authenticate_device_credential(db: Session, authorization: str | None) -> Device | None:
    """Verifica un header `Authorization: Device <public_id>:<secret>` y
    devuelve el `Device` si es válido, o `None` si no — nunca levanta
    excepción, para que tanto la dependencia HTTP (`get_current_device`,
    que sí necesita convertir esto en un 401) como el handshake WebSocket
    (`app/api/iot/ws.py`, que necesita cerrar el socket con su propio
    código en vez de una excepción HTTP) puedan reusar la misma
    verificación sin duplicarla."""
    if not authorization:
        return None

    scheme, _, param = authorization.partition(" ")
    if scheme.lower() != "device" or not param:
        return None

    public_id, _, secret = param.partition(":")
    if not public_id or not secret:
        return None

    device = db.query(Device).filter(Device.public_id == public_id).first()
    if device is None or device.credential is None:
        return None
    if device.credential.revoked_at is not None:
        return None
    if not verify_password(secret, device.credential.secret_hash):
        return None

    return device


def get_current_device(
    authorization: str = Header(..., description='Esquema: "Device <public_id>:<secret>"'),
    db: Session = Depends(get_db),
) -> Device:
    """Autenticación de dispositivo, independiente del JWT de usuario: un
    dispositivo se identifica con su `public_id` y un secreto propio (ver
    DeviceCredential / app/services/device_auth.py), nunca con un token de
    usuario — ciclo de vida y revocación distintos."""
    device = authenticate_device_credential(db, authorization)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de dispositivo inválidas.",
        )
    return device
