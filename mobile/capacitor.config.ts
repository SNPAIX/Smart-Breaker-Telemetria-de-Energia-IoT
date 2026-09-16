import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.voltguard.app",
  appName: "VoltGuard",
  webDir: "dist",
  // El backend todavía no tiene TLS (llega en la etapa 15, reverse proxy +
  // HTTPS) — con el esquema por defecto ("https://localhost") Chromium
  // bloquea como "mixed content" cualquier fetch a un backend http://,
  // sin importar `usesCleartextTraffic` (eso solo cubre la capa de red de
  // Android, no la política de contenido mixto del propio WebView). Con
  // "http" la página también carga como http://localhost, coherente con
  // el backend.
  server: {
    androidScheme: "http",
  },
};

export default config;
