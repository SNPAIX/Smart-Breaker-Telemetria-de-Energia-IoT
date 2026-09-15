import { isAxiosError } from "axios";
import { useState, type FormEvent } from "react";

import { useAdminSites, useCreateAdminSite, useDeleteAdminSite, useUpdateAdminSite } from "../../api/hooks";
import type { Site } from "../../api/types";

function extractErrorDetail(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail;
  }
  return fallback;
}

function SiteRow({ site }: { site: Site }) {
  const updateSite = useUpdateAdminSite();
  const deleteSite = useDeleteAdminSite();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(site.name);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  const handleRename = async (event: FormEvent) => {
    event.preventDefault();
    if (name.trim().length === 0 || name === site.name) {
      setEditing(false);
      setName(site.name);
      return;
    }
    await updateSite.mutateAsync({ siteId: site.id, name: name.trim() });
    setEditing(false);
  };

  const handleDelete = async () => {
    setRowError(null);
    try {
      await deleteSite.mutateAsync(site.id);
    } catch (error) {
      setRowError(extractErrorDetail(error, "No se pudo eliminar el sitio."));
      setConfirmingDelete(false);
    }
  };

  return (
    <tr>
      <td>{site.id}</td>
      <td>
        {editing ? (
          <form className="site-card-rename" onSubmit={handleRename}>
            <input autoFocus value={name} onChange={(e) => setName(e.target.value)} />
            <button type="submit" className="icon-btn" title="Guardar" disabled={updateSite.isPending}>
              ✓
            </button>
          </form>
        ) : (
          site.name
        )}
      </td>
      <td>{site.kind}</td>
      <td>
        {!editing && (
          <button type="button" className="icon-btn" title="Renombrar" onClick={() => setEditing(true)}>
            ✎
          </button>
        )}
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
            title="Eliminar sitio"
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

export function AdminSitesPage() {
  const { data: sites, isLoading, isError } = useAdminSites();
  const createSite = useCreateAdminSite();

  const [name, setName] = useState("");
  const [kind, setKind] = useState("otro");
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    try {
      await createSite.mutateAsync({ name, kind });
      setName("");
      setKind("otro");
    } catch (error) {
      setFormError(extractErrorDetail(error, "No se pudo crear el sitio."));
    }
  };

  return (
    <div>
      <h1>Sitios</h1>

      <form className="glass-card inline-form" onSubmit={handleSubmit}>
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
        <button type="submit" className="btn-primary" disabled={createSite.isPending}>
          Crear sitio
        </button>
      </form>
      {formError && <p className="error">{formError}</p>}

      {isLoading && <p>Cargando sitios...</p>}
      {isError && <p className="error">No se pudieron cargar los sitios.</p>}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Tipo</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sites?.map((site) => (
            <SiteRow key={site.id} site={site} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
