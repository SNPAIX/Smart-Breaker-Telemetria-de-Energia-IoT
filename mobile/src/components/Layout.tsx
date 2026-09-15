import type { ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useLiveNotifications } from "../notifications/useLiveNotifications";
import { VoiceAssistant } from "../voice/VoiceAssistant";

// Las únicas dos pantallas "raíz" (una por pestaña de la tabbar) — desde
// cualquier otra ruta (detalle de sitio, detalle de dispositivo) hace
// falta un camino de vuelta explícito, porque la tabbar solo lleva a la
// raíz de cada sección, no atrás en el historial de navegación real.
const ROOT_PATHS = ["/sites", "/notifications"];

function NavLinks() {
  return (
    <>
      <NavLink to="/sites" className={({ isActive }) => `tab${isActive ? " active" : ""}`}>
        <span className="tab-icon">🏠</span>
        <span>Sitios</span>
      </NavLink>
      <NavLink to="/notifications" className={({ isActive }) => `tab${isActive ? " active" : ""}`}>
        <span className="tab-icon">🔔</span>
        <span>Alertas</span>
      </NavLink>
    </>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  useLiveNotifications();

  const isRootScreen = ROOT_PATHS.includes(location.pathname);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div>
      <header className="topbar">
        {!isRootScreen && (
          <button
            type="button"
            className="back-btn"
            onClick={() => navigate(-1)}
            aria-label="Volver"
            title="Volver"
          >
            ←
          </button>
        )}
        <span className="brand">VoltGuard</span>
        {/* En pantallas grandes la navegación vive acá, como un sitio
            normal — la tabbar inferior (patrón de app) queda solo para
            mobile, ver el breakpoint en index.css. */}
        <div className="topbar-links">
          <NavLinks />
        </div>
        <button className="link-button" onClick={handleLogout}>
          Salir
        </button>
      </header>

      <main className="content">{children}</main>

      <nav className="tabbar">
        <NavLinks />
      </nav>

      <VoiceAssistant />
    </div>
  );
}
