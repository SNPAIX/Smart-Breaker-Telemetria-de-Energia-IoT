"""Simulador de dispositivo VoltGuard.

Reproduce el contrato HTTP que el firmware ESP32-C3 habla contra
`/api/v1/iot/*`, para poder probar el backend de punta a punta sin
hardware físico (ver `roadmap/ORIGINAL-SPEC-HARDWARE-VALIDATION.md`).

Acepta cualquier cliente HTTP compatible con la interfaz de httpx (métodos
`get`/`post` con `json=`/`headers=`) — tanto `httpx.Client(base_url=...)`
contra un servidor real como `fastapi.testclient.TestClient(app)` en
proceso satisfacen esa interfaz. El mismo simulador sirve para la suite de
pytest (etapas 4, 5, 6, 11) y para una verificación manual contra el stack
real levantado con Docker Compose, y más adelante para el arnés de
Hardware-in-the-Loop de la etapa 12.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol


class HttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...
    def post(self, url: str, **kwargs: Any) -> Any: ...


@dataclass
class DeviceSimulator:
    client: HttpClient
    public_id: str
    secret: str

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Device {self.public_id}:{self.secret}"}

    def send_telemetry(
        self,
        *,
        sequence: int,
        voltage_v: float = 127.0,
        current_a: float = 1.5,
        power_w: float = 190.0,
        energy_kwh: float = 1.0,
        frequency_hz: float = 60.0,
        power_factor: float = 0.95,
        relay_state: str = "ON",
        timestamp: datetime | None = None,
    ) -> Any:
        body = {
            "sequence": sequence,
            "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
            "voltage_v": voltage_v,
            "current_a": current_a,
            "power_w": power_w,
            "energy_kwh": energy_kwh,
            "frequency_hz": frequency_hz,
            "power_factor": power_factor,
            "relay_state": relay_state,
        }
        return self.client.post("/api/v1/iot/telemetry", json=body, headers=self._headers())

    def send_malformed_telemetry(self, body: dict[str, Any]) -> Any:
        """Envía un payload arbitrario tal cual, sin validar del lado del
        simulador — para ejercitar el escenario "malformed telemetry" contra
        la validación real del servidor."""
        return self.client.post("/api/v1/iot/telemetry", json=body, headers=self._headers())

    def send_heartbeat(self) -> Any:
        return self.client.post("/api/v1/iot/heartbeat", headers=self._headers())

    def list_pending_commands(self) -> Any:
        return self.client.get("/api/v1/iot/commands/pending", headers=self._headers())

    def ack_command(self, command_id: int, actual_state: str) -> Any:
        return self.client.post(
            f"/api/v1/iot/commands/{command_id}/ack",
            json={"actual_state": actual_state},
            headers=self._headers(),
        )
