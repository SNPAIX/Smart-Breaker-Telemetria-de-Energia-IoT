# 0018: Calidad, CI/CD y observabilidad — cierre del backend

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

Esta etapa no partía de cero: `.github/workflows/ci.yml` ya apuntaba a `backend-server/` y a la rama `experiment/voltguard-platform-v2` desde la etapa 0, y **cada uno de los 10 commits anteriores ya disparó una corrida real de GitHub Actions**, todas en verde (`gh run list` lo confirma). El gate de cobertura del 80% tampoco era nuevo: `pyproject.toml` ya traía `addopts = "... --cov-fail-under=80"` desde el repo base, así que `pytest` a secas ya lo aplicaba en cada corrida local de este roadmap.

## Decisión

1. Se hizo explícito en el propio paso de CI (`pytest --cov=app --cov-report=term-missing --cov-fail-under=80`) lo que antes dependía silenciosamente de `pyproject.toml` — más robusto ante un futuro cambio accidental de `addopts`, y más legible para quien lea el workflow sin conocer ese detalle.
2. `/health/ready` (nuevo): a diferencia de `/health` (vida del proceso, nunca toca la base), consulta `SELECT 1` contra Postgres y responde 503 si falla — separación explícita que ya sugería el roadmap en vez de sobrecargar `/health`.
3. Auditoría de calidad sobre todo `app/`: sin `print()`, sin `TODO`/`FIXME` colgados, sin secretos hardcodeados fuera de los defaults de desarrollo ya marcados como inseguros (`_DEV_FALLBACK_KEY` en `security.py`), un solo `# type: ignore[operator]` preexistente y acotado a un código de error específico (no un `# type: ignore` genérico).
4. `.env.example` completado: le faltaban `ENVIRONMENT`, `ACCESS_TOKEN_EXPIRE_MINUTES` (desde el repo base) y `DEVICE_ONLINE_THRESHOLD_SECONDS` (agregado en la etapa 7) — quien clone el repo ahora ve documentada toda la configuración real que `app/config.py::Settings` acepta.
5. Se verificó manualmente (sin commitear el cambio) que el gate de cobertura realmente rompe el build: ignorando los archivos de test de varias etapas, `pytest` cae a 70.94% y termina con exit code 1 y el mensaje `FAIL Required test coverage of 80% not reached` — no es un gate decorativo.

## Consecuencias

* **Positivas:** el backend queda con evidencia continua (11 corridas reales de CI, no solo verificación local en esta sesión) de que compila, pasa lint/tipos, migra limpio y mantiene ≥80% de cobertura en cada etapa — no es una afirmación de cierre, es un historial verificable en la pestaña Actions del repo.
* **Negativas:** ninguna — esta etapa fue mayormente auditoría y endurecimiento de algo que ya funcionaba, no una reconstrucción.
