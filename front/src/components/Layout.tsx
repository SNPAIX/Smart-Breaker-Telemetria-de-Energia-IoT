import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function Layout({ children }: { children: ReactNode }) {
  const { isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div>
      <nav className="navbar">
        <span className="brand">VoltGuard</span>
        <Link to="/sites">Mis sitios</Link>
        <Link to="/notifications">Notificaciones</Link>
        {isAdmin && (
          <>
            <Link to="/admin">Dashboard admin</Link>
            <Link to="/admin/users">Usuarios</Link>
            <Link to="/admin/sites">Sitios</Link>
            <Link to="/admin/devices">Dispositivos</Link>
          </>
        )}
        <button className="link-button" onClick={handleLogout}>
          Salir
        </button>
      </nav>
      <main className="content">{children}</main>
    </div>
  );
}
