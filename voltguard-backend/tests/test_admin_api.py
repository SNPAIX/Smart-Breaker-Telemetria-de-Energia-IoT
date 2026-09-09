from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token, get_password_hash
from app.db import SessionLocal
from app.models.entities import User

client = TestClient(app)

def test_admin_dashboard_access():
    # 1. Generar token con rol de administrador
    admin_token = create_access_token(subject="1", role="admin")
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
            id=99,
            email="normal_test@voltguard.com",
            hashed_password=get_password_hash("password123"),
            role="user"
        )
        db.add(normal_user)
        db.commit()
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
    # 1. Generar token de administrador
    admin_token = create_access_token(subject="1", role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 2. Datos del dispositivo a registrar
    payload = {
        "id": "DEV-ESP32-ADMIN-01",
        "name": "Bomba de Agua Taller",
        "max_current_threshold": 12.5
    }
    
    # 3. Enviar petición POST
    response = client.post("/api/v1/admin/devices", headers=headers, json=payload)
    
    # Aceptamos 201 (creado) o 400 (si ya fue creado en una ejecución previa)
    assert response.status_code in [201, 400]
    if response.status_code == 201:
        data = response.json()
        assert data["id"] == "DEV-ESP32-ADMIN-01"
        assert data["max_current_threshold"] == 12.5