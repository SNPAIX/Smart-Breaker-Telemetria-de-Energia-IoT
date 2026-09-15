# Contexto de build: la raíz del repo (ver docker-compose.yml, `context: .`)
# — necesita ver `front/` para compilar el build estático.

# Etapa 1: build del frontend
FROM node:20-alpine AS front-builder

WORKDIR /app

COPY front/package.json front/package-lock.json ./
# --legacy-peer-deps: openapi-typescript pide typescript ^5.x como peer,
# pero el proyecto fija ~6.0.2 — mismo choque no bloqueante que en
# mobile/, openapi-typescript funciona bien igual con TS 6.
RUN npm ci --legacy-peer-deps

COPY front/ .

# Relativo (mismo origen) a propósito: Caddy sirve el build estático y
# hace proxy de /api/* al backend bajo el mismo dominio/puerto, así que el
# frontend no necesita saber ninguna IP ni puerto — nunca hay CORS de por
# medio en este despliegue, a diferencia del desarrollo local (etapa 13),
# donde front corre en otro puerto que el backend.
ENV VITE_API_BASE_URL=""
RUN npm run build

# Etapa 2: Caddy sirviendo el build + proxy hacia el backend
FROM caddy:2-alpine

COPY infra/Caddyfile /etc/caddy/Caddyfile
COPY --from=front-builder /app/dist /srv/front
