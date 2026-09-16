import { useState, type FormEvent } from "react";

import {
  useAdminUsers,
  useCreateAdminUser,
  useDeleteAdminUser,
  useUpdateAdminUser,
  useUserDeletionImpact,
} from "../../api/hooks";
import type { AdminUser } from "../../api/types";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { notifyError, notifySuccess } from "../../lib/errors";

function UserRow({ user }: { user: AdminUser }) {
  const updateUser = useUpdateAdminUser();
  const deleteUser = useDeleteAdminUser();
  const previewDeletion = useUserDeletionImpact();
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [orphanedSites, setOrphanedSites] = useState<{ id: number; name: string; device_count: number }[]>([]);
  const [deleteOrphanedSites, setDeleteOrphanedSites] = useState(false);

  const handleRoleChange = async (role: string) => {
    try {
      await updateUser.mutateAsync({ userId: user.id, role });
    } catch (error) {
      notifyError(error, "No se pudo actualizar el rol.");
    }
  };

  const handleToggleActive = async () => {
    try {
      await updateUser.mutateAsync({ userId: user.id, is_active: !user.is_active });
    } catch (error) {
      notifyError(error, "No se pudo actualizar el estado.");
    }
  };

  const startDeleteFlow = async () => {
    try {
      const impact = await previewDeletion.mutateAsync(user.id);
      setOrphanedSites(impact.orphaned_sites);
      setDeleteOrphanedSites(false);
      setConfirmingDelete(true);
    } catch (error) {
      notifyError(error, "No se pudo revisar el impacto de eliminar este usuario.");
    }
  };

  const handleDelete = async () => {
    try {
      await deleteUser.mutateAsync({ userId: user.id, deleteOrphanedSites });
      notifySuccess(
        deleteOrphanedSites && orphanedSites.length > 0
          ? "Usuario y sitios huérfanos eliminados."
          : "Usuario eliminado.",
      );
      setConfirmingDelete(false);
    } catch (error) {
      notifyError(error, "No se pudo eliminar el usuario.");
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
        <button
          type="button"
          className="icon-btn danger"
          title="Eliminar usuario"
          onClick={startDeleteFlow}
          disabled={previewDeletion.isPending}
        >
          🗑
        </button>

        <ConfirmDialog
          open={confirmingDelete}
          onOpenChange={setConfirmingDelete}
          title={`¿Eliminar a ${user.email}?`}
          confirmLabel="Eliminar"
          confirmPending={deleteUser.isPending}
          onConfirm={handleDelete}
        >
          {orphanedSites.length > 0 && (
            <>
              <p className="error" style={{ marginTop: 0 }}>
                Este usuario es el único dueño de {orphanedSites.length}{" "}
                {orphanedSites.length === 1 ? "sitio" : "sitios"} — al borrarlo,{" "}
                {orphanedSites.length === 1 ? "ese sitio quedará" : "esos sitios quedarán"} sin
                dueño:
              </p>
              <ul>
                {orphanedSites.map((site) => (
                  <li key={site.id}>
                    {site.name} — {site.device_count}{" "}
                    {site.device_count === 1 ? "dispositivo" : "dispositivos"}
                  </li>
                ))}
              </ul>
              <label className="inline-checkbox" style={{ display: "flex", marginBottom: "0.6rem" }}>
                <input
                  type="checkbox"
                  checked={deleteOrphanedSites}
                  onChange={(e) => setDeleteOrphanedSites(e.target.checked)}
                />
                Borrar también {orphanedSites.length === 1 ? "ese sitio" : "esos sitios"}
              </label>
              {deleteOrphanedSites && (
                <p className="error" style={{ fontSize: "0.8rem" }}>
                  Esto es irreversible. Los dispositivos de{" "}
                  {orphanedSites.length === 1 ? "ese sitio" : "esos sitios"} quedarán sin sitio —
                  alguien va a tener que volver a vincularlos a uno.
                </p>
              )}
            </>
          )}
        </ConfirmDialog>
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

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await createUser.mutateAsync({ email, password, role });
      setEmail("");
      setPassword("");
      setRole("user");
      notifySuccess("Usuario creado.");
    } catch (error) {
      notifyError(error, "No se pudo crear el usuario (¿el correo ya existe?).");
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

      {isLoading && <p>Cargando usuarios...</p>}
      {isError && <p className="error">No se pudieron cargar los usuarios.</p>}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Correo</th>
            <th>Rol</th>
            <th>Activo</th>
            <th>Acciones</th>
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
