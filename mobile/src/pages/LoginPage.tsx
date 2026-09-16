import { useRef, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { getApiBaseUrlOverride, setApiBaseUrlOverride } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { notifyError, notifySuccess } from "../lib/errors";

const UNLOCK_TAPS = 5;
const UNLOCK_WINDOW_MS = 2000;

function DemoServerPanel() {
  const [url, setUrl] = useState(getApiBaseUrlOverride() ?? "");

  const handleSave = (event: FormEvent) => {
    event.preventDefault();
    setApiBaseUrlOverride(url.trim() || null);
    notifySuccess(url.trim() ? "Servidor de demo guardado. Recargando..." : "Servidor restablecido. Recargando...");
    setTimeout(() => window.location.reload(), 600);
  };

  return (
    <form
      className="card"
      onSubmit={handleSave}
      style={{ marginTop: "0.75rem", borderStyle: "dashed" }}
    >
      <h2 style={{ marginTop: 0 }}>Servidor de demo</h2>
      <p className="muted" style={{ marginTop: "-0.4rem" }}>
        Ajuste temporal, solo para pruebas fuera de la red local (ej. un túnel). Se guarda
        únicamente en este dispositivo.
      </p>
      <label>
        URL del backend
        <input
          placeholder="https://tu-tunel.trycloudflare.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
      </label>
      <div className="button-row">
        <button type="submit">Guardar y recargar</button>
        {getApiBaseUrlOverride() && (
          <button
            type="button"
            onClick={() => {
              setApiBaseUrlOverride(null);
              window.location.reload();
            }}
          >
            Quitar
          </button>
        )}
      </div>
    </form>
  );
}

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [demoPanelOpen, setDemoPanelOpen] = useState(false);
  const tapCount = useRef(0);
  const tapTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  if (isAuthenticated) {
    return <Navigate to="/sites" replace />;
  }

  const handleTitleTap = () => {
    tapCount.current += 1;
    if (tapTimer.current) clearTimeout(tapTimer.current);
    tapTimer.current = setTimeout(() => {
      tapCount.current = 0;
    }, UNLOCK_WINDOW_MS);

    if (tapCount.current >= UNLOCK_TAPS) {
      tapCount.current = 0;
      setDemoPanelOpen((open) => !open);
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/sites");
    } catch {
      notifyError(null, "Correo o contraseña incorrectos.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="centered-page">
      <div>
        <form className="card" onSubmit={handleSubmit}>
          <h1 onClick={handleTitleTap} style={{ cursor: "default" }}>
            VoltGuard
          </h1>
          <label>
            Correo
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Ingresando..." : "Ingresar"}
          </button>
        </form>
        {demoPanelOpen && <DemoServerPanel />}
      </div>
    </div>
  );
}
