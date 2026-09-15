import { isAxiosError } from "axios";
import { useState, type FormEvent } from "react";

import {
  useAdminUsers,
  useCreateAdminUser,
  useDeleteAdminUser,
  useUpdateAdminUser,
} from "../../api/hooks";
import type { AdminUser } from "../../api/types";

function extractErrorDetail(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail;
  }
  return fallback;
}

function UserRow({ user }: { user: AdminUser }) {
  const updateUser = useUpdateAdminUser();
  const deleteUser = useDeleteAdminUser();
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  const handleRoleChange = async (role: string) => {
    setRowError(null);
    try {
      await updateUser.mutateAsync({ userId: user.id, role });
    } catch (error) {
      setRowError(extractErrorDetail(error, "No se pudo actualizar el rol."));
    }
  };

  const handleToggleActive = async () => {
    setRowError(null);
    try {
      await updateUser.mutateAsync({ userId: user.id, is_active: !user.is_active });
    } catch (error) {
      setRowError(extractErrorDetail(error, "No se pudo actualizar el estado."));
    }
  };

  const handleDelete = async () => {
    setRowError(null);
    try {
      await deleteUser.mutateAsync(user.id);
    } catch (error) {
      setRowError(extractErrorDetail(error, "No se pudo eliminar el usuario."));
      setConfirmingDelete(false);
    }
  };

  return (
    <tr>
      <td>{user.id}</td>
      <td>{user.email}</td>
      <td>
        <select
          value={user.role}
          onChange={(e) => handleRoleChange(e.target.value)}
          disabled={updateUser.isPending}
        >
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
      </td>
      <td>
        <button
          type="button"
          className={user.is_active ? "icon-btn" : "icon-btn danger"}
          onClick={handleToggleActive}
          disabled={updateUser.isPending}
          title={user.is_active ? "Desactivar" : "Activar"}
        >
          {user.is_active ? "✓" : "✕"}
        </button>
      </td>
      <td>
        {confirmingDelete ? (
          <span className="confirm-inline">
            ¿Eliminar?
            <button type="button" className="icon-btn danger" onClick={handleDelete}>
              Sí
            </button>
            <button type="button" className="icon-btn" onClick={() => setConfirmingDelete(false)}>
              No
            </button>
          </span>
        ) : (
          <button
            type="button"
            className="icon-btn danger"
            title="Eliminar usuario"
            onClick={() => setConfirmingDelete(true)}
          >
            🗑
          </button>
        )}
        {rowError && <p className="error site-card-error">{rowError}</p>}
      </td>
    </tr>
  );
}

export function AdminUsersPage() {
  const { data: users, isLoading, isError } = useAdminUsers();
  const createUser = useCreateAdminUser();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    try {
      await createUser.mutateAsync({ email, password, role });
      setEmail("");
      setPassword("");
      setRole("user");
    } catch (error) {
      setFormError(extractErrorDetail(error, "No se pudo crear el usuario (¿el correo ya existe?)."));
    }
  };

  return (
    <div>
      <h1>Usuarios</h1>

      <form className="glass-card inline-form" onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="correo@ejemplo.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
        <button type="submit" className="btn-primary" disabled={createUser.isPending}>
          Crear usuario
        </button>
      </form>
      {formError && <p className="error">{formError}</p>}

      {isLoading && <p>Cargando usuarios...</p>}
      {isError && <p className="error">No se pudieron cargar los usuarios.</p>}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Correo</th>
            <th>Rol</th>
            <th>Activo</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users?.map((user) => (
            <UserRow key={user.id} user={user} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
