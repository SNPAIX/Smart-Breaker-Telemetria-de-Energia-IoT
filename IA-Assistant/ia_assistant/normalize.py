"""Normalización de texto compartida — sin acentos y en minúsculas, para
que "está" y "esta", o "cuánto" y "cuanto", matcheen igual contra el
vocabulario cerrado de `synonyms.py`."""
from __future__ import annotations

import re
import unicodedata

_ACCENTS = str.maketrans("áéíóúñ", "aeioun")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text.strip().lower())
    text = text.translate(_ACCENTS)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
