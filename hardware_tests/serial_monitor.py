"""Lee el log serie de un ESP32-C3 real (115200 baudios) durante una sesión
de PASS físico (ver docs/claude/HIL_TEST_PLAN.md) y lo vuelca a stdout con
marca de tiempo — para correlacionar lo que imprime el dispositivo (ej.
"CORTE CRITICO LOCAL aplicado") con lo que registra el backend en ese
mismo instante.

Requiere: pip install pyserial

Uso:
    python hardware_tests/serial_monitor.py --port COM5
"""
from __future__ import annotations

import argparse
import datetime as dt

import serial


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Puerto serie del ESP32-C3 (ej. COM5, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    with serial.Serial(args.port, args.baud, timeout=1) as connection:
        print(f"Escuchando {args.port} @ {args.baud} baudios — Ctrl+C para salir.")
        while True:
            line = connection.readline()
            if not line:
                continue
            timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
            print(f"[{timestamp}] {line.decode(errors='replace').rstrip()}")


if __name__ == "__main__":
    raise SystemExit(main())
