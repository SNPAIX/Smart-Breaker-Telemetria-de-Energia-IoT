# IA-Assistant

Motor de interpretación de comandos de voz para VoltGuard — módulo aislado,
a la misma altura de `backend-server/`, `front/` y `mobile/`.

## Aislamiento

Este módulo no depende de `backend-server` ni de FastAPI/SQLAlchemy — recibe
texto plano y una lista de dispositivos ya resueltos, y devuelve una
intención estructurada o un texto de respuesta. Toda la ejecución real
(autenticación, base de datos, `switch_device`, costo, etc.) sigue viviendo
en `backend-server`.

Por diseño, si esta carpeta se elimina por completo, `backend-server` sigue
arrancando sin errores: el router de voz solo se importa cuando
`settings.voice_assistant_enabled` es `True` (ver
`backend-server/app/config.py` y `backend-server/app/main.py`). Esa es la
"constante global" que permite excluir toda la feature sin tocar el resto
del backend.

## Arquitectura

Inspirada en la separación por interfaces del proyecto de asistente local en
C++ (`ILlmEngine`, `ISttEngine`, etc.): cada pieza reemplazable vive detrás
de una interfaz explícita, no de un módulo monolítico.

- `schemas.py` — tipos de datos puros (sin dependencias externas).
- `synonyms.py` — diccionario cerrado de sinónimos en español (acciones y
  tipos de dispositivo) — cubre "apaga/enciende la luz/foco/lámpara de la
  sala" sin necesitar ningún modelo.
- `intent_matcher.py` — coincidencia determinista (sinónimos + fuzzy
  matching con `rapidfuzz` contra los nombres reales de los dispositivos del
  usuario). Es la ruta rápida y sin red: cubre la mayoría de comandos.
- `llm_fallback.py` — interfaz `IIntentEngine` + implementación opcional con
  `llama.cpp` (`llama-cpp-python`) para frases que el matcher determinista no
  logra resolver con confianza suficiente. Si no hay modelo GGUF configurado
  o el archivo no existe, esta ruta queda deshabilitada automáticamente — el
  matcher determinista sigue funcionando solo.
- `responder.py` — arma el texto hablado final **siempre a partir de
  plantillas rellenadas con el resultado real** devuelto por el backend
  (nunca un texto genérico ni generado libremente por el LLM). Esto es
  intencional: la confirmación de voz debe corresponder siempre a lo que
  realmente ocurrió.
- `orchestrator.py` — punto de entrada único (`resolve_voice_command`) que
  encadena matcher determinista → fallback LLM (si está disponible) → texto
  de respuesta.

## Modelo para el fallback (opcional)

Recomendado: **LiquidAI LFM2.5-350M** en formato GGUF, corrido con
`llama-cpp-python` (mismo motor que ya se usa en el proyecto de asistente
local en C++, solo que aquí corre del lado del servidor). Colocar el archivo
`.gguf` en `IA-Assistant/models/` (ignorado por git — ver `.gitignore`) y
apuntar `VOICE_ASSISTANT_MODEL_PATH` en el `.env` del backend a esa ruta.

Si el archivo no está presente, la feature completa (con el flag activado)
sigue funcionando solo con el matcher determinista — el fallback simplemente
no se activa.

## Instalación (solo si se activa la feature)

```bash
pip install -r IA-Assistant/requirements.txt
pip install -e IA-Assistant   # para que backend-server pueda importar `ia_assistant`
```

## Tests

Aislados, sin base de datos ni FastAPI:

```bash
cd IA-Assistant
pytest
```
