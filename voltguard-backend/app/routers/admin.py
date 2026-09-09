from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.entities import Device, User
from app.schemas.device import DeviceCreate, DeviceOut
from app.core.dependencies import get_current_admin

router = APIRouter(
    prefix="/api/v1/admin", 
    tags=["Admin & Dashboard"],
    dependencies=[Depends(get_current_admin)]  # Protege TODAS las rutas de este archivo
)

@router.post("/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def register_device(device_in: DeviceCreate, db: Session = Depends(get_db)):
    """Da de alta un nuevo dispositivo (ESP32) en el sistema."""
    existing_device = db.query(Device).filter(Device.id == device_in.id).first()
    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID del dispositivo ya existe."
        )
    
    new_device = Device(
        id=device_in.id,
        name=device_in.name,
        max_current_threshold=device_in.max_current_threshold
    )
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device

@router.get("/dashboard/metrics")
def get_global_metrics(db: Session = Depends(get_db)):
    """Retorna las métricas globales para el dashboard del administrador."""
    total_devices = db.query(Device).count()
    active_devices = db.query(Device).filter(Device.relay_status == True).count()
    total_users = db.query(User).filter(User.role == "user").count()
    
    return {
        "total_devices": total_devices,
        "active_devices": active_devices,
        "total_users": total_users,
        "system_status": "healthy"
    }