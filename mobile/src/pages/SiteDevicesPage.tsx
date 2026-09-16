import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import {
  useClaimDevice,
  useCreateMyDevice,
  useSiteDevices,
  useSwitchDevice,
  useUnlinkDevice,
} from "../api/hooks";
import type { Device } from "../api/types";
import { notifyError, notifySuccess } from "../lib/errors";

const STALE_AFTER_MS = 2 * 60 * 1000;

function deviceStatus(
  device: Device,
  pendingDesired: "ON" | "OFF" | null,
): { glow: string; icon: string; label: string } {
  if (pendingDesired) {
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
  // actual_state ya confirmado por el dispositivo real.
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
    } catch (error) {
      notifyError(error, "No se pudo desvincular el dispositivo.");
      setConfirmingUnlink(false);
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
    <li className="card site-card" style={{ "--glow": status.glow } as React.CSSProperties}>
      <Link to={`/devices/${device.id}`} className="site-card-link">
        <span className="site-card-icon" aria-hidden="true">
          {status.icon}
        </span>
        <span className="site-card-text">
          <span className="site-card-name">{device.name}</span>
          <span className="tag">{device.public_id}</span>
          <span className="site-card-status">{status.label}</span>
        </span>
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
        {confirmingUnlink ? (
          <span className="confirm-inline">
            ¿Desvincular?
            <button type="button" className="icon-btn danger" onClick={handleUnlink}>
              Sí
            </button>
            <button type="button" className="icon-btn" onClick={() => setConfirmingUnlink(false)}>
              No
            </button>
          </span>
        ) : (
          <button
            type="button"
            className="icon-btn danger"
            title="Desvincular del sitio"
            onClick={() => setConfirmingUnlink(true)}
          >
            🔗✕
          </button>
        )}
      </div>
    </li>
  );
}

export function SiteDevicesPage() {
  const { siteId } = useParams<{ siteId: string }>();
  const numericSiteId = siteId ? Number(siteId) : undefined;
  const { data: devices, isLoading, isError } = useSiteDevices(numericSiteId);
  const claimDevice = useClaimDevice();
  const createDevice = useCreateMyDevice(numericSiteId ?? 0);

  const [publicId, setPublicId] = useState("");

  const [newPublicId, setNewPublicId] = useState("");
  const [newName, setNewName] = useState("");
  const [newMaxCurrent, setNewMaxCurrent] = useState("15");
  const [lastIssuedSecret, setLastIssuedSecret] = useState<{ public_id: string; secret: string } | null>(
    null,
  );

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

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!numericSiteId) return;
    try {
      const created = await createDevice.mutateAsync({
        public_id: newPublicId,
        name: newName,
        max_current_a: Number(newMaxCurrent),
      });
      setLastIssuedSecret({ public_id: created.public_id, secret: created.secret });
      setNewPublicId("");
      setNewName("");
      notifySuccess("Dispositivo dado de alta.");
    } catch {
      notifyError(null, "No se pudo dar de alta el dispositivo (¿ese identificador ya existe?).");
    }
  };

  return (
    <div>
      <h1>Dispositivos del sitio</h1>

      {lastIssuedSecret && (
        <div className="banner banner-warning">
          Dispositivo <strong>{lastIssuedSecret.public_id}</strong> creado — secreto (solo se muestra
          una vez, cargalo en el portal de aprovisionamiento del dispositivo físico):{" "}
          <code>{lastIssuedSecret.secret}</code>
        </div>
      )}

      <section className="card">
        <h2>Dar de alta un dispositivo nuevo</h2>
        <form className="inline-form" onSubmit={handleCreate}>
          <input
            placeholder="Identificador (ej. VG-001)"
            value={newPublicId}
            onChange={(e) => setNewPublicId(e.target.value)}
            required
          />
          <input
            placeholder="Nombre (ej. Luz Sala)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
          />
          <input
            type="number"
            step="0.1"
            placeholder="Corriente máx. (A)"
            value={newMaxCurrent}
            onChange={(e) => setNewMaxCurrent(e.target.value)}
            required
          />
          <button type="submit" disabled={createDevice.isPending}>
            {createDevice.isPending ? "Creando..." : "Dar de alta"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Vincular un dispositivo ya provisionado</h2>
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
      </section>

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
