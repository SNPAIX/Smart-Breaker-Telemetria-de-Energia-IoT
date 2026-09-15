import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "./client";
import type {
  AdminEvent,
  AdminOverview,
  AdminProfile,
  AdminUser,
  Device,
  DeviceConsumption,
  DeviceCost,
  DeviceCreateOut,
  DeviceEvent,
  DeviceMetrics,
  DevicePrediction,
  DeviceState,
  NotificationItem,
  Site,
} from "./types";

// --- Usuario final (/api/v1/app) ---

export function useMySites() {
  return useQuery({
    queryKey: ["sites"],
    queryFn: async () => (await apiClient.get<Site[]>("/api/v1/app/sites")).data,
  });
}

export function useCreateMySite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; kind: string }) =>
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

export function useSiteDevices(siteId: number | undefined) {
  return useQuery({
    queryKey: ["site-devices", siteId],
    queryFn: async () =>
      (await apiClient.get<Device[]>(`/api/v1/app/sites/${siteId}/devices`)).data,
    enabled: siteId !== undefined,
  });
}

// El detalle del dispositivo se refresca solo (polling) para reflejar un
// bloqueo por CRITICAL_OVERLOAD sin que el usuario tenga que recargar.
// Bajado de 5s a 2s (14-sep, HIL real): con hardware real de por medio la
// diferencia se siente — la telemetria del dispositivo ya llega casi
// continua, la UI no deberia ser el cuello de botella visible.
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
      (
        await apiClient.get<import("./types").Telemetry[]>(
          `/api/v1/app/devices/${deviceId}/telemetry?limit=20`,
        )
      ).data,
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

export function useDeviceMetrics(deviceId: number | undefined) {
  return useQuery({
    queryKey: ["device-metrics", deviceId],
    queryFn: async () =>
      (await apiClient.get<DeviceMetrics>(`/api/v1/app/devices/${deviceId}/metrics`)).data,
    enabled: deviceId !== undefined,
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
    queryFn: async () =>
      (await apiClient.get<NotificationItem[]>("/api/v1/app/notifications")).data,
  });
}

// --- Administración (/api/v1/admin) ---

export function useAdminOverview() {
  return useQuery({
    queryKey: ["admin-overview"],
    queryFn: async () => (await apiClient.get<AdminOverview>("/api/v1/admin/dashboard/overview")).data,
    refetchInterval: 10000,
  });
}

export function useAdminUsers() {
  return useQuery({
    queryKey: ["admin-users"],
    queryFn: async () => (await apiClient.get<AdminUser[]>("/api/v1/admin/users")).data,
  });
}

export function useCreateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { email: string; password: string; role: string }) =>
      (await apiClient.post<AdminUser>("/api/v1/admin/users", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      ...payload
    }: {
      userId: number;
      role?: string;
      is_active?: boolean;
    }) => (await apiClient.patch<AdminUser>(`/api/v1/admin/users/${userId}`, payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useDeleteAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: number) => {
      await apiClient.delete(`/api/v1/admin/users/${userId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useAdminSites() {
  return useQuery({
    queryKey: ["admin-sites"],
    queryFn: async () => (await apiClient.get<Site[]>("/api/v1/admin/sites")).data,
  });
}

export function useCreateAdminSite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; kind: string }) =>
      (await apiClient.post<Site>("/api/v1/admin/sites", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-sites"] }),
  });
}

export function useUpdateAdminSite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ siteId, name }: { siteId: number; name: string }) =>
      (await apiClient.patch<Site>(`/api/v1/admin/sites/${siteId}`, { name })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-sites"] }),
  });
}

export function useDeleteAdminSite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (siteId: number) => {
      await apiClient.delete(`/api/v1/admin/sites/${siteId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-sites"] }),
  });
}

export function useAdminProfiles() {
  return useQuery({
    queryKey: ["admin-profiles"],
    queryFn: async () => (await apiClient.get<AdminProfile[]>("/api/v1/admin/profiles")).data,
  });
}

export function useCreateAdminProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      max_current_a: number;
      site_id?: number;
      min_voltage_v?: number;
      max_voltage_v?: number;
      auto_cutoff_enabled?: boolean;
    }) => (await apiClient.post<AdminProfile>("/api/v1/admin/profiles", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-profiles"] }),
  });
}

export function useUpdateAdminProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      profileId,
      ...payload
    }: {
      profileId: number;
      max_current_a?: number;
      min_voltage_v?: number | null;
      max_voltage_v?: number | null;
      auto_cutoff_enabled?: boolean;
    }) => (await apiClient.patch<AdminProfile>(`/api/v1/admin/profiles/${profileId}`, payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-profiles"] }),
  });
}

export function useDeleteAdminProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (profileId: number) => {
      await apiClient.delete(`/api/v1/admin/profiles/${profileId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-profiles"] }),
  });
}

export function useAdminDevices() {
  return useQuery({
    queryKey: ["admin-devices"],
    queryFn: async () => (await apiClient.get<Device[]>("/api/v1/admin/devices")).data,
  });
}

export function useCreateAdminDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { public_id: string; name: string; profile_id?: number; site_id?: number }) =>
      (await apiClient.post<DeviceCreateOut>("/api/v1/admin/devices", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-devices"] }),
  });
}

export function useReassignAdminDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ deviceId, siteId }: { deviceId: number; siteId: number | null }) =>
      (
        await apiClient.post<Device>(`/api/v1/admin/devices/${deviceId}/reassign`, {
          site_id: siteId,
        })
      ).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-devices"] }),
  });
}

export function useDeleteAdminDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (deviceId: number) => {
      await apiClient.delete(`/api/v1/admin/devices/${deviceId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-devices"] }),
  });
}

export function useAdminEvents() {
  return useQuery({
    queryKey: ["admin-events"],
    queryFn: async () => (await apiClient.get<AdminEvent[]>("/api/v1/admin/events")).data,
    refetchInterval: 10000,
  });
}
