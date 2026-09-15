import { useState, type FormEvent } from "react";

import { useVoiceAssistant } from "./useVoiceAssistant";

const STATUS_LABEL: Record<string, string> = {
  idle: "🎤",
  listening: "⏹",
  thinking: "…",
  speaking: "🔊",
  error: "🎤",
};

export function VoiceAssistant() {
  const { status, lastExchange, errorMessage, toggleListening, submitText } = useVoiceAssistant();
  const [panelOpen, setPanelOpen] = useState(false);
  const [typedText, setTypedText] = useState("");

  const busy = status === "thinking" || status === "speaking";

  const handleTextSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await submitText(typedText);
    setTypedText("");
  };

  return (
    <>
      {panelOpen && (
        <div className="voice-panel">
          {lastExchange && (
            <>
              <p className="muted">Escuché: "{lastExchange.transcript}"</p>
              <p>{lastExchange.spokenText}</p>
            </>
          )}
          {errorMessage && <p className="error">{errorMessage}</p>}

          {/* Modo de texto: mismo camino que la voz a partir de la
              transcripción — útil para probar sin micrófono (emulador,
              entornos sin audio) y como alternativa accesible real. */}
          <form className="inline-form" onSubmit={handleTextSubmit}>
            <input
              placeholder='Escribí un comando (ej. "apaga la luz de la sala")'
              value={typedText}
              onChange={(e) => setTypedText(e.target.value)}
              disabled={busy}
            />
            <button type="submit" disabled={busy || typedText.trim().length === 0}>
              Enviar
            </button>
          </form>
        </div>
      )}

      <button
        type="button"
        className="voice-fab voice-fab-secondary"
        onClick={() => setPanelOpen((open) => !open)}
        aria-label="Escribir comando"
        title="Escribir comando"
      >
        ⌨️
      </button>

      <button
        type="button"
        className={`voice-fab${status === "listening" ? " listening" : ""}`}
        onClick={toggleListening}
        disabled={busy}
        aria-label="Asistente de voz"
        title="Asistente de voz"
      >
        {STATUS_LABEL[status]}
      </button>
    </>
  );
}
