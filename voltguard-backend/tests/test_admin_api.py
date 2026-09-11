from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.db import SessionLocal
from app.main import app
from app.models.entities import Device, User

client = TestClient(app)


def _ensure_admin_user() -> int:
    """El middleware de auth busca el usuario por id en la BD (no solo en
    el token), así que el usuario admin debe existir antes de usarlo."""
    db = SessionLocal()
    existing = db.query(User).filter(User.email == "admin_test@voltguard.com").first()
    if not existing:
        admin_user = User(
            email="admin_test@voltguard.com",
            hashed_password=get_password_hash("password123"),
            role="admin",
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        user_id = admin_user.id
    else:
        user_id = existing.id
    db.close()
    return user_id


def test_admin_dashboard_access():
    # 1. Generar token con rol de administrador (el usuario debe existir)
    admin_id = _ensure_admin_user()
    admin_token = create_access_token(subject=str(admin_id), role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 2. Intentar acceder al dashboard
    response = client.get("/api/v1/admin/dashboard/metrics", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "total_devices" in data
    assert data["system_status"] == "healthy"

def test_normal_user_rejected():
    # 1. Asegurar que existe un usuario normal en la BD de pruebas con ID conocido
    db = SessionLocal()
    existing = db.query(User).filter(User.email == "normal_test@voltguard.com").first()
    if not existing:
        normal_user = User(
            email="normal_test@voltguard.com",
            hashed_password=get_password_hash("password123"),
            role="user"
        )
        db.add(normal_user)
        db.commit()
        db.refresh(normal_user)
        user_id = normal_user.id
    else:
        user_id = existing.id
    db.close()

    # 2. Generar token para ese usuario existente
    user_token = create_access_token(subject=str(user_id), role="user")
    headers = {"Authorization": f"Bearer {user_token}"}
    
    # 3. Intentar acceder a una ruta protegida para administradores
    response = client.post(
        "/api/v1/admin/devices", 
        headers=headers,
        json={"id": "DEV-TEST-01", "name": "Test", "max_current_threshold": 10.0}
    )
    
    # 4. Verificar que el sistema lo prohíba correctamente con 403 Forbidden
    assert response.status_code == 403
    assert response.json()["detail"] == "Privilegios insuficientes. Se requiere rol de administrador."

def test_create_device_success():
    # 1. Generar token de administrador (el usuario debe existir)
    admin_id = _ensure_admin_user()
    admin_token = create_access_token(subject=str(admin_id), role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Garantizar estado limpio: sin esto, en una segunda corrida el
    # dispositivo ya existiría y nunca se ejercería el camino de éxito.
    db = SessionLocal()
    db.query(Device).filter(Device.id == "DEV-ESP32-ADMIN-01").delete()
    db.commit()
    db.close()

    # 3. Datos del dispositivo a registrar
    payload = {
        "id": "DEV-ESP32-ADMIN-01",
        "name": "Bomba de Agua Taller",
        "max_current_threshold": 12.5
    }

    # 4. Enviar petición POST
    response = client.post("/api/v1/admin/devices", headers=headers, json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "DEV-ESP32-ADMIN-01"
    assert data["max_current_threshold"] == 12.5


def test_create_duplicate_device_returns_400():
    admin_id = _ensure_admin_user()
    admin_token = create_access_token(subject=str(admin_id), role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    payload = {
        "id": "DEV-ESP32-ADMIN-DUP-01",
        "name": "Dispositivo duplicado de prueba",
        "max_current_threshold": 10.0
    }
    client.post("/api/v1/admin/devices", headers=headers, json=payload)  # primera vez

    response = client.post("/api/v1/admin/devices", headers=headers, json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "El ID del dispositivo ya existe."