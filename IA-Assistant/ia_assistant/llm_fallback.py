"""Fallback opcional con LLM local para frases que el matcher determinista
no logra resolver. Sigue el mismo patrón de interfaz explícita que
`ILlmEngine` en el proyecto de asistente local en C++, pero aquí el LLM
NUNCA decide la acción final por sí solo: solo propone una interpretación
de texto libre, y esa propuesta se vuelve a pasar por el mismo fuzzy match
determinista contra los dispositivos reales antes de aceptarse (ver
`orchestrator.py`). Así, un desvío del modelo (alucinar un dispositivo que
no existe, por ejemplo) nunca se traduce en una acción real.

Si `llama-cpp-python` no está instalado o no hay un archivo de modelo
configurado, `build_default_engine` devuelve `None` y el orquestador sigue
funcionando solo con el matcher determinista."""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from mypy_extensions import mypyc_attr

logger = logging.getLogger("ia_assistant.llm_fallback")

_SYSTEM_PROMPT = (
    "Extrae la intencion de un comando de voz para controlar dispositivos "
    "electricos del hogar. Responde SOLO con un JSON de una linea, sin "
    "texto adicional, con esta forma exacta: "
    '{"action": "encender"|"apagar"|"consultar_estado"|"consultar_costo"|"desconocido", '
    '"device_hint": "<texto libre que describe el dispositivo mencionado, o vacio>", '
    '"days": <numero entero de dias si se menciona un periodo, o null>}'
)


@mypyc_attr(allow_interpreted_subclasses=True)
class IIntentEngine(ABC):
    """Contrato que cualquier motor de fallback debe cumplir. Se marca
    explícitamente para permitir subclases interpretadas (no compiladas) —
    los tests usan un motor falso en Python puro, y `backend-server` podría
    querer implementar uno propio sin tener que recompilar este paquete."""

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def extract(self, text: str) -> dict[str, Any] | None:
        """Devuelve `{"action": str, "device_hint": str, "days": int|None}`
        o `None` si no pudo interpretar nada útil."""


class LlamaCppIntentEngine(IIntentEngine):
    def __init__(self, model_path: str, *, max_tokens: int = 80) -> None:
        self._model_path = model_path
        self._max_tokens = max_tokens
        self._llm: Any | None = None
        self._load_failed = False

    def _ensure_loaded(self) -> bool:
        if self._llm is not None:
            return True
        if self._load_failed:
            return False
        if not Path(self._model_path).is_file():
            logger.warning("Modelo de fallback no encontrado en %s — fallback deshabilitado.", self._model_path)
            self._load_failed = True
            return False
        try:
            from llama_cpp import Llama  # type: ignore[import-not-found]
        except ImportError:
            logger.warning("llama-cpp-python no está instalado — fallback deshabilitado.")
            self._load_failed = True
            return False

        try:
            self._llm = Llama(model_path=self._model_path, n_ctx=512, verbose=False)
        except Exception:
            logger.exception("No se pudo cargar el modelo de fallback — fallback deshabilitado.")
            self._load_failed = True
            return False
        return True

    def is_available(self) -> bool:
        return self._ensure_loaded()

    def extract(self, text: str) -> dict[str, Any] | None:
        if not self._ensure_loaded() or self._llm is None:
            return None

        prompt = f"{_SYSTEM_PROMPT}\n\nComando: \"{text}\"\nJSON:"
        try:
            completion = self._llm(
                prompt,
                max_tokens=self._max_tokens,
                stop=["\n"],
                temperature=0.0,
            )
            raw = completion["choices"][0]["text"].strip()
            parsed = json.loads(raw)
        except Exception:
            logger.warning("Salida del LLM no interpretable, se descarta: no se ejecuta ninguna accion a ciegas.")
            return None

        if not isinstance(parsed, dict) or "action" not in parsed:
            return None
        return parsed


def build_default_engine(model_path: str | None) -> IIntentEngine | None:
    if not model_path:
        return None
    return LlamaCppIntentEngine(model_path)
