// Reexporta los tipos generados desde el OpenAPI real del backend (ver
// src/api/schema.ts, generado con `npm run generate:types`) — mismo
// criterio que front/src/api/types.ts, pero solo con lo que necesita la
// app de usuario final (sin superficie administrativa).
import type { components } from "./schema";

export type Site = components["schemas"]["SiteOut"];
export type MySite = components["schemas"]["MySiteOut"];
export type Device = components["schemas"]["DeviceOut"];
// Colisión de nombres: existe `SiteCreateIn` también en admin_api (sin
// dueño automático) — ver ADR 0020 para el criterio de namespacing.
export type SiteCreateIn = components["schemas"]["app__schemas__app_api__SiteCreateIn"];
export type DeviceSelfCreateIn = components["schemas"]["DeviceSelfCreateIn"];
export type DeviceCreateOut = components["schemas"]["DeviceCreateOut"];
export type DeviceState = components["schemas"]["app__schemas__app_api__DeviceStateOut"];
export type Telemetry = components["schemas"]["TelemetryOut"];
export type DeviceEvent = components["schemas"]["EventOut"];
export type DeviceCost = components["schemas"]["DeviceCostOut"];
export type DeviceConsumption = components["schemas"]["DeviceConsumptionOut"];
export type ConsumptionPoint = components["schemas"]["ConsumptionPointOut"];
export type DevicePrediction = components["schemas"]["DevicePredictionOut"];
export type NotificationItem = components["schemas"]["NotificationOut"];
export type NotificationPreference = components["schemas"]["NotificationPreferenceOut"];
export type Token = components["schemas"]["Token"];

// Asistente de voz (etapa 14) — solo existe si el backend se desplegó con
// VOICE_ASSISTANT_ENABLED=true; si no, este endpoint responde 404 y la UI
// lo maneja como cualquier otro error de red (ver src/voice/useVoiceAssistant.ts).
export type VoiceQueryIn = components["schemas"]["VoiceQueryIn"];
export type VoiceQueryOut = components["schemas"]["VoiceQueryOut"];
