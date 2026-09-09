from fastapi import FastAPI
from app.routers import operative, auth, admin  # <--- Asegúrate de incluir 'admin' aquí

app = FastAPI(
    title="VoltGuard IoT API",
    description="Smart Breaker & Energy Management API",
    version="0.1.0",
)

# Registrar Routers
app.include_router(auth.router)
app.include_router(operative.router)
app.include_router(admin.router)  # <--- Aquí es donde se usa


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "VoltGuard IoT API"}