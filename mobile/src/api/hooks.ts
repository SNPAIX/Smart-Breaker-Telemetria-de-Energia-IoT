import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "./client";
import type {
  Device,
  DeviceConsumption,
  DeviceCost,
  DeviceCreateOut,
  DeviceEvent,
  DevicePrediction,
  DeviceSelfCreateIn,
  DeviceState,
  MySite,
  NotificationItem,
  NotificationPreference,
  Site,
  SiteCreateIn,
  Telemetry,
  VoiceQueryOut,
} from "./types";

export function useMySites() {
  return useQuery({
    queryKey: ["sites"],
    queryFn: async () => (await apiClient.get<MySite[]>("/api/v1/app/sites")).data,
  });
}

export function useLeaveMySite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (siteId: number) => {
      await apiClient.delete(`/api/v1/app/sites/${siteId}/membership`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sites"] }),
  });
}

export function useCreateMySite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SiteCreateIn) =>
      (await apiClient.post<Site>("/api/v1/app/sites", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sites"] }),
  });
}

export function useRenameMySite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ siteId, name }: { siteId: number; name: string }) =>
      (await apiClient.patch<Site>(`/api/v1/app/sites/${siteId}`, { name })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sites"] }),
  });
}

export function useDeleteMySite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (siteId: number) => {
      await apiClient.delete(`/api/v1/app/sites/${siteId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sites"] }),
  });
}

export function useCreateMyDevice(siteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: DeviceSelfCreateIn) =>
      (await apiClient.post<DeviceCreateOut>(`/api/v1/app/sites/${siteId}/devices`, payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["site-devices", siteId] }),
  });
}

// El detalle del dispositivo se refresca solo (polling) para reflejar un
// bloqueo por CRITICAL_OVERLOAD sin que el usuario tenga que recargar —
// igual que en front/ (etapa 13). Bajado a 2s (14-sep, HIL real) por el
// mismo motivo que en front/.
const DEVICE_POLL_INTERVAL_MS = 2000;

export function useSiteDevices(siteId: number | undefined) {
  return useQuery({
    queryKey: ["site-devices", siteId],
    queryFn: async () =>
      (await apiClient.get<Device[]>(`/api/v1/app/sites/${siteId}/devices`)).data,
    enabled: siteId !== undefined,
    // Mismo motivo que useDevice: sin esto, la tarjeta se queda con el
    // estado viejo hasta que algo más dispare un refetch, aunque el
    // dispositivo real ya haya confirmado el cambio.
    refetchInterval: DEVICE_POLL_INTERVAL_MS,
  });
}

export function useDevice(deviceId: number | undefined) {
  return useQuery({
    queryKey: ["device", deviceId],
    queryFn: async () => (await apiClient.get<Device>(`/api/v1/app/devices/${deviceId}`)).data,
    enabled: deviceId !== undefined,
    refetchInterval: DEVICE_POLL_INTERVAL_MS,
  });
}

export function useDeviceTelemetry(deviceId: number | undefined) {
  return useQuery({
    queryKey: ["device-telemetry", deviceId],
    queryFn: async () =>
      (await apiClient.get<Telemetry[]>(`/api/v1/app/devices/${deviceId}/telemetry?limit=20`)).data,
    enabled: deviceId !== undefined,
    refetchInterval: DEVICE_POLL_INTERVAL_MS,
  });
}

export function useDeviceEvents(deviceId: number | undefined) {
  return useQuery({
    queryKey: ["device-events", deviceId],
    queryFn: async () =>
      (await apiClient.get<DeviceEvent[]>(`/api/v1/app/devices/${deviceId}/events`)).data,
    enabled: deviceId !== undefined,
    refetchInterval: DEVICE_POLL_INTERVAL_MS,
  });
}

// Costo/predicción no necesitan actualizarse al segundo, pero sí deben
// reflejar lecturas nuevas sin que el usuario tenga que recargar — antes
// se pedían una sola vez al montar la página y se quedaban congeladas
// (bug reportado: "no veo movimiento" en Costo/Predicción mientras el
// consumo sí se actualizaba).
const COST_POLL_INTERVAL_MS = 15000;

export function useDeviceCost(deviceId: number | undefined) {
  return useQuery({
    queryKey: ["device-cost", deviceId],
    queryFn: async () => (await apiClient.get<DeviceCost>(`/api/v1/app/devices/${deviceId}/cost`)).data,
    enabled: deviceId !== undefined,
    refetchInterval: COST_POLL_INTERVAL_MS,
  });
}

export interface ConsumptionRangeParams {
  granularity: "hour" | "day" | "month";
  // Rango preestablecido (últimos N días) o personalizado (start/end,
  // "YYYY-MM-DD") — se manda uno u otro, nunca los dos (ver ConsumptionChart).
  days?: number;
  start?: string;
  end?: string;
}

// Consumo/costo no necesitan la frescura de la telemetria/estado (por eso
// no van por el WebSocket de notificaciones, que es para eventos puntuales,
// no para un agregado que cambia con cada lectura) pero sí deben reflejar
// lecturas nuevas sin que el usuario tenga que recargar la pantalla. La
// vista "hoy, por hora" sí se beneficia de refrescar más seguido — es la
// que el usuario mira mientras el consumo va llegando en vivo.
const CONSUMPTION_POLL_INTERVAL_MS = 15000;
const HOURLY_CONSUMPTION_POLL_INTERVAL_MS = 5000;

export function useDeviceConsumption(
  deviceId: number | undefined,
  { days, granularity, start, end }: ConsumptionRangeParams,
) {
  const query = new URLSearchParams({ granularity });
  if (start && end) {
    query.set("start", start);
    query.set("end", end);
  } else {
    query.set("days", String(days ?? 30));
  }
  return useQuery({
    queryKey: ["device-consumption", deviceId, granularity, days, start, end],
    refetchInterval:
      granularity === "hour" ? HOURLY_CONSUMPTION_POLL_INTERVAL_MS : CONSUMPTION_POLL_INTERVAL_MS,
    queryFn: async () =>
      (
        await apiClient.get<DeviceConsumption>(
          `/api/v1/app/devices/${deviceId}/consumption?${query.toString()}`,
        )
      ).data,
    enabled: deviceId !== undefined,
  });
}

export function useDevicePrediction(deviceId: number | undefined) {
  return useQuery({
    queryKey: ["device-prediction", deviceId],
    queryFn: async () =>
      (await apiClient.get<DevicePrediction>(`/api/v1/app/devices/${deviceId}/prediction`)).data,
    enabled: deviceId !== undefined,
  });
}

export function useSwitchDevice(deviceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (desiredState: "ON" | "OFF") =>
      (
        await apiClient.post<DeviceState>(`/api/v1/app/devices/${deviceId}/switch`, {
          desired_state: desiredState,
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["device", deviceId] });
      queryClient.invalidateQueries({ queryKey: ["site-devices"] });
    },
  });
}

export function useReactivateDevice(deviceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await apiClient.post<DeviceState>(`/api/v1/app/devices/${deviceId}/reactivate`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["device", deviceId] });
      queryClient.invalidateQueries({ queryKey: ["device-events", deviceId] });
    },
  });
}

export function useClaimDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { public_id: string; site_id: number }) =>
      (await apiClient.post<Device>("/api/v1/app/devices/claim", payload)).data,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["site-devices", variables.site_id] });
    },
  });
}

export function useUnlinkDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ deviceId }: { deviceId: number; siteId: number }) =>
      (await apiClient.post<Device>(`/api/v1/app/devices/${deviceId}/unlink`)).data,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["site-devices", variables.siteId] });
    },
  });
}

export function useMyNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: async () => (await apiClient.get<NotificationItem[]>("/api/v1/app/notifications")).data,
  });
}

export function useNotificationPreferences() {
  return useQuery({
    queryKey: ["notification-preferences"],
    queryFn: async () =>
      (
        await apiClient.get<NotificationPreference[]>("/api/v1/app/notifications/preferences")
      ).data,
  });
}

export function useSetNotificationPreference() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { channel: string; enabled: boolean }) =>
      (
        await apiClient.patch<NotificationPreference>(
          "/api/v1/app/notifications/preferences",
          payload,
        )
      ).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notification-preferences"] }),
  });
}

// --- Asistente de voz (etapa 14) ---

export function useVoiceQuery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (text: string) =>
      (await apiClient.post<VoiceQueryOut>("/api/v1/app/voice/query", { text })).data,
    onSuccess: (data) => {
      // Una acción de voz puede haber encendido/apagado un dispositivo real
      // — se invalida su cache para que la UI (si está en esa pantalla) lo
      // refleje sin esperar al próximo polling.
      if (data.device_id !== null) {
        queryClient.invalidateQueries({ queryKey: ["device", data.device_id] });
      }
    },
  });
}
