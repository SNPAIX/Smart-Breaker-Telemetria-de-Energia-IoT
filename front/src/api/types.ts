// Reexporta los tipos generados desde el OpenAPI real del backend
// (ver src/api/schema.ts, generado con `npm run generate:types` — nunca se
// escriben a mano para no duplicar lo que Pydantic ya define).
import type { components } from "./schema";

export type Site = components["schemas"]["SiteOut"];
export type Device = components["schemas"]["DeviceOut"];
// FastAPI namespaca los nombres duplicados entre módulos de schemas —
// DeviceStateOut existe tanto en app_api (con is_locked_out, la que
// devuelven /switch y /reactivate) como en iot (sin ese campo).
export type DeviceState = components["schemas"]["app__schemas__app_api__DeviceStateOut"];
export type Telemetry = components["schemas"]["TelemetryOut"];
export type DeviceEvent = components["schemas"]["EventOut"];
export type DeviceMetrics = components["schemas"]["DeviceMetricsOut"];
export type DeviceCost = components["schemas"]["DeviceCostOut"];
export type DeviceConsumption = components["schemas"]["DeviceConsumptionOut"];
export type ConsumptionPoint = components["schemas"]["ConsumptionPointOut"];
export type DevicePrediction = components["schemas"]["DevicePredictionOut"];
export type NotificationItem = components["schemas"]["NotificationOut"];

// Igual que DeviceState: UserOut existe en auth (registro) y en admin_api
// (CRUD administrativo) — se usa la de admin_api aquí.
export type AdminUser = components["schemas"]["app__schemas__admin_api__UserOut"];
export type AdminEvent = components["schemas"]["AdminEventOut"];
export type AdminProfile = components["schemas"]["ProfileOut"];
export type GlobalMetrics = components["schemas"]["GlobalMetricsOut"];
export type SiteMetrics = components["schemas"]["SiteMetricsOut"];
export type ProfileMetrics = components["schemas"]["ProfileMetricsOut"];
export type AdminOverview = components["schemas"]["AdminOverviewOut"];
export type DeviceCreateOut = components["schemas"]["DeviceCreateOut"];

export type Token = components["schemas"]["Token"];
