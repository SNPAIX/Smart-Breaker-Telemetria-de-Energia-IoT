# Contexto de build: la raíz del repo (ver docker-compose.yml, `context: ..`)
# — necesario para que esta imagen pueda ver `IA-Assistant/`, que vive fuera
# de `backend-server/` a propósito (etapa 14, módulo aislado y desacoplable).

# Etapa 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend-server/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Asistente de voz (etapa 14) — opcional y desacoplado del resto del
# backend. Se activa con --build-arg ENABLE_VOICE_ASSISTANT=true; si se
# omite (default), la imagen no instala ni compila nada de IA-Assistant/ y
# el backend arranca igual, con `settings.voice_assistant_enabled=False`.
# Cuando se activa, el módulo se compila a extensión nativa (mypyc) en vez
# de copiarse como fuente interpretada, por costo de latencia por consulta.
ARG ENABLE_VOICE_ASSISTANT=false

COPY IA-Assistant /tmp/IA-Assistant

# El directorio destino se crea siempre (vacío si el flag está apagado)
# para que el COPY --from=builder de la etapa runner nunca falle por falta
# de origen, sin recurrir a comodines para "hacerlo opcional". mypyc genera,
# además de un .so por módulo dentro de `ia_assistant/`, un módulo nativo
# compartido de soporte a nivel raíz (`<hash>__mypyc.*.so`) del que esos
# .so dependen en tiempo de import — hay que copiarlo también, como
# hermano de `ia_assistant/`, no dentro.
RUN mkdir -p /build/ia_assistant && \
    if [ "$ENABLE_VOICE_ASSISTANT" = "true" ]; then \
        pip install --no-cache-dir --user setuptools -r /tmp/IA-Assistant/requirements.txt mypy && \
        cd /tmp/IA-Assistant && \
        python -m mypyc ia_assistant/normalize.py ia_assistant/schemas.py \
            ia_assistant/synonyms.py ia_assistant/intent_matcher.py \
            ia_assistant/responder.py ia_assistant/llm_fallback.py \
            ia_assistant/orchestrator.py ia_assistant/__init__.py && \
        find ia_assistant -name "*.py" -delete && \
        cp -r ia_assistant/. /build/ia_assistant/ && \
        cp *__mypyc*.so /build/; \
    fi

# Etapa 2: Runner
FROM python:3.12-slim AS runner

WORKDIR /app

ARG ENABLE_VOICE_ASSISTANT=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/opt/vendor

COPY --from=builder /root/.local /root/.local
COPY --chmod=644 backend-server/. .

# Vive en /opt (fuera de /app) a propósito: docker-compose.yml monta
# `.:/app` en desarrollo, y ese bind-mount reemplazaría cualquier cosa
# copiada dentro de /app con el contenido de `backend-server/` del host
# (que no tiene este directorio). Si ENABLE_VOICE_ASSISTANT=false esto
# copia solo el directorio vacío — el import queda protegido igual por
# `settings.voice_assistant_enabled` en app/main.py, que nunca intenta
# importar `ia_assistant` en ese caso.
COPY --from=builder /build /opt/vendor

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
