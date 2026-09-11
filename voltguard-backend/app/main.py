import time

from fastapi import FastAPI, Request, Response

from app.core.logging_config import configure_logging, get_logger
from app.routers import admin, auth, operative  # <--- Asegúrate de incluir 'admin' aquí

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
app.include_router(operative.router)
app.include_router(operative.devices_router)
app.include_router(admin.router)  # <--- Aquí es donde se usa


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "VoltGuard IoT API"}