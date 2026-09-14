import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useClaimDevice, useSiteDevices } from "../api/hooks";

export function SiteDevicesPage() {
  const { siteId } = useParams<{ siteId: string }>();
  const numericSiteId = siteId ? Number(siteId) : undefined;
  const { data: devices, isLoading, isError } = useSiteDevices(numericSiteId);
  const claimDevice = useClaimDevice();
  const [publicId, setPublicId] = useState("");
  const [claimError, setClaimError] = useState<string | null>(null);

  const handleClaim = async (event: FormEvent) => {
    event.preventDefault();
    if (!numericSiteId) return;
    setClaimError(null);
    try {
      await claimDevice.mutateAsync({ public_id: publicId, site_id: numericSiteId });
      setPublicId("");
    } catch {
      setClaimError("No se pudo vincular ese dispositivo (¿ya está vinculado o no existe?).");
    }
  };

  return (
    <div>
      <h1>Dispositivos del sitio</h1>

      <form className="inline-form" onSubmit={handleClaim}>
        <input
          placeholder="Identificador del dispositivo (ej. VG-001)"
          value={publicId}
          onChange={(e) => setPublicId(e.target.value)}
          required
        />
        <button type="submit" disabled={claimDevice.isPending}>
          Vincular dispositivo
        </button>
      </form>
      {claimError && <p className="error">{claimError}</p>}

      {isLoading && <p>Cargando dispositivos...</p>}
      {isError && <p className="error">No se pudieron cargar los dispositivos.</p>}
      {devices && devices.length === 0 && <p>Este sitio todavía no tiene dispositivos.</p>}

      <ul className="list">
        {devices?.map((device) => (
          <li key={device.id}>
            <Link to={`/devices/${device.id}`}>
              {device.name} <span className="tag">{device.public_id}</span>{" "}
              {device.is_locked_out && <span className="tag tag-danger">BLOQUEADO</span>}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
