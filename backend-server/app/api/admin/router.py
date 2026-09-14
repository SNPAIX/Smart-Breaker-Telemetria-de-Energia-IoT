from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_admin

# Superficie /api/v1/admin/*. Cascarón vacío a propósito: el registro de
# dispositivos y el dashboard de métricas del repo base dependían de
# columnas que el esquema v2 elimina de Device (max_current_threshold,
# relay_status). Se reconstruyen en la etapa 7 (CRUD de sitios/dispositivos/
# perfiles) y la etapa 8 (métricas) sobre el modelo nuevo.
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin & Dashboard"],
    dependencies=[Depends(get_current_admin)],
)
