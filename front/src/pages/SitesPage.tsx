import { isAxiosError } from "axios";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { useCreateMySite, useDeleteMySite, useMySites, useRenameMySite } from "../api/hooks";
import type { Site } from "../api/types";

function extractErrorDetail(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail;
  }
  return fallback;
}

function SiteCard({ site }: { site: Site }) {
  const renameSite = useRenameMySite();
  const deleteSite = useDeleteMySite();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(site.name);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleRename = async (event: FormEvent) => {
    event.preventDefault();
    if (name.trim().length === 0 || name === site.name) {
      setEditing(false);
      setName(site.name);
      return;
    }
    await renameSite.mutateAsync({ siteId: site.id, name: name.trim() });
    setEditing(false);
  };

  const handleDelete = async () => {
    setErrorMessage(null);
    try {
      await deleteSite.mutateAsync(site.id);
    } catch (error) {
      setErrorMessage(extractErrorDetail(error, "No se pudo eliminar el sitio."));
      setConfirmingDelete(false);
    }
  };

  return (
    <li className="glass-card site-card">
      {editing ? (
        <form className="site-card-rename" onSubmit={handleRename}>
          <input
            autoFocus
            value={name}
            onChange={(event) => setName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                setEditing(false);
                setName(site.name);
              }
            }}
          />
          <button type="submit" className="icon-btn" title="Guardar" disabled={renameSite.isPending}>
            ✓
          </button>
        </form>
      ) : (
        <Link to={`/sites/${site.id}`} className="site-card-link">
          <span className="site-card-icon" aria-hidden="true">
            🏠
          </span>
          <span className="site-card-name">{site.name}</span>
          <span className="tag">{site.kind}</span>
        </Link>
      )}

      <div className="site-card-actions">
        {!editing && (
          <button
            type="button"
            className="icon-btn"
            title="Renombrar"
            onClick={() => setEditing(true)}
          >
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
      </div>
      {errorMessage && <p className="error site-card-error">{errorMessage}</p>}
    </li>
  );
}

export function SitesPage() {
  const { data: sites, isLoading, isError } = useMySites();
  const createSite = useCreateMySite();
  const [name, setName] = useState("");
  const [kind, setKind] = useState("casa");
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await createSite.mutateAsync({ name, kind });
      setName("");
    } catch (err) {
      setError(extractErrorDetail(err, "No se pudo crear el sitio."));
    }
  };

  return (
    <div>
      <h1>Mis sitios</h1>

      <form className="glass-card inline-form" onSubmit={handleCreate}>
        <input
          placeholder="Nombre del sitio (ej. Mi casa)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="casa">Casa</option>
          <option value="taller">Taller</option>
          <option value="oficina">Oficina</option>
          <option value="otro">Otro</option>
        </select>
        <button type="submit" className="btn-primary" disabled={createSite.isPending}>
          {createSite.isPending ? "Creando..." : "Crear sitio"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}

      {isLoading && <p>Cargando sitios...</p>}
      {isError && <p className="error">No se pudieron cargar los sitios.</p>}
      {sites && sites.length === 0 && <p>Todavía no hay ningún sitio — crea uno arriba.</p>}

      <ul className="list site-list">
        {sites?.map((site) => (
          <SiteCard key={site.id} site={site} />
        ))}
      </ul>
    </div>
  );
}
