import json
import logging
import os
import sys
from typing import Any, ClassVar


class JSONFormatter(logging.Formatter):
    """Formatea cada log como una línea JSON (uno por evento), en vez de
    texto plano. Requisito de la sección "Observabilidad" de las bases del
    reto: los logs deben poder ingerirse por herramientas como
    CloudWatch/Datadog/ELK sin parsing frágil con regex.
    """

    RESERVED_ATTRS: ClassVar[set[str]] = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Campos extra pasados vía logger.info(..., extra={...}), por
        # ejemplo device_id, event_type, status_code.
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configura el logger raíz para emitir JSON a stdout.

    Nivel configurable con la variable de entorno LOG_LEVEL (default INFO),
    para poder subir a DEBUG en un contenedor específico sin reconstruir
    la imagen.
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Uvicorn trae sus propios loggers con su propio formato de texto;
    # los redirigimos al mismo handler JSON para no mezclar dos formatos
    # en la misma salida de logs.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
