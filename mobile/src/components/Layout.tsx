import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useLiveNotifications } from "../notifications/useLiveNotifications";
import { VoiceAssistant } from "../voice/VoiceAssistant";

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
  useLiveNotifications();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div>
      <header className="topbar">
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
