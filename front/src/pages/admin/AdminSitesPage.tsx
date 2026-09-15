import { useState, type FormEvent } from "react";

import {
  useAddAdminSiteMember,
  useAdminSiteMembers,
  useAdminSites,
  useAdminTariffs,
  useAdminUsers,
  useCreateAdminSite,
  useCreateAdminTariff,
  useDeleteAdminSite,
  useRemoveAdminSiteMember,
  useUpdateAdminSite,
} from "../../api/hooks";
import type { AdminSite } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { notifyError, notifySuccess } from "../../lib/errors";

function SiteMembersPanel({ siteId }: { siteId: number }) {
  const { user: currentUser } = useAuth();
  const { data: members, isLoading } = useAdminSiteMembers(siteId);
  const { data: allUsers } = useAdminUsers();
  const addMember = useAddAdminSiteMember();
  const removeMember = useRemoveAdminSiteMember();
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("member");

  const emailById = new Map(allUsers?.map((u) => [u.id, u.email]));
  const iAmAlreadyMember = members?.some((m) => m.user_id === currentUser?.id) ?? false;

  const handleAdd = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await addMember.mutateAsync({ siteId, userId: Number(userId), role });
      setUserId("");
      notifySuccess("Usuario agregado al sitio.");
    } catch (err) {
      notifyError(err, "No se pudo agregar al usuario a este sitio.");
    }
  };

  const handleRemove = async (memberUserId: number) => {
    try {
      await removeMember.mutateAsync({ siteId, userId: memberUserId });
      notifySuccess(
        memberUserId === currentUser?.id ? "Saliste del sitio." : "Miembro quitado del sitio.",
      );
    } catch (err) {
      notifyError(err, "No se pudo quitar al miembro de este sitio.");
    }
  };

  const handleJoinForSupport = async () => {
    if (!currentUser) return;
    try {
      await addMember.mutateAsync({ siteId, userId: currentUser.id, role: "member" });
      notifySuccess("Vinculado temporalmente para dar soporte — recuerda salir al terminar.");
    } catch (err) {
      notifyError(err, "No se pudo vincular al sitio.");
    }
  };

  return (
    <div>
      <h4>Miembros del sitio</h4>
      <p className="muted" style={{ marginTop: "-0.4rem" }}>
        Acceso operativo de soporte: vincularse acá es para revisar una anomalía o resolver un
        problema puntual del sitio de otra persona — al terminar, hay que salir de la lista.
      </p>

      {!iAmAlreadyMember && (
        <button
          type="button"
          className="btn-primary"
          style={{ marginBottom: "0.75rem" }}
          onClick={handleJoinForSupport}
          disabled={addMember.isPending || !currentUser}
        >
          Vincularme temporalmente para dar soporte
        </button>
      )}

      {isLoading && <p>Cargando miembros...</p>}
      <ul className="list">
        {members?.map((member) => {
          const isMe = member.user_id === currentUser?.id;
          return (
            <li key={member.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
              <span>
                {emailById.get(member.user_id) ?? `Usuario #${member.user_id}`}{" "}
                <span className="tag">{member.role}</span>
                {isMe && <span className="tag tag-danger">tú (soporte)</span>}
              </span>
              <button
                type="button"
                className="icon-btn danger"
                title={isMe ? "Salir del sitio" : "Quitar del sitio"}
                onClick={() => handleRemove(member.user_id)}
              >
                {isMe ? "🚪" : "🗑"}
              </button>
            </li>
          );
        })}
        {members && members.length === 0 && <p>Este sitio todavía no tiene miembros.</p>}
      </ul>
      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="number"
          placeholder="ID de usuario (ver pestaña Usuarios)"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          required
        />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="member">member</option>
          <option value="owner">owner</option>
        </select>
        <button type="submit" disabled={addMember.isPending}>
          Agregar otro usuario
        </button>
      </form>
    </div>
  );
}

function SiteTariffsPanel({ siteId }: { siteId: number }) {
  const { data: tariffs, isLoading } = useAdminTariffs(siteId);
  const createTariff = useCreateAdminTariff();
  const [pricePerKwh, setPricePerKwh] = useState("");
  const [currency, setCurrency] = useState("MXN");

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await createTariff.mutateAsync({
        siteId,
        price_per_kwh: Number(pricePerKwh),
        currency,
      });
      setPricePerKwh("");
      notifySuccess("Tarifa registrada.");
    } catch (err) {
      notifyError(err, "No se pudo crear la tarifa.");
    }
  };

  return (
    <div>
      <h4>Historial de tarifas (precio por kWh)</h4>
      {isLoading && <p>Cargando tarifas...</p>}
      <table>
        <thead>
          <tr>
            <th>Precio</th>
            <th>Moneda</th>
            <th>Vigente desde</th>
            <th>Vigente hasta</th>
          </tr>
        </thead>
        <tbody>
          {tariffs?.map((tariff) => (
            <tr key={tariff.id}>
              <td>{tariff.price_per_kwh}</td>
              <td>{tariff.currency}</td>
              <td>{new Date(tariff.valid_from).toLocaleDateString()}</td>
              <td>{tariff.valid_to ? new Date(tariff.valid_to).toLocaleDateString() : "vigente"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {tariffs && tariffs.length === 0 && <p>Este sitio todavía no tiene tarifas registradas.</p>}
      <form className="inline-form" onSubmit={handleCreate}>
        <input
          type="number"
          step="0.01"
          placeholder="Precio por kWh"
          value={pricePerKwh}
          onChange={(e) => setPricePerKwh(e.target.value)}
          required
        />
        <input
          placeholder="Moneda (ej. MXN)"
          value={currency}
          onChange={(e) => setCurrency(e.target.value)}
          required
        />
        <button type="submit" disabled={createTariff.isPending}>
          Registrar tarifa nueva
        </button>
      </form>
    </div>
  );
}

function SiteRow({ site }: { site: AdminSite }) {
  const updateSite = useUpdateAdminSite();
  const deleteSite = useDeleteAdminSite();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(site.name);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleRename = async (event: FormEvent) => {
    event.preventDefault();
    if (name.trim().length === 0 || name === site.name) {
      setEditing(false);
      setName(site.name);
      return;
    }
    try {
      await updateSite.mutateAsync({ siteId: site.id, name: name.trim() });
      setEditing(false);
    } catch (err) {
      notifyError(err, "No se pudo renombrar el sitio.");
    }
  };

  const handleDelete = async () => {
    try {
      await deleteSite.mutateAsync(site.id);
      notifySuccess("Sitio eliminado.");
      setConfirmingDelete(false);
    } catch (error) {
      notifyError(error, "No se pudo eliminar el sitio.");
    }
  };

  return (
    <>
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
          {site.owner_email ?? <span className="muted">Sin dueño</span>}
        </td>
        <td>
          {site.admin_is_member ? (
            <span className="tag tag-danger" title="Estás vinculado a este sitio para dar soporte">
              🛠 vinculado
            </span>
          ) : (
            <span className="muted">—</span>
          )}
        </td>
        <td>
          <button
            type="button"
            className="icon-btn"
            title="Miembros y tarifas"
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "▲" : "👥"}
          </button>
          {!editing && (
            <button type="button" className="icon-btn" title="Renombrar" onClick={() => setEditing(true)}>
              ✎
            </button>
          )}
          <button
            type="button"
            className="icon-btn danger"
            title="Eliminar sitio"
            onClick={() => setConfirmingDelete(true)}
          >
            🗑
          </button>
          <ConfirmDialog
            open={confirmingDelete}
            onOpenChange={setConfirmingDelete}
            title={`¿Eliminar el sitio "${site.name}"?`}
            confirmLabel="Eliminar"
            confirmPending={deleteSite.isPending}
            onConfirm={handleDelete}
          />
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={6}>
            <div className="glass-card" style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 280px" }}>
                <SiteMembersPanel siteId={site.id} />
              </div>
              <div style={{ flex: "1 1 320px" }}>
                <SiteTariffsPanel siteId={site.id} />
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export function AdminSitesPage() {
  const { data: sites, isLoading, isError } = useAdminSites();
  const createSite = useCreateAdminSite();

  const [name, setName] = useState("");
  const [kind, setKind] = useState("otro");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await createSite.mutateAsync({ name, kind });
      setName("");
      setKind("otro");
      notifySuccess("Sitio creado.");
    } catch (error) {
      notifyError(error, "No se pudo crear el sitio.");
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

      {isLoading && <p>Cargando sitios...</p>}
      {isError && <p className="error">No se pudieron cargar los sitios.</p>}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Tipo</th>
            <th>Dueño</th>
            <th>Soporte</th>
            <th>Acciones</th>
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
