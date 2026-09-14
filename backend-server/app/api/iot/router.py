from fastapi import APIRouter

# Superficie /api/v1/iot/* (dispositivos físicos). Cascarón vacío a
# propósito: el endpoint de telemetría del repo base dependía de columnas
# que el esquema v2 elimina de Device (max_current_threshold, relay_status)
# y de los modelos Reading/Alert/SafetyEvent, ya retirados. Se reconstruye
# en la etapa 4 sobre el modelo nuevo, con autenticación de dispositivo real
# (etapa 3) — ver roadmap/01-gap-analysis.md y roadmap/PROGRESS.md.
router = APIRouter(prefix="/api/v1/iot", tags=["IoT"])
