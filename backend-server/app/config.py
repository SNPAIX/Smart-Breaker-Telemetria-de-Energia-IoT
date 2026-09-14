from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada, leída de variables de entorno (o de un
    `.env` local — ver `.env.example`). Reemplaza las llamadas dispersas a
    `os.getenv(...)` que existían en `core/security.py`, `db.py`,
    `core/logging_config.py` y `routers/operative.py`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://voltguard_user:supersecretpassword@localhost:5432/voltguard_db"

    # Sin default seguro a propósito: si no se define, cae en la clave de
    # desarrollo insegura marcada explícitamente como tal (ver security.py).
    secret_key: str = "dev-only-insecure-key-set-SECRET_KEY-env-var"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 días

    environment: str = "development"
    log_level: str = "INFO"

    # "rule_based" (sin IA, default) o "isolation_forest" (con IA).
    anomaly_detector: str = "rule_based"

    # Un dispositivo se considera "online" si su last_seen_at es más
    # reciente que este umbral — no es un campo booleano que haya que
    # mantener sincronizado, se calcula al consultar (ver etapa 7).
    device_online_threshold_seconds: int = 300


settings = Settings()
