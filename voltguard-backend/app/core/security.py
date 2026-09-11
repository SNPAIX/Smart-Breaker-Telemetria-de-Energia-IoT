import os
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.logging_config import get_logger

logger = get_logger("voltguard.security")

# La clave se lee de la variable de entorno SECRET_KEY. El valor de aquí
# abajo es SOLO un fallback para desarrollo local sin .env — nunca se debe
# usar en producción. En CI y en despliegue real, SECRET_KEY viene de un
# secret (ver .env.example y Settings > Secrets en GitHub Actions).
_DEV_FALLBACK_KEY = "dev-only-insecure-key-set-SECRET_KEY-env-var"
SECRET_KEY = os.getenv("SECRET_KEY", _DEV_FALLBACK_KEY)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días


def _warn_if_insecure_key(key: str) -> None:
    """Aislado en su propia función (en vez de un `if` suelto a nivel de
    módulo) para poder probarlo directamente sin recargar el módulo
    completo — recargar app.core.security en un test sería frágil, ya que
    otros módulos (dependencies.py) importan SECRET_KEY por valor al
    arrancar el proceso, no por referencia."""
    if key == _DEV_FALLBACK_KEY:
        logger.warning(
            "insecure_secret_key_in_use",
            extra={"hint": "Define la variable de entorno SECRET_KEY antes de desplegar."},
        )


_warn_if_insecure_key(SECRET_KEY)

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def create_access_token(subject: str | Any, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "role": role}
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt