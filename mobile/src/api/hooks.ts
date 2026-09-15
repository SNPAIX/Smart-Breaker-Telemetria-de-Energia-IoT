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
  NotificationItem,
  Site,
  SiteCreateIn,
  Telemetry,
  VoiceQueryOut,
} from "./types";

export function useMySites() {
  return useQuery({
    queryKey: ["sites"],
    queryFn: async () => (await apiClient.get<Site[]>("/api/v1/app/sites")).data,
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

export function useCreateMyDevice(siteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: DeviceSelfCreateIn) =>
      (await apiClient.post<DeviceCreateOut>(`/api/v1/app/sites/${siteId}/devices`, payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["site-devices", siteId] }),
  });
}

export function useSiteDevices(siteId: number | undefined) {
  return useQuery({
    queryKey: ["site-devices", siteId],
    queryFn: async () =>
      (await apiClient.get<Device[]>(`/api/v1/app/sites/${siteId}/devices`)).data,
    enabled: siteId !== undefined,
  });
}

// El detalle del dispositivo se refresca solo (polling) para reflejar un
// bloqueo por CRITICAL_OVERLOAD sin que el usuario tenga que recargar —
// igual que en front/ (etapa 13). Bajado a 2s (14-sep, HIL real) por el
// mismo motivo que en front/.
const DEVICE_POLL_INTERVAL_MS = 2000;

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

export function useDeviceCost(deviceId: number | undefined) {
  return useQuery({
    queryKey: ["device-cost", deviceId],
    queryFn: async () => (await apiClient.get<DeviceCost>(`/api/v1/app/devices/${deviceId}/cost`)).data,
    enabled: deviceId !== undefined,
  });
}

export function useDeviceConsumption(
  deviceId: number | undefined,
  days: number,
  granularity: "day" | "month",
) {
  return useQuery({
    queryKey: ["device-consumption", deviceId, days, granularity],
    queryFn: async () =>
      (
        await apiClient.get<DeviceConsumption>(
          `/api/v1/app/devices/${deviceId}/consumption?days=${days}&granularity=${granularity}`,
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

export function useMyNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: async () => (await apiClient.get<NotificationItem[]>("/api/v1/app/notifications")).data,
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
