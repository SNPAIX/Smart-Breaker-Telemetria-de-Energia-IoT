import { useState, type FormEvent } from "react";

import { useAdminSites, useCreateAdminSite } from "../../api/hooks";

export function AdminSitesPage() {
  const { data: sites, isLoading, isError } = useAdminSites();
  const createSite = useCreateAdminSite();

  const [name, setName] = useState("");
  const [kind, setKind] = useState("otro");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await createSite.mutateAsync({ name, kind });
    setName("");
    setKind("otro");
  };

  return (
    <div>
      <h1>Sitios</h1>

      <form className="inline-form" onSubmit={handleSubmit}>
        <input
          placeholder="Nombre del sitio"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="casa">casa</option>
          <option value="laboratorio">laboratorio</option>
          <option value="taller">taller</option>
          <option value="negocio">negocio</option>
          <option value="sucursal">sucursal</option>
          <option value="otro">otro</option>
        </select>
        <button type="submit" disabled={createSite.isPending}>
          Crear sitio
        </button>
      </form>

      {isLoading && <p>Cargando sitios...</p>}
      {isError && <p className="error">No se pudieron cargar los sitios.</p>}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Tipo</th>
          </tr>
        </thead>
        <tbody>
          {sites?.map((site) => (
            <tr key={site.id}>
              <td>{site.id}</td>
              <td>{site.name}</td>
              <td>{site.kind}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
