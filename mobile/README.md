# mobile/ — Aplicación móvil de usuario final

Capacitor empaquetando una UI web (React + Vite + TypeScript, mismo patrón
de `front/` pero solo con las vistas de usuario final — sin superficie
administrativa) para Android, más un asistente de voz que usa el
reconocimiento de voz y la síntesis de voz **nativos del sistema**.

La app **no** se comunica directamente con PostgreSQL ni con el ESP32.
Toda operación pasa por `backend-server` vía `/api/v1/app/...`, incluyendo
`/api/v1/app/voice/query` (etapa 14, ver `IA-Assistant/`).

## Asistente de voz

- **Modo texto**: el botón ⌨️ (junto al micrófono) abre un campo para escribir el comando en vez de hablarlo — mismo camino que la voz a partir de la transcripción (mismo endpoint, misma plantilla de respuesta, mismo TTS). Pensado para probar sin micrófono (emulador, CI) y como alternativa accesible real, no solo como atajo de desarrollo.
- **Reconocimiento de voz**: `@capacitor-community/speech-recognition`
  (nativo: `SpeechRecognizer` en Android). El audio se procesa en el
  dispositivo/por el servicio de voz del sistema — la app nunca sube audio,
  solo el texto ya transcrito.
- **Síntesis de voz**: `@capacitor-community/text-to-speech` (nativo:
  `TextToSpeech` de Android).
- **Interpretación del comando**: ocurre enteramente en el backend
  (`IA-Assistant/`, etapa 14) — el celular solo manda el texto transcrito a
  `/api/v1/app/voice/query` y reproduce por voz el `spoken_text` que
  responde, que siempre está armado a partir del resultado real de la
  acción (nunca un "listo" genérico).
- Ambos plugins incluyen una implementación web además de la nativa, así
  que el flujo completo (mic → texto → backend real → voz) también corre
  en `npm run dev` dentro de un navegador de escritorio con soporte de
  Web Speech API (Chrome), sin necesidad de compilar la app Android para
  probar la lógica.

## Estado de validación (mismo criterio de dos niveles usado en `ino/`)

- **PASS software**: `npm run build` compila sin errores de TypeScript,
  `oxlint` limpio, `npx cap add android` generó el proyecto nativo con los
  manifiestos de ambos plugins fusionados correctamente.
- **PASS físico — completo, validado dos veces**:
  - **Celular real** (Moto G75 5G, por USB + WiFi/LAN): login, crear
    sitio/dispositivo propio, switch ON/OFF, permiso nativo de micrófono,
    reconocedor de voz nativo entrando en estado de escucha real, TTS
    nativo hablando la respuesta.
  - **Emulador** (`R:\virtual-devices\VoltGuard_Test.avd`, Pixel 6 /
    Android 14 x86_64, AVD_HOME apuntado a esa carpeta): mismo flujo
    completo probado por **modo texto** (sin micrófono disponible en el
    emulador) conectando por Chrome DevTools Protocol — login real,
    navegación, y un comando de texto real ("apaga la luz de la sala")
    ejecutando la acción real sobre el dispositivo y devolviendo la
    respuesta grounded ("Listo, apagué Luz Sala.").
  - Cuatro bugs reales encontrados y corregidos en el camino (CORS
    faltante, cleartext HTTP bloqueado por Android, mixed content por el
    esquema `https://localhost` de Capacitor, y Docker Desktop
    cayéndose bajo la carga combinada de emulador + build) — detalle en
    `roadmap/PROGRESS.md`.

## Desarrollo (navegador, sin Android)

```bash
npm install
cp .env.example .env.local   # ajustar VITE_API_BASE_URL
npm run dev
```

## Build y sincronización con Android

```bash
npm run cap:sync   # build web + npx cap sync
npx cap open android   # abre Android Studio
```

Al correr en un emulador o dispositivo físico, `localhost` en
`VITE_API_BASE_URL` apunta al propio celular, no a la máquina de
desarrollo — usar la IP de red de la máquina que corre `backend-server`
(o `10.0.2.2` para el emulador de Android Studio).

## Tipos generados desde el backend

Igual que `front/`:

```bash
npm run generate:types
```
