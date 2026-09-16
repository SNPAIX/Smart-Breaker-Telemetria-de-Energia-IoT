# Etapa 1 — Fundación del backend

- `Settings` centralizado (`app/config.py`), reemplaza `os.getenv` disperso.
- Routers reorganizados: `app/routers/` → `app/api/{iot,app,admin}` + `app/api/auth.py`.
- Verificado end-to-end: Docker Compose real, Postgres real, `/health` y `/docs` OK, `ruff`/`mypy` limpios, 52 tests, 100% cobertura.
- Commit: `b8a142e`.
