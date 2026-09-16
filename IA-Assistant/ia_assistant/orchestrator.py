"""Punto de entrada único del módulo. `backend-server` solo debería importar
`resolve_voice_command` (y los tipos de `schemas.py`) — todo lo demás es
detalle interno reemplazable."""
from __future__ import annotations

from ia_assistant.intent_matcher import find_device, match_intent
from ia_assistant.llm_fallback import IIntentEngine
from ia_assistant.schemas import DeviceRef, IntentType, VoiceIntent
from ia_assistant.synonyms import DEFAULT_COST_DAYS

_ACTION_TO_TYPE = {
    "encender": IntentType.SWITCH_ON,
    "apagar": IntentType.SWITCH_OFF,
    "consultar_estado": IntentType.QUERY_STATE,
    "consultar_costo": IntentType.QUERY_COST,
}

def resolve_voice_command(
    text: str,
    devices: list[DeviceRef],
    *,
    llm_engine: IIntentEngine | None = None,
) -> VoiceIntent:
    """Resuelve un comando de voz transcrito a una intención estructurada.

    1. Intenta el matcher determinista (sin red, sin modelo).
    2. Si no logra determinar la acción, y hay un motor de fallback
       disponible, le pasa el texto — pero el dispositivo que el modelo
       proponga se vuelve a validar contra la lista real (`find_device`),
       nunca se acepta a ciegas.
    3. Si nada resuelve, devuelve `IntentType.UNKNOWN` — el llamador decide
       qué decir en ese caso (ver `responder.py`).
    """
    intent = match_intent(text, devices)

    needs_fallback = intent.type is IntentType.UNKNOWN or (
        intent.device is None and not intent.ambiguous_candidates
    )
    if not needs_fallback or llm_engine is None or not llm_engine.is_available():
        return intent

    guess = llm_engine.extract(text)
    if not guess:
        return intent

    action = str(guess.get("action", "")).strip().lower()
    guessed_type = _ACTION_TO_TYPE.get(action)
    if guessed_type is None:
        return intent

    device_hint = str(guess.get("device_hint", "") or "")
    device, ambiguous = find_device(device_hint, devices) if device_hint else (None, [])

    days = guess.get("days")
    days = int(days) if isinstance(days, int) else (DEFAULT_COST_DAYS if guessed_type is IntentType.QUERY_COST else None)

    return VoiceIntent(
        type=guessed_type,
        device=device,
        days=days,
        confidence=0.5,  # el LLM no da una probabilidad calibrada, pero al haber
        # pasado la revalidación determinista contra dispositivos reales, se
        # considera una intención utilizable.
        source="llm",
        ambiguous_candidates=tuple(ambiguous),
    )
