import { isAxiosError } from "axios";
import toast from "react-hot-toast";

// Único punto de la app que sabe leer el `detail` real de un error de la
// API (FastAPI/axios) — antes esta misma función vivía copiada en cada
// página que hacía una mutación, cada una además con su propio <p
// className="error"> empujando el layout. Ahora centraliza extracción Y
// aviso: un solo lugar para mantener homogéneo el "cómo se ve un error"
// en toda la app.
export function extractErrorDetail(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail;
  }
  return fallback;
}

export function notifyError(error: unknown, fallback: string): void {
  toast.error(extractErrorDetail(error, fallback));
}

export function notifySuccess(message: string): void {
  toast.success(message);
}
