// Puente delgado hacia los plugins nativos de voz. Ambos declaran también
// una implementación web (ver node_modules/@capacitor-community/*/dist/esm/web.*),
// así que el mismo código corre sin cambios en `npm run dev` (navegador,
// usando SpeechRecognition/speechSynthesis del propio browser) y en la app
// Android real empaquetada con Capacitor (usando el reconocedor y el TTS
// nativos del sistema) — no hay una rama de código separada para "modo
// desarrollo" vs "modo nativo".
import { SpeechRecognition } from "@capacitor-community/speech-recognition";
import { TextToSpeech } from "@capacitor-community/text-to-speech";

const RECOGNITION_LANGUAGE = "es-ES";

export async function ensureVoicePermissions(): Promise<boolean> {
  const status = await SpeechRecognition.checkPermissions();
  if (status.speechRecognition === "granted") return true;

  const requested = await SpeechRecognition.requestPermissions();
  return requested.speechRecognition === "granted";
}

export async function listenOnce(): Promise<string> {
  const result = await SpeechRecognition.start({
    language: RECOGNITION_LANGUAGE,
    maxResults: 1,
    partialResults: false,
    popup: false,
  });
  const transcript = result.matches?.[0];
  if (!transcript) {
    throw new Error("No se entendió nada — no llegó ninguna transcripción.");
  }
  return transcript;
}

export async function stopListening(): Promise<void> {
  await SpeechRecognition.stop();
}

export async function speak(text: string): Promise<void> {
  await TextToSpeech.speak({
    text,
    lang: RECOGNITION_LANGUAGE,
    rate: 1.0,
    pitch: 1.0,
    volume: 1.0,
  });
}
