import json
import logging

from app.core.logging_config import JSONFormatter


def _make_record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="voltguard.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="evento de prueba",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formatter_produces_valid_json_with_extra_fields():
    record = _make_record(device_id="DEV-01", status_code=200)
    formatted = JSONFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["message"] == "evento de prueba"
    assert payload["level"] == "INFO"
    assert payload["device_id"] == "DEV-01"
    assert payload["status_code"] == 200


def test_formatter_includes_exception_traceback():
    try:
        raise ValueError("algo salió mal")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="voltguard.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="fallo inesperado",
            args=(),
            exc_info=sys.exc_info(),
        )

    formatted = JSONFormatter().format(record)
    payload = json.loads(formatted)
    assert "exception" in payload
    assert "ValueError" in payload["exception"]
