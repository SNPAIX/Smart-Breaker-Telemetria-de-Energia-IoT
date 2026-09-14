import secrets

from app.core.security import get_password_hash
from app.models.entities import Device, DeviceCredential


def issue_device_credential(device: Device) -> str:
    """Genera un secreto nuevo para el dispositivo y persiste solo su hash
    (mismo mecanismo bcrypt que las contraseñas de usuario — un secreto de
    dispositivo es, en esencia, una contraseña).

    El secreto en texto plano se devuelve una única vez: quien lo recibe
    (la etapa 4/7 al dar de alta el dispositivo) debe guardarlo, porque no
    se puede recuperar a partir del hash.
    """
    plain_secret = secrets.token_urlsafe(32)
    device.credential = DeviceCredential(secret_hash=get_password_hash(plain_secret))
    return plain_secret
