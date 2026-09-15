"""Endpoint del asistente de voz (etapa 14). Solo se importa/registra desde
`app/main.py` cuando `settings.voice_assistant_enabled` es `True` — si
`IA-Assistant/` no está instalado, este módulo no debe cargarse nunca.

Toda la interpretación de texto vive en el paquete aislado `ia_assistant`;
acá solo se traduce hacia/desde los modelos reales de la base de datos y se
ejecuta la acción con los mismos servicios que ya usa `/api/v1/app`."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ia_assistant.llm_fallback import IIntentEngine, build_default_engine
from ia_assistant.orchestrator import resolve_voice_command
from ia_assistant.responder import build_spoken_text
from ia_assistant.schemas import DeviceRef, ExecutionOutcome, IntentType

from app.config import settings
from app.core.dependencies import get_current_user
from app.db import get_db
from app.models.entities import Device, User
from app.schemas.app_api import VoiceQueryIn, VoiceQueryOut
from app.services.costs import compute_cost_breakdown
from app.services.devices import switch_device
from app.services.sites import list_user_devices

router = APIRouter(prefix="/api/v1/app/voice", tags=["Asistente de voz"])

# Construido una sola vez por proceso — `LlamaCppIntentEngine` carga el
# modelo de forma perezosa en el primer uso real, así que instanciarlo acá
# no le agrega arranque lento a la app si nunca se llega a usar.
_llm_engine: IIntentEngine | None = build_default_engine(settings.voice_assistant_model_path)


def _resolve_outcome(db: Session, device: Device, intent_type: IntentType, days: int | None) -> ExecutionOutcome:
    if intent_type is IntentType.SWITCH_ON or intent_type is IntentType.SWITCH_OFF:
        desired = "ON" if intent_type is IntentType.SWITCH_ON else "OFF"
        try:
            switch_device(db, device, desired)
        except HTTPException as exc:
            error_code = "locked_out" if exc.status_code == status.HTTP_409_CONFLICT else "internal"
            return ExecutionOutcome(ok=False, error_code=error_code, device_name=device.name)
        return ExecutionOutcome(ok=True, device_name=device.name)

    if intent_type is IntentType.QUERY_STATE:
        return ExecutionOutcome(
            ok=True,
            device_name=device.name,
            actual_state=device.actual_state,
            is_locked_out=device.is_locked_out,
        )

    if intent_type is IntentType.QUERY_COST:
        breakdown = compute_cost_breakdown(db, device, days=days or 14)
        return ExecutionOutcome(
            ok=True,
            device_name=device.name,
            days_analyzed=breakdown.days_analyzed,
            total_kwh=breakdown.total_kwh,
            total_cost=breakdown.total_cost,
            currency=breakdown.currency,
        )

    return ExecutionOutcome(ok=False, error_code="internal", device_name=device.name)


@router.post("/query", response_model=VoiceQueryOut)
def voice_query(
    payload: VoiceQueryIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoiceQueryOut:
    devices = list_user_devices(db, current_user.id)
    devices_by_id = {device.id: device for device in devices}
    device_refs = [DeviceRef(id=device.id, name=device.name) for device in devices]

    intent = resolve_voice_command(payload.text, device_refs, llm_engine=_llm_engine)

    outcome: ExecutionOutcome | None = None
    action_taken = False
    if intent.device is not None:
        device = devices_by_id[intent.device.id]
        outcome = _resolve_outcome(db, device, intent.type, intent.days)
        action_taken = outcome.ok and intent.type in (IntentType.SWITCH_ON, IntentType.SWITCH_OFF)

    return VoiceQueryOut(
        spoken_text=build_spoken_text(intent, outcome),
        action_taken=action_taken,
        intent_type=intent.type.value,
        device_id=intent.device.id if intent.device else None,
    )
