#  AI_LOG — Bitácora de Uso de IA Responsable

> **Proyecto:** VoltGuard — Smart Breaker & Telemetría de Energía IoT  
> **Equipo:** 3 Integrantes  

---

##  Registro de Interacciones y Decisiones Técnica

### Entrada #001-Diseño de arquitectura y Definicion de Stack
* **Prompt / Consulta a la IA:**  
  *"Necesitamos diseñar la arquitectura base para un sistema IoT de corte de energía (Smart Breaker) que ingiera lecturas de un ESP32, gestione roles (User/Admin) y cumpla con el piso profesional del reto final (FastAPI, PostgreSQL, Docker, CI/CD)."*
* **Sugerencia Generada por la IA:**  
  Propuso una arquitectura monolítica simple con FastAPI, un único router de endpoints y un modelo plano para lecturas y usuarios.
* **Criterio de Aceptación / Rechazo:**  
  * **Aceptado:** Uso de FastAPI con Pydantic V2, PostgreSQL 15 Alpine, SQLAlchemy 2.x, Alembic y construcción *multi-stage* en Docker con `python:3.12-slim`.
  * **Rechazado:** La estructura de un solo router. Se ajustó manualmente para separar la **API Operativa** (ingesta IoT y usuario final) de la **API de Administración** (dashboard agrupado y RBAC), atendiendo la sugerencia de evaluación del profesor.

---

### Entrada #002 — Modelado de Datos (SQLAlchemy 2.x) y Migraciones
* **Prompt / Consulta a la IA:**  
  *"Escribe los modelos de SQLAlchemy 2.x para las entidades User, Device, DeviceGroup y Reading con relaciones bidireccionales y tipos estrictos de Python 3.12."*
* **Sugerencia Generada por la IA:**  
  Generó los modelos usando la sintaxis antigua de SQLAlchemy (`Column(Integer, primary_key=True)`).
* **Criterio de Aceptación / Rechazo:**  
  * **Rechazado:** Se descartó el estilo antiguo de SQLAlchemy 1.x.
  * **Modificado/Aceptado:** Se reescribió utilizando la sintaxis moderna con `Mapped[...]` y `mapped_column(...)`, garantizando compatibilidad total con el tipado estricto de `mypy`.

---

### Entrada #003 — Configuración de Alembic y Resolución de Errores
* **Prompt / Consulta a la IA:**  
  *"Fallo al ejecutar `alembic revision --autogenerate`: ImportError 'Base' from 'app.db' y error en la plantilla de script."*
* **Sugerencia Generada por la IA:**  
  Ajustar `app/db.py` usando `DeclarativeBase` explícito y corregir `migrations/env.py` e `ini` para importar `Base` y leer las variables de entorno de PostgreSQL.
* **Criterio de Aceptación / Rechazo:**  
  * **Aceptado al 100%:** Se corrigió la estructura de importación y se reconfiguró `script.py.mako`, logrando aplicar la migración `init_db` exitosamente sobre la base de datos PostgreSQL en Docker.

---

##  Experimento de Uso de IA y Lecciones Aprendidas

1. **Validación sobre Generación:** El código generado para modelos ORM debe ser auditado manualmente para asegurar que cumpla con las reglas de negocio y los estándares estStrictos de tipado (`mypy`).
2. **Control de Contexto:** Proporcionar la versión exacta de las librerías (ej. Pydantic V2, SQLAlchemy 2.x) en el prompt evita sugerencias con sintaxis obsoleta o deprecada.