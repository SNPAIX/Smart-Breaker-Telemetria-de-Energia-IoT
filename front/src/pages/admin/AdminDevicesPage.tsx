import { useState, type FormEvent } from "react";

import {
  useAdminDevices,
  useAdminProfiles,
  useAdminSites,
  useCreateAdminDevice,
  useCreateAdminProfile,
  useReassignAdminDevice,
} from "../../api/hooks";
import type { DeviceCreateOut } from "../../api/types";

export function AdminDevicesPage() {
  const { data: devices, isLoading, isError } = useAdminDevices();
  const { data: profiles } = useAdminProfiles();
  const { data: sites } = useAdminSites();
  const createDevice = useCreateAdminDevice();
  const createProfile = useCreateAdminProfile();
  const reassignDevice = useReassignAdminDevice();

  const [publicId, setPublicId] = useState("");
  const [deviceName, setDeviceName] = useState("");
  const [profileId, setProfileId] = useState<string>("");
  const [lastIssuedSecret, setLastIssuedSecret] = useState<DeviceCreateOut | null>(null);

  const [profileName, setProfileName] = useState("");
  const [maxCurrentA, setMaxCurrentA] = useState("15");

  const handleCreateDevice = async (event: FormEvent) => {
    event.preventDefault();
    const created = await createDevice.mutateAsync({
      public_id: publicId,
      name: deviceName,
      profile_id: profileId ? Number(profileId) : undefined,
    });
    setLastIssuedSecret(created);
    setPublicId("");
    setDeviceName("");
    setProfileId("");
  };

  const handleCreateProfile = async (event: FormEvent) => {
    event.preventDefault();
    await createProfile.mutateAsync({ name: profileName, max_current_a: Number(maxCurrentA) });
    setProfileName("");
    setMaxCurrentA("15");
  };

  const handleReassign = (deviceId: number, siteIdValue: string) => {
    reassignDevice.mutate({ deviceId, siteId: siteIdValue ? Number(siteIdValue) : null });
  };

  return (
    <div>
      <h1>Dispositivos</h1>

      {lastIssuedSecret && (
        <div className="banner banner-warning">
          Secreto del dispositivo <strong>{lastIssuedSecret.public_id}</strong> (solo se muestra una
          vez, guárdalo): <code>{lastIssuedSecret.secret}</code>
        </div>
      )}

      <form className="inline-form" onSubmit={handleCreateDevice}>
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

      <form className="inline-form" onSubmit={handleCreateProfile}>
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
        <button type="submit" disabled={createProfile.isPending}>
          Crear perfil
        </button>
      </form>

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
                  defaultValue={device.site_id ?? ""}
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
