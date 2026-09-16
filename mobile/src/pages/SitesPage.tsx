import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import {
  useCreateMySite,
  useDeleteMySite,
  useLeaveMySite,
  useMySites,
  useRenameMySite,
} from "../api/hooks";
import type { MySite } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { notifyError, notifySuccess } from "../lib/errors";

function OwnershipChip({ isSupportAccess, site }: { isSupportAccess: boolean; site: MySite }) {
  if (site.my_role === "owner") {
    return <span className="tag">Dueño</span>;
  }
  if (isSupportAccess) {
    return <span className="tag tag-danger">Soporte temporal</span>;
  }
  return (
    <span className="tag" title={site.owner_email ?? undefined}>
      Invitado{site.owner_email ? ` de ${site.owner_email}` : ""}
    </span>
  );
}

function SiteCard({ site }: { site: MySite }) {
  const { user } = useAuth();
  const renameSite = useRenameMySite();
  const deleteSite = useDeleteMySite();
  const leaveSite = useLeaveMySite();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(site.name);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const isSupportAccess = user?.role === "admin" && site.my_role !== "owner";

  const handleLeave = async () => {
    try {
      await leaveSite.mutateAsync(site.id);
      notifySuccess("Te desvinculaste de este sitio.");
    } catch (error) {
      notifyError(error, "No se pudo desvincular.");
    }
  };

  const handleRename = async (event: FormEvent) => {
    event.preventDefault();
    if (name.trim().length === 0 || name === site.name) {
      setEditing(false);
      setName(site.name);
      return;
    }
    try {
      await renameSite.mutateAsync({ siteId: site.id, name: name.trim() });
      setEditing(false);
    } catch (error) {
      notifyError(error, "No se pudo renombrar el sitio.");
    }
  };

  const handleDelete = async () => {
    try {
      await deleteSite.mutateAsync(site.id);
      notifySuccess("Sitio eliminado.");
    } catch (error) {
      notifyError(error, "No se pudo eliminar el sitio.");
      setConfirmingDelete(false);
    }
  };

  return (
    <li className="card site-card">
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
          <span className="site-card-text">
            <span className="site-card-name">{site.name}</span>
            <span style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
              <span className="tag">{site.kind}</span>
              <OwnershipChip site={site} isSupportAccess={isSupportAccess} />
            </span>
          </span>
        </Link>
      )}

      <div className="site-card-actions">
        {isSupportAccess && (
          <button
            type="button"
            className="icon-btn danger"
            title="Desvincularme (soporte temporal)"
            onClick={handleLeave}
            disabled={leaveSite.isPending}
          >
            🚪
          </button>
        )}
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
    </li>
  );
}

export function SitesPage() {
  const { data: sites, isLoading, isError } = useMySites();
  const createSite = useCreateMySite();
  const [name, setName] = useState("");
  const [kind, setKind] = useState("casa");

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await createSite.mutateAsync({ name, kind });
      setName("");
      notifySuccess("Sitio creado.");
    } catch (err) {
      notifyError(err, "No se pudo crear el sitio.");
    }
  };

  return (
    <div>
      <h1>Mis sitios</h1>

      <form className="card inline-form" onSubmit={handleCreate}>
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
        <button type="submit" disabled={createSite.isPending}>
          {createSite.isPending ? "Creando..." : "Crear sitio"}
        </button>
      </form>

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
