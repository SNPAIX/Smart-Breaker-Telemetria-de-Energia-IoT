from ia_assistant.intent_matcher import match_intent
from ia_assistant.schemas import DeviceRef, IntentType

DEVICES = [
    DeviceRef(id=1, name="Luz Sala"),
    DeviceRef(id=2, name="Luz Cocina"),
    DeviceRef(id=3, name="Bomba de Agua"),
]


def test_apaga_la_luz_de_la_sala_matchea_por_nombre_exacto():
    intent = match_intent("apaga la luz de la sala", DEVICES)
    assert intent.type is IntentType.SWITCH_OFF
    assert intent.device is not None
    assert intent.device.id == 1


def test_apaga_el_foco_de_la_sala_matchea_via_sinonimo():
    intent = match_intent("apaga el foco de la sala", DEVICES)
    assert intent.type is IntentType.SWITCH_OFF
    assert intent.device is not None
    assert intent.device.id == 1


def test_enciende_la_lampara_de_la_cocina():
    intent = match_intent("enciende la lampara de la cocina", DEVICES)
    assert intent.type is IntentType.SWITCH_ON
    assert intent.device is not None
    assert intent.device.id == 2


def test_consulta_de_estado():
    intent = match_intent("esta encendida la luz de la sala", DEVICES)
    assert intent.type is IntentType.QUERY_STATE
    assert intent.device is not None
    assert intent.device.id == 1


def test_consulta_de_costo_con_rango_de_dias():
    intent = match_intent("cuanto es mi consumo de la bomba esta semana", DEVICES)
    assert intent.type is IntentType.QUERY_COST
    assert intent.device is not None
    assert intent.device.id == 3
    assert intent.days == 7


def test_texto_sin_relacion_es_desconocido():
    intent = match_intent("hola como estas hoy", DEVICES)
    assert intent.type is IntentType.UNKNOWN


def test_dispositivo_ambiguo_entre_dos_luces_con_nombre_generico():
    devices = [DeviceRef(id=1, name="Luz"), DeviceRef(id=2, name="Luz")]
    intent = match_intent("apaga la luz", devices)
    assert intent.type is IntentType.SWITCH_OFF
    assert intent.device is None
    assert len(intent.ambiguous_candidates) == 2


def test_sin_dispositivos_no_encuentra_match():
    intent = match_intent("apaga la luz de la sala", [])
    assert intent.type is IntentType.SWITCH_OFF
    assert intent.device is None
