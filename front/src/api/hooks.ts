import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "./client";
import type {
  AdminEvent,
  AdminOverview,
  AdminProfile,
  AdminUser,
  Device,
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
const DEVICE_POLL_INTERVAL_MS = 5000;

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

export function useDeviceCost(deviceId: number | undefined) {
  return useQuery({
    queryKey: ["device-cost", deviceId],
    queryFn: async () => (await apiClient.get<DeviceCost>(`/api/v1/app/devices/${deviceId}/cost`)).data,
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

export function useAdminProfiles() {
  return useQuery({
    queryKey: ["admin-profiles"],
    queryFn: async () => (await apiClient.get<AdminProfile[]>("/api/v1/admin/profiles")).data,
  });
}

export function useCreateAdminProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; max_current_a: number; site_id?: number }) =>
      (await apiClient.post<AdminProfile>("/api/v1/admin/profiles", payload)).data,
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

export function useAdminEvents() {
  return useQuery({
    queryKey: ["admin-events"],
    queryFn: async () => (await apiClient.get<AdminEvent[]>("/api/v1/admin/events")).data,
    refetchInterval: 10000,
  });
}
