import axios from "axios";

const API_BASE_URL_OVERRIDE_KEY = "voltguard_api_base_url_override";

// Ajuste oculto solo para demos (ver pages/LoginPage.tsx): apunta la app
// ya compilada a un backend por túnel sin recompilar el APK.
export function getApiBaseUrlOverride(): string | null {
  return localStorage.getItem(API_BASE_URL_OVERRIDE_KEY);
}

export function setApiBaseUrlOverride(url: string | null): void {
  if (url) {
    localStorage.setItem(API_BASE_URL_OVERRIDE_KEY, url);
  } else {
    localStorage.removeItem(API_BASE_URL_OVERRIDE_KEY);
  }
}

// En un dispositivo/emulador real, "localhost" apunta al propio celular,
// no a la máquina de desarrollo — ver mobile/.env.example.
const baseURL =
  getApiBaseUrlOverride() ?? import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = axios.create({ baseURL });

const TOKEN_STORAGE_KEY = "voltguard_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Un 401 en /auth/login es un login fallido, no una sesión expirada
    // — redirigir ahí recarga la página antes de que el error se pinte.
    const isLoginRequest = error.config?.url?.includes("/auth/login");
    if (error.response?.status === 401 && !isLoginRequest) {
      clearStoredToken();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);
