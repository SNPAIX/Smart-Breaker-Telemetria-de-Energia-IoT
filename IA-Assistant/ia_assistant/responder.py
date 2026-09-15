"""Arma el texto que el celular va a pronunciar por TTS. Regla no
negociable: cada plantilla solo puede citar datos que vengan en
`ExecutionOutcome` o en la propia `VoiceIntent` (el nombre del dispositivo,
el estado real, el costo real) — nunca un texto genérico tipo "listo" sin
relación con lo que realmente pasó. Si en el futuro se reemplaza esto por
generación con LLM, esta regla debe seguir aplicando: el LLM podría
parafrasear, pero nunca inventar el resultado."""
from __future__ import annotations

from ia_assistant.schemas import ExecutionOutcome, IntentType, VoiceIntent


def build_spoken_text(intent: VoiceIntent, outcome: ExecutionOutcome | None) -> str:
    if intent.type is IntentType.UNKNOWN:
        return "No se entendió ese comando. Se puede pedir encender, apagar, o consultar el estado o el costo de un dispositivo."

    if intent.ambiguous_candidates:
        names = ", ".join(device.name for device in intent.ambiguous_candidates)
        return f"Hay más de un dispositivo que coincide: {names}. Falta indicar cuál con más precisión."

    if intent.device is None:
        return "No hay ningún dispositivo registrado que coincida con eso."

    if outcome is None:
        return "No pude procesar esa solicitud en este momento."

    if intent.type is IntentType.SWITCH_ON:
        return _switch_response(outcome, desired="encender")
    if intent.type is IntentType.SWITCH_OFF:
        return _switch_response(outcome, desired="apagar")
    if intent.type is IntentType.QUERY_STATE:
        return _state_response(outcome)
    if intent.type is IntentType.QUERY_COST:
        return _cost_response(outcome, intent.days)

    return "No pude procesar esa solicitud en este momento."


def _switch_response(outcome: ExecutionOutcome, *, desired: str) -> str:
    name = outcome.device_name or "el dispositivo"
    if outcome.ok:
        verbo = "encendí" if desired == "encender" else "apagué"
        return f"Listo, {verbo} {name}."
    if outcome.error_code == "locked_out":
        return f"No pude {desired} {name} porque está bloqueado por una sobrecarga. Necesita reactivarse primero."
    if outcome.error_code == "not_found":
        return f"No encontré {name}."
    return f"No pude {desired} {name} por un problema del sistema."


def _state_response(outcome: ExecutionOutcome) -> str:
    name = outcome.device_name or "el dispositivo"
    if not outcome.ok:
        return f"No pude consultar el estado de {name}."
    if outcome.is_locked_out:
        return f"{name} está bloqueado por una sobrecarga."
    estado = "encendido" if outcome.actual_state == "ON" else "apagado"
    return f"{name} está {estado}."


def _cost_response(outcome: ExecutionOutcome, days: int | None) -> str:
    name = outcome.device_name or "ese dispositivo"
    if not outcome.ok or outcome.total_cost is None:
        return f"No pude calcular el costo de {name}."
    periodo = f"los últimos {days} días" if days else "el período analizado"
    kwh = f"{outcome.total_kwh:.2f}" if outcome.total_kwh is not None else "desconocido"
    costo = f"{outcome.total_cost:.2f} {outcome.currency or ''}".strip()
    return f"En {periodo}, {name} consumió {kwh} kilovatios hora, unos {costo}."
