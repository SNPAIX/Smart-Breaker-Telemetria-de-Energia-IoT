from fastapi import FastAPI

app = FastAPI(
    title="VoltGuard IoT API",
    description="Smart Breaker & Energy Management API",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "VoltGuard IoT API"}