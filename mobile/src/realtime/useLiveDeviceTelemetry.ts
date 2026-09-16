import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { getStoredToken } from "../api/client";
import type { Telemetry } from "../api/types";

// Complementa el polling de useDeviceTelemetry (que sigue activo como red
// de respaldo, igual patrón que el poll de 3s del firmware sobre el
// comando embebido en telemetría) empujando cada lectura nueva en cuanto
// el backend la guarda, en vez de esperar al próximo intervalo de poll —
// ver app/api/app/ws.py (suscripción por device_id) y
// app/api/iot/router.py (quién la empuja).
const RECONNECT_DELAY_MS = 3000;

function buildWebSocketUrl(token: string): string {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const wsBaseUrl = apiBaseUrl.replace(/^http/, "ws");
  return `${wsBaseUrl}/api/v1/app/ws?token=${encodeURIComponent(token)}`;
}

interface TelemetryMessage {
  type: "telemetry";
  device_id: number;
  reading: Telemetry;
}

export function useLiveDeviceTelemetry(deviceId: number | undefined): void {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    if (deviceId === undefined) return undefined;
    stoppedRef.current = false;

    function connect() {
      if (stoppedRef.current) return;
      const token = getStoredToken();
      if (!token) return;

      const socket = new WebSocket(buildWebSocketUrl(token));
      socketRef.current = socket;

      socket.onopen = () => {
        socket.send(JSON.stringify({ type: "subscribe", device_id: deviceId }));
      };

      socket.onmessage = (event) => {
        let payload: TelemetryMessage;
        try {
          payload = JSON.parse(event.data);
        } catch {
          return;
        }
        if (payload.type !== "telemetry" || payload.device_id !== deviceId) return;

        queryClient.setQueryData<Telemetry[]>(["device-telemetry", deviceId], (old) => {
          const existing = old ?? [];
          if (existing.some((reading) => reading.id === payload.reading.id)) return existing;
          return [payload.reading, ...existing].slice(0, 20);
        });
      };

      socket.onclose = () => {
        if (stoppedRef.current) return;
        setTimeout(connect, RECONNECT_DELAY_MS);
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      stoppedRef.current = true;
      socketRef.current?.close();
    };
  }, [deviceId, queryClient]);
}
