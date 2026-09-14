import { useState, type FormEvent } from "react";

import { useAdminUsers, useCreateAdminUser } from "../../api/hooks";

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
    } catch {
      setFormError("No se pudo crear el usuario (¿el correo ya existe?).");
    }
  };

  return (
    <div>
      <h1>Usuarios</h1>

      <form className="inline-form" onSubmit={handleSubmit}>
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
        <button type="submit" disabled={createUser.isPending}>
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
          </tr>
        </thead>
        <tbody>
          {users?.map((user) => (
            <tr key={user.id}>
              <td>{user.id}</td>
              <td>{user.email}</td>
              <td>{user.role}</td>
              <td>{user.is_active ? "sí" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
