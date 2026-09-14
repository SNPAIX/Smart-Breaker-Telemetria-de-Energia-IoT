import { useParams } from "react-router-dom";

import {
  useDevice,
  useDeviceCost,
  useDeviceEvents,
  useDevicePrediction,
  useDeviceTelemetry,
  useReactivateDevice,
  useSwitchDevice,
} from "../api/hooks";

export function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const numericDeviceId = deviceId ? Number(deviceId) : undefined;

  const { data: device, isLoading, isError } = useDevice(numericDeviceId);
  const { data: telemetry } = useDeviceTelemetry(numericDeviceId);
  const { data: events } = useDeviceEvents(numericDeviceId);
  const { data: cost } = useDeviceCost(numericDeviceId);
  const { data: prediction } = useDevicePrediction(numericDeviceId);

  const switchDevice = useSwitchDevice(numericDeviceId ?? 0);
  const reactivateDevice = useReactivateDevice(numericDeviceId ?? 0);

  if (isLoading) return <p>Cargando dispositivo...</p>;
  if (isError || !device) return <p className="error">No se pudo cargar el dispositivo.</p>;

  const latestReading = telemetry?.[0];

  return (
    <div>
      <h1>
        {device.name} <span className="tag">{device.public_id}</span>
      </h1>

      {device.is_locked_out && (
        <div className="banner banner-danger">
          Este dispositivo está bloqueado por un evento crítico. No se puede encender hasta
          reactivarlo explícitamente.
          <button onClick={() => reactivateDevice.mutate()} disabled={reactivateDevice.isPending}>
            {reactivateDevice.isPending ? "Reactivando..." : "Reactivar dispositivo"}
          </button>
        </div>
      )}

      <section className="card">
        <h2>Estado</h2>
        <p>Deseado: {device.desired_state}</p>
        <p>Real (confirmado por el dispositivo): {device.actual_state}</p>
        <p>Último contacto: {device.last_seen_at ?? "nunca"}</p>
        <div className="button-row">
          <button
            onClick={() => switchDevice.mutate("ON")}
            disabled={switchDevice.isPending || device.is_locked_out}
          >
            Encender
          </button>
          <button onClick={() => switchDevice.mutate("OFF")} disabled={switchDevice.isPending}>
            Apagar
          </button>
        </div>
        {switchDevice.isError && (
          <p className="error">
            No se pudo cambiar el estado (¿el dispositivo está bloqueado por un evento crítico?).
          </p>
        )}
      </section>

      <section className="card">
        <h2>Última lectura</h2>
        {latestReading ? (
          <ul>
            <li>Voltaje: {latestReading.voltage} V</li>
            <li>Corriente: {latestReading.current} A</li>
            <li>Potencia: {latestReading.power} W</li>
            <li>Frecuencia: {latestReading.frequency} Hz</li>
            <li>Factor de potencia: {latestReading.power_factor}</li>
          </ul>
        ) : (
          <p>Sin lecturas todavía.</p>
        )}
      </section>

      <section className="card">
        <h2>Costo (período analizado)</h2>
        {cost ? (
          <p>
            {cost.total_kwh.toFixed(2)} kWh ≈ {cost.total_cost.toFixed(2)} {cost.currency}
            {cost.used_default_tariff && " (tarifa por defecto, sin Tariff configurada)"}
          </p>
        ) : (
          <p>Sin datos de costo todavía.</p>
        )}
      </section>

      <section className="card">
        <h2>Predicción mensual</h2>
        {prediction ? (
          <p>
            {prediction.projected_kwh.toFixed(2)} kWh proyectados ≈ {prediction.projected_cost.toFixed(2)}
          </p>
        ) : (
          <p>Sin predicción todavía.</p>
        )}
      </section>

      <section className="card">
        <h2>Eventos recientes</h2>
        {events && events.length > 0 ? (
          <ul className="list">
            {events.map((event) => (
              <li key={event.id}>
                <strong>{event.type}</strong> — {new Date(event.created_at).toLocaleString()}
              </li>
            ))}
          </ul>
        ) : (
          <p>Sin eventos.</p>
        )}
      </section>
    </div>
  );
}
