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

### Entrada #004 — Port de las piezas de inteligencia, seguridad y CI real sobre `rama2July`
* **Prompt / Consulta a la IA:**
  *"Portar a `rama2July` las 3 piezas de inteligencia (motor de corte, detector de anomalías, proyección de costo), agregar logging estructurado en JSON, RBAC en los endpoints nuevos, sacar `SECRET_KEY` del código a variable de entorno, y revisar por qué el pipeline de CI nunca había corrido."*
* **Sugerencia Generada por la IA:**
  Identificó que el workflow de GitHub Actions estaba en una carpeta que no correspondía a la raíz esperada por CI, por lo que nunca se había disparado. Para la advertencia de `SECRET_KEY` insegura, propuso inicialmente usar `importlib.reload()` en las pruebas para forzar la reevaluación del módulo al cambiar la variable de entorno.
* **Criterio de Aceptación / Rechazo:**
  * **Aceptado:** Reubicación del workflow de CI a la carpeta correcta (quedó corriendo por primera vez de forma real). Port de las 3 piezas de inteligencia, logging en JSON y RBAC en los endpoints nuevos.
  * **Rechazado:** El uso de `importlib.reload()` para probar la advertencia de clave insegura, por ser frágil (otros módulos como `dependencies.py` importan `SECRET_KEY` por valor al arrancar el proceso, y recargar `security.py` a media suite podía desincronizar esa copia).
  * **Modificado/Aceptado:** Se extrajo la lógica de la advertencia a una función independiente (`_warn_if_insecure_key`), probada directamente con el fixture `caplog` de pytest sin recargar módulos. Resultado: 50 pruebas, 100% de cobertura, determinista en cualquier número de corridas.
---
 
##  Experimento de Uso de IA y Lecciones Aprendidas
 
1. **Validación sobre Generación:** El código generado para modelos ORM debe ser auditado manualmente para asegurar que cumpla con las reglas de negocio y los estándares estrictos de tipado (`mypy`).
2. **Control de Contexto:** Proporcionar la versión exacta de las librerías (ej. Pydantic V2, SQLAlchemy 2.x) en el prompt evita sugerencias con sintaxis obsoleta o deprecada.
3. **Preferir pruebas deterministas sobre atajos de conveniencia:** Ante un efecto secundario a nivel de módulo (como una advertencia de log al importar), aislarlo en una función propia es más robusto para pruebas que recurrir a recargar módulos, lo que puede introducir estado inconsistente entre pruebas.
4. **La configuración de CI también se audita:** Un pipeline de CI "verde" no garantiza que se esté ejecutando; verificar que el workflow viva en la ruta correcta del repositorio fue clave para detectar que nunca se había disparado.
 