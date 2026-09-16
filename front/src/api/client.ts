import axios from "axios";

// En desarrollo, Vite corre en un puerto distinto al backend — se
// configura vía variable de entorno para no hardcodear localhost:8000 en
// el bundle de producción (ver etapa 15, reverse proxy).
const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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
