"""Vocabulario cerrado en español — a propósito chico y explícito en vez de
un modelo, para cubrir sin red ni latencia los comandos más comunes
("apaga la luz de la sala" / "apaga el foco de la sala" deben resolver al
mismo dispositivo)."""
from __future__ import annotations

# Palabras que indican encender. El matcher busca por palabra completa,
# no substring, para no confundir "prender" dentro de otra palabra.
TURN_ON_WORDS = {"enciende", "encender", "prende", "prender", "activa", "activar"}

TURN_OFF_WORDS = {"apaga", "apagar", "desactiva", "desactivar"}

# Frases completas (con límite de palabra en ambos extremos) — "cómo" o
# "está" sueltos son demasiado ambiguos, y sin límite de palabra "como
# esta" matchearía también dentro de "como estas [tú]".
QUERY_STATE_FULL_PHRASES = ("como esta", "cual es el estado", "estado de")

# Prefijos de palabra (sin límite al final, a propósito): cubren tanto la
# forma masculina como la femenina del participio ("encendido"/"encendida")
# sin necesitar una entrada por cada una.
QUERY_STATE_STEMS = ("encendid", "apagad", "prendid")

QUERY_COST_WORDS = {
    "costo",
    "cuesta",
    "gasto",
    "gaste",
    "consumo",
    "consumi",
    "kwh",
    "cuanto",
}

# Sinónimo -> palabra canónica usada para expandir el texto antes del fuzzy
# match contra los nombres reales de los dispositivos del usuario. No son
# nombres de dispositivo — son tipos genéricos que la gente usa para
# referirse a ellos en vez del nombre exacto guardado en el sistema.
DEVICE_TYPE_SYNONYMS: dict[str, str] = {
    "foco": "luz",
    "lampara": "luz",
    "bombillo": "luz",
    "bombilla": "luz",
    "luminaria": "luz",
    "motor": "bomba",
    "toma": "enchufe",
    "contacto": "enchufe",
    "tomacorriente": "enchufe",
    "clima": "aire",
    "ac": "aire",
    "aire acondicionado": "aire",
}

# Expresiones de rango de días para la consulta de costo/consumo.
DAY_RANGE_PHRASES: tuple[tuple[str, int], ...] = (
    ("hoy", 1),
    ("ayer", 2),
    ("esta semana", 7),
    ("estos dias", 7),
    ("ultima semana", 7),
    ("este mes", 30),
    ("ultimo mes", 30),
    ("estos ultimos dias", 7),
)

DEFAULT_COST_DAYS = 14
