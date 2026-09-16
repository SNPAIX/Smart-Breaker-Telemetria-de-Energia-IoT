import { useCallback, useState } from "react";

import { useVoiceQuery } from "../api/hooks";
import { ensureVoicePermissions, listenOnce, speak, stopListening } from "./nativeVoice";

export type VoiceAssistantStatus = "idle" | "listening" | "thinking" | "speaking" | "error";

interface VoiceExchange {
  transcript: string;
  spokenText: string;
}

const UNAVAILABLE_MESSAGE =
  "El asistente de voz no está disponible en este momento. Probá de nuevo más tarde.";
const NO_PERMISSION_MESSAGE = "Necesito permiso del micrófono para poder escucharte.";
// Distinto de UNAVAILABLE_MESSAGE a propósito: esto es el reconocedor nativo
// devolviendo "No match" (no escuchó nada entendible — silencio, ruido,
// hablaste antes de que empezara a escuchar), no una falla del backend ni
// de la app. Antes ambos casos mostraban el mismo mensaje de "no
// disponible", lo que hacía pensar que el servidor estaba caído cuando en
// realidad el micrófono simplemente no captó nada.
const NOT_UNDERSTOOD_MESSAGE = "No te escuché bien. Intentá de nuevo.";

export function useVoiceAssistant() {
  const [status, setStatus] = useState<VoiceAssistantStatus>("idle");
  const [lastExchange, setLastExchange] = useState<VoiceExchange | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const voiceQuery = useVoiceQuery();

  // Camino compartido por voz y por texto escrito: a partir de acá los dos
  // modos son indistinguibles — mismo endpoint, misma plantilla de
  // respuesta, mismo TTS. Solo cambia cómo se obtiene el `transcript`.
  const processTranscript = useCallback(
    async (transcript: string) => {
      setStatus("thinking");
      const response = await voiceQuery.mutateAsync(transcript);

      setLastExchange({ transcript, spokenText: response.spoken_text });
      setStatus("speaking");
      await speak(response.spoken_text);
      setStatus("idle");
    },
    [voiceQuery],
  );

  const toggleListening = useCallback(async () => {
    if (status === "listening") {
      await stopListening();
      return;
    }
    if (status === "thinking" || status === "speaking") {
      return; // ya hay un ciclo en curso, ignorar toques repetidos
    }

    setErrorMessage(null);
    try {
      const granted = await ensureVoicePermissions();
      if (!granted) {
        setStatus("error");
        setErrorMessage(NO_PERMISSION_MESSAGE);
        await speak(NO_PERMISSION_MESSAGE);
        setStatus("idle");
        return;
      }

      setStatus("listening");
      let transcript: string;
      try {
        transcript = await listenOnce();
      } catch {
        // Fallo del reconocedor nativo (típicamente "No match": no captó
        // ninguna palabra) — nunca llegó a tocar el backend, así que no es
        // un problema de disponibilidad del servicio.
        setStatus("error");
        setErrorMessage(NOT_UNDERSTOOD_MESSAGE);
        await speak(NOT_UNDERSTOOD_MESSAGE);
        setStatus("idle");
        return;
      }
      await processTranscript(transcript);
    } catch {
      // Acá sí es el backend: responde 404 (VOICE_ASSISTANT_ENABLED=false en
      // ese despliegue), un error de red, o el propio TTS falló.
      setStatus("error");
      setErrorMessage(UNAVAILABLE_MESSAGE);
      await speak(UNAVAILABLE_MESSAGE);
      setStatus("idle");
    }
  }, [status, processTranscript]);

  const submitText = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || status === "listening" || status === "thinking" || status === "speaking") {
        return;
      }
      setErrorMessage(null);
      try {
        await processTranscript(trimmed);
      } catch {
        setStatus("error");
        setErrorMessage(UNAVAILABLE_MESSAGE);
        await speak(UNAVAILABLE_MESSAGE);
        setStatus("idle");
      }
    },
    [status, processTranscript],
  );

  return { status, lastExchange, errorMessage, toggleListening, submitText };
}
