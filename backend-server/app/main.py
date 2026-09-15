import time

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import admin, auth, iot
from app.api import app as app_api
from app.api.app import ws as ws_api
from app.api.iot import ws as iot_ws_api
from app.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.db import get_db

configure_logging()
logger = get_logger("voltguard.http")

app = FastAPI(
    title="VoltGuard IoT API",
    description="Smart Breaker & Energy Management API",
    version="0.1.0",
)

# `front/` (Vite, otro puerto) y `mobile/` (WebView de Capacitor, otro
# origen todavía) son clientes de navegador reales, a diferencia del
# script Node usado para verificar la etapa 13 — axios en Node no aplica
# same-origin policy, así que esta brecha no se había notado hasta probar
# la app móvil en un WebView real. La autenticación va por header
# `Authorization` (JWT), no por cookies, así que permitir cualquier origen
# no expone credenciales de sesión — no hace falta `allow_credentials`.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next: object) -> Response:
    start = time.perf_counter()
    response: Response = await call_next(request)  # type: ignore[operator]
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "http_request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return response


# Registrar Routers
app.include_router(auth.router)
app.include_router(iot.router)
app.include_router(admin.router)
app.include_router(app_api.router)
app.include_router(ws_api.router)
app.include_router(iot_ws_api.router)

# Asistente de voz (etapa 14) — módulo aislado y desacoplable en
# `IA-Assistant/` (fuera de este paquete). El import de `app.api.app.voice`
# (y, transitivamente, de `ia_assistant`) solo ocurre si el flag global
# está encendido: con el flag apagado, ni siquiera hace falta tener el
# paquete instalado para que el backend arranque.
if settings.voice_assistant_enabled:
    from app.api.app import voice as voice_api

    app.include_router(voice_api.router)
    logger.info("voice_assistant_enabled", extra={"model_path": settings.voice_assistant_model_path})


@app.get("/health")
def health_check() -> dict[str, str]:
    """Vida del proceso, sin tocar la base de datos — no debe fallar solo
    porque Postgres esté caído (eso es lo que verifica /health/ready)."""
    return {"status": "ok", "service": "VoltGuard IoT API"}


@app.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible.",
        ) from exc
    return {"status": "ready"}