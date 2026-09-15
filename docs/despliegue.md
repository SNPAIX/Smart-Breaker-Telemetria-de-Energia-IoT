# Despliegue de la plataforma completa (etapa 15)

Todo local, sin ningún paso de `docker push` ni dependencia de un registry
o proveedor cloud específico. Cada máquina construye sus propias imágenes
con `docker compose build` a partir del código fuente. Para mover la
plataforma a otra máquina **no se publica nada** — se copia el repositorio
completo (comprimido en un `.zip`, o vía `git clone` si hay acceso a git
en el destino) y se buildea ahí mismo.

## Qué levanta este compose

`docker-compose.yml` en la raíz del repo levanta 3 contenedores:

- **`db`** — Postgres 15, sin puerto publicado al host (solo la red interna
  de Docker le habla).
- **`api`** — el backend FastAPI, corre `alembic upgrade head` solo al
  arrancar y después `uvicorn` — sin puerto publicado al host tampoco.
- **`proxy`** — Caddy, con dos responsabilidades: sirve el build estático
  de `front/` (compilado dentro de la misma imagen, `infra/proxy.Dockerfile`)
  y hace de reverse proxy de `/api/*` hacia `api:8000`. Es el único
  contenedor con puertos publicados (`80` y `443`).

Ningún componente del compose ni del código asume S3, RDS, ni ningún otro
servicio propietario de un cloud — todo corre en contenedores estándar
(`postgres:15-alpine`, `python:3.12-slim`, `node:20-alpine`, `caddy:2-alpine`).

Este archivo es distinto de `backend-server/docker-compose.yml`, que sigue
existiendo tal cual para desarrollo del backend solo (con hot-reload por
bind-mount y el puerto de Postgres expuesto para conectarse con un
cliente SQL) — no lo reemplaza, son dos propósitos distintos.

## Requisitos en la máquina destino

- Docker + Docker Compose v2 (`docker compose version`).
- Nada más — no hace falta Node, Python, ni ninguna otra herramienta
  instalada en el host: todo el build ocurre dentro de los contenedores.

## Procedimiento desde cero

### 1. Llevar el código a la máquina destino

**Opción A — copiar un `.zip`** (la forma prevista para este proyecto, sin
depender de ningún servicio externo):

```bash
# En la máquina origen
cd ..
zip -r voltguard-platform.zip "Proyect Final-v2" -x "*/node_modules/*" -x "*/dist/*" -x "*/.git/*"
# Copiar voltguard-platform.zip a la máquina destino por el medio que sea
# (USB, red local, lo que corresponda) y descomprimir ahí.
```

**Opción B — `git clone`**, si el destino tiene acceso al repositorio:

```bash
git clone <url-del-repo> voltguard-platform
cd voltguard-platform
git checkout experiment/voltguard-platform-v2   # o main, según lo que se despliegue
```

### 2. Configurar secretos

```bash
cp .env.example .env
```

Editar `.env` y completar como mínimo:
- `POSTGRES_PASSWORD` — una contraseña real, no la de ejemplo.
- `SECRET_KEY` — generar una con `python -c "import secrets; print(secrets.token_hex(32))"`.

`ENABLE_VOICE_ASSISTANT`/`VOICE_ASSISTANT_ENABLED` quedan en `false` salvo
que se quiera el asistente de voz activo (ver `IA-Assistant/README.md` —
agrega tiempo de build real por la compilación nativa con mypyc).

### 3. Levantar todo

```bash
docker compose up --build -d
```

Esto construye las 3 imágenes localmente (nada se descarga de un registry
propio, solo las imágenes base públicas de Docker Hub: `postgres`,
`python`, `node`, `caddy`) y arranca los 3 contenedores. Las migraciones de
Alembic corren solas al iniciar `api` — no hace falta ningún paso manual.

### 4. Verificar

```bash
docker compose ps                          # los 3 contenedores "Up"
curl -sk https://localhost/                # el frontend responde (200)
curl -sk -X POST https://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@voltguard.com","password":"cambiar-esto","role":"admin"}'
```

El certificado TLS es **autofirmado** (Caddy actúa como su propia CA
local, directiva `tls internal` en `infra/Caddyfile`) — el navegador va a
marcarlo como no confiable la primera vez, es esperado. Si en algún
momento hay un dominio real con DNS público apuntando a esta máquina,
reemplazar `localhost` por ese dominio en `infra/Caddyfile` y borrar la
línea `tls internal` — Caddy emite un certificado real de Let's Encrypt
automáticamente, sin ningún otro cambio.

### 5. Persistencia

Los datos de Postgres viven en el volumen nombrado `postgres_data` (por
proyecto: `<carpeta>_postgres_data`), fuera del ciclo de vida de los
contenedores — `docker compose down && docker compose up` los conserva.
Solo `docker compose down -v` (con `-v`) los borra — no usarlo salvo que
sea intencional.

## Migrar a otra máquina más adelante

Repetir el paso 1 (zip o clone) en la máquina nueva y el paso 2-3 ahí. Si
se quiere migrar **con los datos** (no solo el código), respaldar el
volumen de Postgres antes:

```bash
docker compose exec db pg_dump -U voltguard_user voltguard_db > respaldo.sql
```

Copiar `respaldo.sql` junto con el zip del código, y restaurarlo en la
máquina nueva después de `docker compose up -d` (con la base ya
migrada/vacía):

```bash
docker compose exec -T db psql -U voltguard_user voltguard_db < respaldo.sql
```

No hay ningún paso de sincronización automática entre máquinas — es
explícitamente manual, por decisión del proyecto (sin infraestructura
cloud de por medio).

## Qué falta para producción real (fuera del alcance de esta etapa)

- Un dominio real + DNS apuntando a la IP pública de la máquina, para
  reemplazar el certificado autofirmado por uno real de Let's Encrypt
  (cambio de una línea en `infra/Caddyfile`, ver paso 4).
- Backups automatizados de `respaldo.sql` (hoy es manual).
- Un firewall en la máquina destino que solo permita `80`/`443` desde
  afuera — Docker ya no expone `5432`/`8000` al host en este compose, pero
  el propio SO/firewall de la máquina sigue siendo responsabilidad de
  quien la administre.
