# VoltGuard Platform v2

Plataforma IoT de monitoreo, administración y protección eléctrica (Smart Breaker) — versión 2, desarrollada en la rama `experiment/voltguard-platform-v2` a partir del repositorio base [Smart-Breaker-Telemetria-de-Energia-IoT](https://github.com/SNPAIX/Smart-Breaker-Telemetria-de-Energia-IoT).



## Estructura del monorepo

```
.
├── backend-server/   # API FastAPI + PostgreSQL + Alembic (Python 3.12)
├── front/            # Dashboard administrativo (React + Vite + TypeScript)
├── mobile/           # App móvil de usuario final (Expo + React Native + TypeScript)
├── ino/              # Firmware ESP32-C3 (base validado, no modificar pines/lógica eléctrica)
└── docs/             # Documentación de referencia (PDF de propuesta, README del repo base)
```

Cada carpeta es independiente y no debe mezclar dependencias ni código de las demás. El único contrato compartido entre ellas es la API HTTP expuesta por `backend-server/`.

## Punto de partida

- **Hardware**: `ino/code.ino` — validado experimentalmente (PZEM-004T + relé sobre ESP32-C3). No modificar pines ni la lógica de medición/control ya probada; solo se le agrega la capa de red (WiFi, aprovisionamiento, llamadas HTTP al backend, cola de comandos, corte crítico local).
- **Backend**: `backend-server/` parte del código del repo base (FastAPI/SQLAlchemy/Alembic/PostgreSQL), pero requiere un rediseño de modelo de datos (abstracción de `Site`) y de superficies de API (`iot` / `app` / `admin`).
- **Frontend / Mobile**: se construyen desde cero en esta v2.

## Documentación

- [`docs/EDSIA_PROYECTO.pdf`](docs/EDSIA_PROYECTO.pdf) — propuesta original del proyecto (programa EDSIA 2026).
- [`docs/BASE-REPO-README.md`](docs/BASE-REPO-README.md) — README del repositorio base, conservado como referencia histórica.
