import time

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import admin, auth, iot
from app.api import app as app_api
from app.core.logging_config import configure_logging, get_logger
from app.db import get_db

configure_logging()
logger = get_logger("voltguard.http")

app = FastAPI(
    title="VoltGuard IoT API",
    description="Smart Breaker & Energy Management API",
    version="0.1.0",
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