import { useState, type FormEvent } from "react";

import {
  useAdminDevices,
  useAdminProfiles,
  useAdminSites,
  useCreateAdminDevice,
  useCreateAdminProfile,
  useDeleteAdminDevice,
  useDeleteAdminProfile,
  useReassignAdminDevice,
  useUpdateAdminProfile,
} from "../../api/hooks";
import type { AdminProfile, DeviceCreateOut } from "../../api/types";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { notifyError, notifySuccess } from "../../lib/errors";

function ProfileRow({ profile }: { profile: AdminProfile }) {
  const updateProfile = useUpdateAdminProfile();
  const deleteProfile = useDeleteAdminProfile();
  const [editing, setEditing] = useState(false);
  const [maxCurrentA, setMaxCurrentA] = useState(String(profile.max_current_a));
  const [minVoltageV, setMinVoltageV] = useState(profile.min_voltage_v?.toString() ?? "");
  const [maxVoltageV, setMaxVoltageV] = useState(profile.max_voltage_v?.toString() ?? "");
  const [autoCutoffEnabled, setAutoCutoffEnabled] = useState(profile.auto_cutoff_enabled);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await updateProfile.mutateAsync({
        profileId: profile.id,
        max_current_a: Number(maxCurrentA),
        min_voltage_v: minVoltageV ? Number(minVoltageV) : null,
        max_voltage_v: maxVoltageV ? Number(maxVoltageV) : null,
        auto_cutoff_enabled: autoCutoffEnabled,
      });
      setEditing(false);
      notifySuccess("Perfil actualizado.");
    } catch (error) {
      notifyError(error, "No se pudo actualizar el perfil.");
    }
  };

  const handleDelete = async () => {
    try {
      await deleteProfile.mutateAsync(profile.id);
      notifySuccess("Perfil eliminado.");
      setConfirmingDelete(false);
    } catch (error) {
      notifyError(error, "No se pudo eliminar el perfil.");
    }
  };

  if (editing) {
    return (
      <tr>
        <td colSpan={6}>
          <form className="profile-edit-row" onSubmit={handleSave}>
            <strong>{profile.name}</strong>
            <label>
              Corriente máx. (A)
              <input
                type="number"
                step="0.1"
                value={maxCurrentA}
                onChange={(e) => setMaxCurrentA(e.target.value)}
                required
              />
            </label>
            <label>
              Voltaje mín.
              <input
                type="number"
                step="0.1"
                value={minVoltageV}
                onChange={(e) => setMinVoltageV(e.target.value)}
              />
            </label>
            <label>
              Voltaje máx.
              <input
                type="number"
                step="0.1"
                value={maxVoltageV}
                onChange={(e) => setMaxVoltageV(e.target.value)}
              />
            </label>
            <label className="inline-checkbox">
              <input
                type="checkbox"
                checked={autoCutoffEnabled}
                onChange={(e) => setAutoCutoffEnabled(e.target.checked)}
              />
              Corte automático
            </label>
            <div className="button-row">
              <button type="submit" className="btn-primary" disabled={updateProfile.isPending}>
                Guardar
              </button>
              <button type="button" onClick={() => setEditing(false)}>
                Cancelar
              </button>
            </div>
          </form>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td>{profile.id}</td>
      <td>{profile.name}</td>
      <td>{profile.max_current_a} A</td>
      <td>
        {profile.min_voltage_v ?? "—"} / {profile.max_voltage_v ?? "—"} V
      </td>
      <td>{profile.auto_cutoff_enabled ? "Sí" : "No"}</td>
      <td>
        <div className="site-card-actions">
          <button type="button" className="icon-btn" title="Editar" onClick={() => setEditing(true)}>
            ✎
          </button>
          <button
            type="button"
            className="icon-btn danger"
            title="Eliminar perfil"
            onClick={() => setConfirmingDelete(true)}
          >
            🗑
          </button>
          <ConfirmDialog
            open={confirmingDelete}
            onOpenChange={setConfirmingDelete}
            title={`¿Eliminar el perfil "${profile.name}"?`}
            confirmLabel="Eliminar"
            confirmPending={deleteProfile.isPending}
            onConfirm={handleDelete}
          />
        </div>
      </td>
    </tr>
  );
}

export function AdminDevicesPage() {
  const { data: devices, isLoading, isError } = useAdminDevices();
  const { data: profiles } = useAdminProfiles();
  const { data: sites } = useAdminSites();
  const createDevice = useCreateAdminDevice();
  const createProfile = useCreateAdminProfile();
  const reassignDevice = useReassignAdminDevice();
  const deleteDevice = useDeleteAdminDevice();
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<number | null>(null);

  const handleDelete = async (deviceId: number) => {
    try {
      await deleteDevice.mutateAsync(deviceId);
      notifySuccess("Dispositivo eliminado.");
      setConfirmingDeleteId(null);
    } catch (error) {
      notifyError(error, "No se pudo eliminar el dispositivo.");
    }
  };

  const deviceBeingDeleted = devices?.find((d) => d.id === confirmingDeleteId) ?? null;

  const [publicId, setPublicId] = useState("");
  const [deviceName, setDeviceName] = useState("");
  const [profileId, setProfileId] = useState<string>("");
  const [lastIssuedSecret, setLastIssuedSecret] = useState<DeviceCreateOut | null>(null);

  const [profileName, setProfileName] = useState("");
  const [maxCurrentA, setMaxCurrentA] = useState("15");
  const [minVoltageV, setMinVoltageV] = useState("");
  const [maxVoltageV, setMaxVoltageV] = useState("");
  const [autoCutoffEnabled, setAutoCutoffEnabled] = useState(true);

  const handleCreateDevice = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const created = await createDevice.mutateAsync({
        public_id: publicId,
        name: deviceName,
        profile_id: profileId ? Number(profileId) : undefined,
      });
      setLastIssuedSecret(created);
      setPublicId("");
      setDeviceName("");
      setProfileId("");
    } catch (error) {
      notifyError(error, "No se pudo dar de alta el dispositivo (¿ese identificador ya existe?).");
    }
  };

  const handleCreateProfile = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await createProfile.mutateAsync({
        name: profileName,
        max_current_a: Number(maxCurrentA),
        min_voltage_v: minVoltageV ? Number(minVoltageV) : undefined,
        max_voltage_v: maxVoltageV ? Number(maxVoltageV) : undefined,
        auto_cutoff_enabled: autoCutoffEnabled,
      });
      setProfileName("");
      setMaxCurrentA("15");
      setMinVoltageV("");
      setMaxVoltageV("");
      setAutoCutoffEnabled(true);
      notifySuccess("Perfil creado.");
    } catch (error) {
      notifyError(error, "No se pudo crear el perfil.");
    }
  };

  const handleReassign = async (deviceId: number, siteIdValue: string) => {
    try {
      await reassignDevice.mutateAsync({
        deviceId,
        siteId: siteIdValue ? Number(siteIdValue) : null,
      });
      notifySuccess("Dispositivo reasignado.");
    } catch (error) {
      notifyError(error, "No se pudo reasignar el dispositivo.");
    }
  };

  return (
    <div>
      <h1>Dispositivos y perfiles</h1>

      {lastIssuedSecret && (
        <div className="banner banner-warning">
          Secreto del dispositivo <strong>{lastIssuedSecret.public_id}</strong> (solo se muestra una
          vez, guárdalo): <code>{lastIssuedSecret.secret}</code>
        </div>
      )}

      <form className="glass-card inline-form" onSubmit={handleCreateDevice}>
        <input
          placeholder="public_id (ej. VG-001)"
          value={publicId}
          onChange={(e) => setPublicId(e.target.value)}
          required
        />
        <input
          placeholder="Nombre"
          value={deviceName}
          onChange={(e) => setDeviceName(e.target.value)}
          required
        />
        <select value={profileId} onChange={(e) => setProfileId(e.target.value)}>
          <option value="">Sin perfil</option>
          {profiles?.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.name} (max {profile.max_current_a}A)
            </option>
          ))}
        </select>
        <button type="submit" disabled={createDevice.isPending}>
          Dar de alta
        </button>
      </form>

      <form className="glass-card inline-form" onSubmit={handleCreateProfile}>
        <input
          placeholder="Nombre del perfil"
          value={profileName}
          onChange={(e) => setProfileName(e.target.value)}
          required
        />
        <input
          type="number"
          step="0.1"
          placeholder="Corriente máxima (A)"
          value={maxCurrentA}
          onChange={(e) => setMaxCurrentA(e.target.value)}
          required
        />
        <input
          type="number"
          step="0.1"
          placeholder="Voltaje mínimo (opcional)"
          value={minVoltageV}
          onChange={(e) => setMinVoltageV(e.target.value)}
        />
        <input
          type="number"
          step="0.1"
          placeholder="Voltaje máximo (opcional)"
          value={maxVoltageV}
          onChange={(e) => setMaxVoltageV(e.target.value)}
        />
        <label className="inline-checkbox">
          <input
            type="checkbox"
            checked={autoCutoffEnabled}
            onChange={(e) => setAutoCutoffEnabled(e.target.checked)}
          />
          Corte automático
        </label>
        <button type="submit" disabled={createProfile.isPending}>
          Crear perfil
        </button>
      </form>

      <h2>Perfiles de seguridad</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Corriente máx.</th>
            <th>Voltaje (mín/máx)</th>
            <th>Corte automático</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {profiles?.map((profile) => (
            <ProfileRow key={profile.id} profile={profile} />
          ))}
        </tbody>
      </table>

      <h2>Dispositivos</h2>
      {isLoading && <p>Cargando dispositivos...</p>}
      {isError && <p className="error">No se pudieron cargar los dispositivos.</p>}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>public_id</th>
            <th>Nombre</th>
            <th>Estado</th>
            <th>Sitio</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {devices?.map((device) => (
            <tr key={device.id}>
              <td>{device.id}</td>
              <td>{device.public_id}</td>
              <td>{device.name}</td>
              <td>
                {device.desired_state}/{device.actual_state}
                {device.is_locked_out && <span className="tag tag-danger">BLOQUEADO</span>}
              </td>
              <td>
                <select
                  value={device.site_id ?? ""}
                  onChange={(e) => handleReassign(device.id, e.target.value)}
                >
                  <option value="">Sin sitio</option>
                  {sites?.map((site) => (
                    <option key={site.id} value={site.id}>
                      {site.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <button
                  type="button"
                  className="icon-btn danger"
                  title="Eliminar dispositivo"
                  onClick={() => setConfirmingDeleteId(device.id)}
                >
                  🗑
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <ConfirmDialog
        open={confirmingDeleteId !== null}
        onOpenChange={(open) => !open && setConfirmingDeleteId(null)}
        title={
          deviceBeingDeleted
            ? `¿Eliminar el dispositivo "${deviceBeingDeleted.name}" (${deviceBeingDeleted.public_id})?`
            : "¿Eliminar el dispositivo?"
        }
        confirmLabel="Eliminar"
        confirmPending={deleteDevice.isPending}
        onConfirm={() => confirmingDeleteId !== null && handleDelete(confirmingDeleteId)}
      />
    </div>
  );
}
