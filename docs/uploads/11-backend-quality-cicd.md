# Etapa 11 — Calidad, CI/CD y observabilidad

- CI ya venía funcionando en verde desde la etapa 0 (11 corridas reales confirmadas en GitHub Actions) — se hizo explícito el gate de cobertura en el propio workflow.
- `/health/ready` nuevo: chequea Postgres real (503 si falla), separado de `/health` (nunca toca la DB).
- Auditoría de calidad: sin `print()`, sin TODOs, sin secretos hardcodeados, `.env.example` completado.
- Gate de cobertura confirmado real: forzar una regresión local (ignorando tests) lo rompe (exit code 1, 70.94% < 80%) — no committeado, solo verificación.
- Verificado end-to-end: 83 tests, 95.97% cobertura, `ruff`/`mypy` limpios. **Backend MVP completo (etapas 1-11).**
