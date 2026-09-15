from ia_assistant.llm_fallback import IIntentEngine
from ia_assistant.orchestrator import resolve_voice_command
from ia_assistant.schemas import DeviceRef, IntentType

DEVICES = [DeviceRef(id=1, name="Luz Sala"), DeviceRef(id=2, name="Bomba de Agua")]


class _FakeEngine(IIntentEngine):
    """Motor de prueba: simula lo que devolvería un LLM, incluyendo el caso
    en que "alucina" un dispositivo que no existe."""

    def __init__(self, response: dict | None):
        self._response = response

    def is_available(self) -> bool:
        return True

    def extract(self, text: str) -> dict | None:
        return self._response


def test_matcher_determinista_no_llama_al_fallback_si_ya_resolvio():
    engine = _FakeEngine({"action": "apagar", "device_hint": "bomba", "days": None})
    intent = resolve_voice_command("apaga la luz de la sala", DEVICES, llm_engine=engine)
    assert intent.source == "matcher"
    assert intent.device is not None
    assert intent.device.id == 1  # nunca llegó a usar la respuesta (equivocada) del fake engine


def test_fallback_se_usa_cuando_el_matcher_no_entiende_nada():
    engine = _FakeEngine({"action": "apagar", "device_hint": "la bomba de agua", "days": None})
    intent = resolve_voice_command("podrias cortar la bomba de agua porfa", DEVICES, llm_engine=engine)
    assert intent.source == "llm"
    assert intent.type is IntentType.SWITCH_OFF
    assert intent.device is not None
    assert intent.device.id == 2


def test_fallback_alucinando_un_dispositivo_inexistente_no_se_acepta():
    engine = _FakeEngine({"action": "apagar", "device_hint": "el microondas del garage", "days": None})
    intent = resolve_voice_command("podrias cortar el microondas porfa", DEVICES, llm_engine=engine)
    assert intent.source == "llm"
    assert intent.device is None  # el hint no matcheó con ningún dispositivo real


def test_sin_fallback_disponible_devuelve_desconocido():
    intent = resolve_voice_command("podrias cortar la bomba de agua porfa", DEVICES, llm_engine=None)
    assert intent.type is IntentType.UNKNOWN
