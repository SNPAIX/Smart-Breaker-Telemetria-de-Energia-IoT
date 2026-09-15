import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useClaimDevice, useSiteDevices } from "../api/hooks";
import type { Device } from "../api/types";

const STALE_AFTER_MS = 2 * 60 * 1000;

function deviceStatus(device: Device): { glow: string; icon: string; label: string } {
  const lastSeen = device.last_seen_at ? new Date(device.last_seen_at).getTime() : null;
  const isOnline = lastSeen !== null && Date.now() - lastSeen < STALE_AFTER_MS;

  if (device.is_locked_out) {
    return { glow: "#ef4444", icon: "⚠", label: "Bloqueado" };
  }
  if (!isOnline) {
    return { glow: "#9ca3af", icon: "⭘", label: "Sin conexión" };
  }
  if (device.actual_state === "ON") {
    return { glow: "#22c55e", icon: "⚡", label: "Encendido" };
  }
  return { glow: "#38bdf8", icon: "⏻", label: "Apagado" };
}

function DeviceCard({ device }: { device: Device }) {
  const status = deviceStatus(device);

  return (
    <li className="glass-card site-card" style={{ "--glow": status.glow } as React.CSSProperties}>
      <Link to={`/devices/${device.id}`} className="site-card-link">
        <span className="site-card-icon" aria-hidden="true">
          {status.icon}
        </span>
        <span className="site-card-name">{device.name}</span>
        <span className="tag">{device.public_id}</span>
        <span className="site-card-status">{status.label}</span>
      </Link>
    </li>
  );
}

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

      <form className="glass-card inline-form" onSubmit={handleClaim}>
        <input
          placeholder="Identificador del dispositivo (ej. VG-001)"
          value={publicId}
          onChange={(e) => setPublicId(e.target.value)}
          required
        />
        <button type="submit" className="btn-primary" disabled={claimDevice.isPending}>
          Vincular dispositivo
        </button>
      </form>
      {claimError && <p className="error">{claimError}</p>}

      {isLoading && <p>Cargando dispositivos...</p>}
      {isError && <p className="error">No se pudieron cargar los dispositivos.</p>}
      {devices && devices.length === 0 && <p>Este sitio todavía no tiene dispositivos.</p>}

      <ul className="list site-list">
        {devices?.map((device) => (
          <DeviceCard key={device.id} device={device} />
        ))}
      </ul>
    </div>
  );
}
