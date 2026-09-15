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
  MySite,
  DeviceMetrics,
  DevicePrediction,
  DeviceState,
  AdminSite,
  NotificationItem,
  NotificationPreference,
  Site,
  SiteMember,
  Tariff,
  UserDeletionImpact,
} from "./types";

// --- Usuario final (/api/v1/app) ---

export function useMySites() {
  return useQuery({
    queryKey: ["sites"],
    queryFn: async () => (await apiClient.get<MySite[]>("/api/v1/app/sites")).data,
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

export function useLeaveMySite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (siteId: number) => {
      await apiClient.delete(`/api/v1/app/sites/${siteId}/membership`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sites"] }),
  });
}

// Refresca solo (polling) para reflejar un bloqueo por CRITICAL_OVERLOAD
// sin que el usuario tenga que recargar.
const DEVICE_POLL_INTERVAL_MS = 2000;

export function useSiteDevices(siteId: number | undefined) {
  return useQuery({
    queryKey: ["site-devices", siteId],
    queryFn: async () =>
      (await apiClient.get<Device[]>(`/api/v1/app/sites/${siteId}/devices`)).data,
    enabled: siteId !== undefined,
    // Mismo motivo que useDevice: sin esto la tarjeta se queda con el
    // estado viejo hasta que algo más dispare un refetch.
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

// Antes se pedían una sola vez al montar y quedaban congelados sin
// reflejar lecturas nuevas.
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

// La vista "hoy, por hora" se beneficia de refrescar más seguido, es la
// que el usuario mira mientras el consumo llega en vivo.
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
      // Coincidencia parcial de clave: refresca la tarjeta de este
      // dispositivo en cualquier listado de "dispositivos del sitio" que
      // esté montado, sin necesidad de saber a qué sitio pertenece.
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
    queryFn: async () =>
      (await apiClient.get<NotificationItem[]>("/api/v1/app/notifications")).data,
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

export function useUserDeletionImpact() {
  return useMutation({
    mutationFn: async (userId: number) =>
      (
        await apiClient.get<UserDeletionImpact>(`/api/v1/admin/users/${userId}/deletion-impact`)
      ).data,
  });
}

export function useDeleteAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      deleteOrphanedSites,
    }: {
      userId: number;
      deleteOrphanedSites: boolean;
    }) => {
      await apiClient.delete(
        `/api/v1/admin/users/${userId}?delete_orphaned_sites=${deleteOrphanedSites}`,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-sites"] });
    },
  });
}

export function useAdminSites() {
  return useQuery({
    queryKey: ["admin-sites"],
    queryFn: async () => (await apiClient.get<AdminSite[]>("/api/v1/admin/sites")).data,
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

export function useAdminSiteMembers(siteId: number | undefined) {
  return useQuery({
    queryKey: ["admin-site-members", siteId],
    queryFn: async () =>
      (await apiClient.get<SiteMember[]>(`/api/v1/admin/sites/${siteId}/members`)).data,
    enabled: siteId !== undefined,
  });
}

export function useAddAdminSiteMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      siteId,
      userId,
      role,
    }: {
      siteId: number;
      userId: number;
      role: string;
    }) =>
      (
        await apiClient.post<SiteMember>(`/api/v1/admin/sites/${siteId}/members`, {
          user_id: userId,
          role,
        })
      ).data,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin-site-members", variables.siteId] });
      // También refresca la lista de sitios: ahí vive la insignia
      // "vinculado (soporte)" que depende de la membresía del admin.
      queryClient.invalidateQueries({ queryKey: ["admin-sites"] });
    },
  });
}

export function useRemoveAdminSiteMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ siteId, userId }: { siteId: number; userId: number }) => {
      await apiClient.delete(`/api/v1/admin/sites/${siteId}/members/${userId}`);
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin-site-members", variables.siteId] });
      queryClient.invalidateQueries({ queryKey: ["admin-sites"] });
    },
  });
}

export function useAdminTariffs(siteId: number | undefined) {
  return useQuery({
    queryKey: ["admin-tariffs", siteId],
    queryFn: async () =>
      (await apiClient.get<Tariff[]>(`/api/v1/admin/sites/${siteId}/tariffs`)).data,
    enabled: siteId !== undefined,
  });
}

export function useCreateAdminTariff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      siteId,
      price_per_kwh,
      currency,
    }: {
      siteId: number;
      price_per_kwh: number;
      currency: string;
    }) =>
      (
        await apiClient.post<Tariff>(`/api/v1/admin/sites/${siteId}/tariffs`, {
          price_per_kwh,
          currency,
        })
      ).data,
    onSuccess: (_data, variables) =>
      queryClient.invalidateQueries({ queryKey: ["admin-tariffs", variables.siteId] }),
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
