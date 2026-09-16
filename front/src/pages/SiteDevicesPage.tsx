import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useClaimDevice, useSiteDevices, useSwitchDevice, useUnlinkDevice } from "../api/hooks";
import type { Device } from "../api/types";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { notifyError, notifySuccess } from "../lib/errors";

const STALE_AFTER_MS = 2 * 60 * 1000;

function deviceStatus(
  device: Device,
  pendingDesired: "ON" | "OFF" | null,
): { glow: string; icon: string; label: string } {
  if (pendingDesired) {
    // El ACK real puede tardar unos segundos — sin este estado, la
    // tarjeta se ve congelada entre el clic y el próximo refetch.
    return { glow: "#f59e0b", icon: "⏳", label: "Cambiando..." };
  }

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

function DeviceCard({ device, siteId }: { device: Device; siteId: number }) {
  const unlinkDevice = useUnlinkDevice();
  const switchDevice = useSwitchDevice(device.id);
  const [confirmingUnlink, setConfirmingUnlink] = useState(false);
  const [pendingDesired, setPendingDesired] = useState<"ON" | "OFF" | null>(null);

  // Se limpia solo apenas el polling de useSiteDevices trae el
  // actual_state ya confirmado por el dispositivo — no hace falta que el
  // usuario recargue ni que se quede esperando a mano.
  useEffect(() => {
    if (pendingDesired && device.actual_state === pendingDesired) {
      setPendingDesired(null);
      notifySuccess(pendingDesired === "ON" ? "Dispositivo encendido." : "Dispositivo apagado.");
    }
  }, [device.actual_state, pendingDesired]);

  const status = deviceStatus(device, pendingDesired);

  const handleUnlink = async () => {
    try {
      await unlinkDevice.mutateAsync({ deviceId: device.id, siteId });
      notifySuccess("Dispositivo desvinculado.");
      setConfirmingUnlink(false);
    } catch (error) {
      notifyError(error, "No se pudo desvincular el dispositivo.");
    }
  };

  const isOn = device.actual_state === "ON";

  const handleToggle = async () => {
    const target = isOn ? "OFF" : "ON";
    setPendingDesired(target);
    try {
      await switchDevice.mutateAsync(target);
    } catch (error) {
      setPendingDesired(null);
      notifyError(
        error,
        "No se pudo cambiar el estado (¿el dispositivo está bloqueado por un evento crítico?).",
      );
    }
  };

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

      <div className="site-card-actions">
        <button
          type="button"
          className="icon-btn"
          title={isOn ? "Apagar" : "Encender"}
          onClick={handleToggle}
          disabled={pendingDesired !== null || (!isOn && device.is_locked_out)}
        >
          ⏻
        </button>
        <button
          type="button"
          className="icon-btn danger"
          title="Desvincular del sitio"
          onClick={() => setConfirmingUnlink(true)}
        >
          🔗✕
        </button>
        <ConfirmDialog
          open={confirmingUnlink}
          onOpenChange={setConfirmingUnlink}
          title={`¿Desvincular "${device.name}" de este sitio?`}
          confirmLabel="Desvincular"
          confirmPending={unlinkDevice.isPending}
          onConfirm={handleUnlink}
        />
      </div>
    </li>
  );
}

export function SiteDevicesPage() {
  const { siteId } = useParams<{ siteId: string }>();
  const numericSiteId = siteId ? Number(siteId) : undefined;
  const { data: devices, isLoading, isError } = useSiteDevices(numericSiteId);
  const claimDevice = useClaimDevice();
  const [publicId, setPublicId] = useState("");

  const handleClaim = async (event: FormEvent) => {
    event.preventDefault();
    if (!numericSiteId) return;
    try {
      await claimDevice.mutateAsync({ public_id: publicId, site_id: numericSiteId });
      setPublicId("");
      notifySuccess("Dispositivo vinculado.");
    } catch {
      notifyError(null, "No se pudo vincular ese dispositivo (¿ya está vinculado o no existe?).");
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

      {isLoading && <p>Cargando dispositivos...</p>}
      {isError && <p className="error">No se pudieron cargar los dispositivos.</p>}
      {devices && devices.length === 0 && <p>Este sitio todavía no tiene dispositivos.</p>}

      <ul className="list site-list">
        {devices?.map((device) => (
          <DeviceCard key={device.id} device={device} siteId={numericSiteId as number} />
        ))}
      </ul>
    </div>
  );
}
