from ia_assistant.responder import build_spoken_text
from ia_assistant.schemas import DeviceRef, ExecutionOutcome, IntentType, VoiceIntent

DEVICE = DeviceRef(id=1, name="Luz Sala")


def test_switch_off_exitoso_cita_el_nombre_real():
    intent = VoiceIntent(type=IntentType.SWITCH_OFF, device=DEVICE, source="matcher")
    outcome = ExecutionOutcome(ok=True, device_name="Luz Sala")
    text = build_spoken_text(intent, outcome)
    assert "Luz Sala" in text
    assert "apagué" in text.lower()


def test_switch_on_bloqueado_no_dice_listo():
    intent = VoiceIntent(type=IntentType.SWITCH_ON, device=DEVICE, source="matcher")
    outcome = ExecutionOutcome(ok=False, error_code="locked_out", device_name="Luz Sala")
    text = build_spoken_text(intent, outcome)
    assert "listo" not in text.lower()
    assert "bloqueado" in text.lower()


def test_query_state_encendido():
    intent = VoiceIntent(type=IntentType.QUERY_STATE, device=DEVICE, source="matcher")
    outcome = ExecutionOutcome(ok=True, device_name="Luz Sala", actual_state="ON", is_locked_out=False)
    text = build_spoken_text(intent, outcome)
    assert "encendido" in text.lower()


def test_query_cost_cita_valores_reales():
    intent = VoiceIntent(type=IntentType.QUERY_COST, device=DEVICE, days=7, source="matcher")
    outcome = ExecutionOutcome(
        ok=True, device_name="Luz Sala", days_analyzed=7, total_kwh=4.2, total_cost=12.5, currency="MXN"
    )
    text = build_spoken_text(intent, outcome)
    assert "4.20" in text
    assert "12.50" in text


def test_intencion_desconocida_no_inventa_una_accion():
    intent = VoiceIntent(type=IntentType.UNKNOWN, source="matcher")
    text = build_spoken_text(intent, None)
    assert "no entendí" in text.lower()


def test_dispositivo_ambiguo_pide_aclaracion_en_vez_de_adivinar():
    intent = VoiceIntent(
        type=IntentType.SWITCH_OFF,
        device=None,
        source="matcher",
        ambiguous_candidates=(DeviceRef(id=1, name="Luz"), DeviceRef(id=2, name="Luz")),
    )
    text = build_spoken_text(intent, None)
    assert "más de un dispositivo" in text.lower() or "mas de un dispositivo" in text.lower()
