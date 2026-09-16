"""Coincidencia determinista — sin modelo, sin red. Cubre la gran mayoría
de comandos reales: acción + tipo de dispositivo con sinónimos + fuzzy
match contra los nombres reales de los dispositivos del usuario."""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from ia_assistant.normalize import normalize_text
from ia_assistant.schemas import DeviceRef, IntentType, VoiceIntent
from ia_assistant.synonyms import (
    DAY_RANGE_PHRASES,
    DEFAULT_COST_DAYS,
    DEVICE_TYPE_SYNONYMS,
    QUERY_COST_WORDS,
    QUERY_STATE_FULL_PHRASES,
    QUERY_STATE_STEMS,
    TURN_OFF_WORDS,
    TURN_ON_WORDS,
)

# Por debajo de esto, el matcher determinista no confía en su propia
# elección de dispositivo y deja la puerta abierta al fallback (si está
# disponible) en vez de arriesgarse a actuar sobre el dispositivo
# equivocado.
DEVICE_MATCH_THRESHOLD = 70.0

# Si el segundo mejor candidato queda a menos de esto del primero, se
# considera ambiguo en vez de forzar una elección.
AMBIGUITY_MARGIN = 8.0


def _detect_type(words: set[str], normalized: str) -> IntentType:
    if words & TURN_ON_WORDS:
        return IntentType.SWITCH_ON
    if words & TURN_OFF_WORDS:
        return IntentType.SWITCH_OFF
    if any(re.search(rf"\b{re.escape(phrase)}\b", normalized) for phrase in QUERY_STATE_FULL_PHRASES):
        return IntentType.QUERY_STATE
    if any(word.startswith(stem) for word in words for stem in QUERY_STATE_STEMS):
        return IntentType.QUERY_STATE
    if words & QUERY_COST_WORDS:
        return IntentType.QUERY_COST
    return IntentType.UNKNOWN


def _expand_with_synonyms(normalized: str) -> str:
    words = normalized.split()
    expanded = [DEVICE_TYPE_SYNONYMS.get(word, word) for word in words]
    return " ".join(expanded)


def _detect_days(normalized: str) -> int:
    for phrase, days in DAY_RANGE_PHRASES:
        if phrase in normalized:
            return days
    return DEFAULT_COST_DAYS


def _best_device_match(
    expanded_text: str, devices: list[DeviceRef]
) -> tuple[DeviceRef | None, float, list[DeviceRef]]:
    if not devices:
        return None, 0.0, []

    scored = sorted(
        (
            (device, fuzz.token_set_ratio(expanded_text, normalize_text(device.name)))
            for device in devices
        ),
        key=lambda pair: pair[1],
        reverse=True,
    )
    best_device, best_score = scored[0]
    if best_score < DEVICE_MATCH_THRESHOLD:
        return None, best_score, []

    close_candidates = [device for device, score in scored if best_score - score < AMBIGUITY_MARGIN]
    if len(close_candidates) > 1:
        return None, best_score, close_candidates

    return best_device, best_score, []


def find_device(hint: str, devices: list[DeviceRef]) -> tuple[DeviceRef | None, list[DeviceRef]]:
    """Punto de entrada público reutilizado por el fallback de LLM: incluso
    cuando el modelo propone a qué dispositivo se refería el usuario, esa
    propuesta se vuelve a validar acá contra los dispositivos reales en vez
    de aceptarse tal cual — un nombre inventado por el modelo simplemente no
    va a matchear con nada por encima del umbral."""
    expanded = _expand_with_synonyms(normalize_text(hint))
    device, _score, ambiguous = _best_device_match(expanded, devices)
    return device, ambiguous


def match_intent(text: str, devices: list[DeviceRef]) -> VoiceIntent:
    """Intenta resolver la intención completa sin ningún modelo. Devuelve
    `IntentType.UNKNOWN` con `confidence=0.0` si no logra determinar la
    acción, y deja `device=None` con `ambiguous_candidates` lleno si la
    acción es clara pero el dispositivo no se puede distinguir."""
    normalized = normalize_text(text)
    words = set(normalized.split())
    intent_type = _detect_type(words, normalized)

    if intent_type is IntentType.UNKNOWN:
        return VoiceIntent(type=IntentType.UNKNOWN, source="matcher")

    if intent_type is IntentType.QUERY_COST:
        expanded = _expand_with_synonyms(normalized)
        device, score, ambiguous = _best_device_match(expanded, devices)
        days = _detect_days(normalized)
        return VoiceIntent(
            type=intent_type,
            device=device,
            days=days,
            confidence=score / 100.0,
            source="matcher",
            ambiguous_candidates=tuple(ambiguous),
        )

    expanded = _expand_with_synonyms(normalized)
    device, score, ambiguous = _best_device_match(expanded, devices)
    return VoiceIntent(
        type=intent_type,
        device=device,
        confidence=score / 100.0,
        source="matcher",
        ambiguous_candidates=tuple(ambiguous),
    )
