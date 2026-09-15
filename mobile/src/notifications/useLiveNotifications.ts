import { useQueryClient } from "@tanstack/react-query";
import { LocalNotifications } from "@capacitor/local-notifications";
import { useEffect, useRef } from "react";

import { getStoredToken } from "../api/client";

// "Camino B" (ver roadmap/GUIA-PUSH-NOTIFICATIONS-FCM.md): el backend
// empuja por este WebSocket mientras la app tenga una conexión abierta
// (incluso en segundo plano) — no sobrevive a que el SO mate el proceso,
// eso requeriría FCM ("Camino A"), fuera de alcance hasta tener un
// proyecto Firebase real.

const RECONNECT_DELAY_MS = 3000;

function buildWebSocketUrl(token: string): string {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const wsBaseUrl = apiBaseUrl.replace(/^http/, "ws");
  return `${wsBaseUrl}/api/v1/app/ws?token=${encodeURIComponent(token)}`;
}

interface IncomingNotification {
  type: "notification";
  title: string;
  body: string;
}

let permissionRequested = false;

async function ensureNotificationPermission(): Promise<void> {
  if (permissionRequested) return;
  permissionRequested = true;
  try {
    const status = await LocalNotifications.checkPermissions();
    if (status.display !== "granted") {
      await LocalNotifications.requestPermissions();
    }
  } catch {
    // Entorno sin plugin nativo (ej. navegador de escritorio en dev) — la
    // conexión WS sigue sirviendo para refrescar la lista in-app.
  }
}

async function showLocalNotification(payload: IncomingNotification): Promise<void> {
  try {
    await LocalNotifications.schedule({
      notifications: [
        {
          id: Date.now() % 2147483647,
          title: payload.title,
          body: payload.body,
        },
      ],
    });
  } catch {
    // Sin plugin nativo disponible — la notificación igual queda en la
    // lista in-app vía la invalidación de query de más abajo.
  }
}

// Se monta una sola vez en `Layout` (que solo renderiza dentro de rutas
// autenticadas) — mantiene la conexión viva mientras haya sesión y se
// reconecta solo mientras el token siga vigente.
export function useLiveNotifications(): void {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    stoppedRef.current = false;
    void ensureNotificationPermission();

    function connect() {
      if (stoppedRef.current) return;
      const token = getStoredToken();
      if (!token) return;

      const socket = new WebSocket(buildWebSocketUrl(token));
      socketRef.current = socket;

      socket.onmessage = (event) => {
        let payload: IncomingNotification;
        try {
          payload = JSON.parse(event.data);
        } catch {
          return;
        }
        if (payload.type !== "notification") return;

        void showLocalNotification(payload);
        queryClient.invalidateQueries({ queryKey: ["notifications"] });
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
  }, [queryClient]);
}
