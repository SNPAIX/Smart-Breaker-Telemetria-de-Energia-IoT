from fastapi import FastAPI
from app.routers import operative, auth  # Agregamos auth aquí

app = FastAPI(
    title="VoltGuard IoT API",
    description="Smart Breaker & Energy Management API",
    version="0.1.0",
)

# Registrar Routers
app.include_router(auth.router)        # Nuevo router de Autenticación
app.include_router(operative.router)   # Router Operativo que ya tenías


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "VoltGuard IoT API"}