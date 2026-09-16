# Etapa 3 — Autenticación usuario + dispositivo

- `get_current_site_member(site_id, ...)`: confirma membresía de usuario en un sitio (403 si no pertenece).
- `get_current_device(authorization, ...)`: auth de dispositivo vía `Authorization: Device <public_id>:<secret>`, hash bcrypt reutilizado de usuarios, rechaza credencial revocada/incorrecta/inexistente.
- `issue_device_credential(device)`: servicio real (no script) que emiten las etapas 4/7 al dar de alta un dispositivo.
- Verificado end-to-end: 49 tests, 99.57% cobertura, `ruff`/`mypy` limpios.
