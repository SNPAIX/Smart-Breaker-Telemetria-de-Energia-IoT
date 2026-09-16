import { useAdminEvents, useAdminOverview } from "../../api/hooks";

export function AdminDashboardPage() {
  const { data: overview, isLoading, isError } = useAdminOverview();
  const { data: events } = useAdminEvents();

  if (isLoading) return <p>Cargando métricas...</p>;
  if (isError || !overview) return <p className="error">No se pudieron cargar las métricas.</p>;

  const { global_metrics: metrics, by_site: bySite, by_profile: byProfile } = overview;

  return (
    <div>
      <h1>Dashboard administrativo</h1>

      <section className="card-grid">
        <div className="stat-card">
          <span className="stat-value">{metrics.total_sites}</span>
          <span className="stat-label">Sitios</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{metrics.total_users}</span>
          <span className="stat-label">Usuarios</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{metrics.total_devices}</span>
          <span className="stat-label">Dispositivos</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{metrics.devices_online}</span>
          <span className="stat-label">En línea</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{metrics.devices_offline}</span>
          <span className="stat-label">Fuera de línea</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{metrics.critical_events_last_24h}</span>
          <span className="stat-label">Eventos críticos (24h)</span>
        </div>
      </section>

      <section className="card">
        <h2>Por sitio</h2>
        <table>
          <thead>
            <tr>
              <th>Sitio</th>
              <th>Dispositivos</th>
              <th>En línea</th>
            </tr>
          </thead>
          <tbody>
            {bySite.map((site) => (
              <tr key={site.site_id}>
                <td>{site.site_name}</td>
                <td>{site.device_count}</td>
                <td>{site.devices_online}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Por perfil</h2>
        <table>
          <thead>
            <tr>
              <th>Perfil</th>
              <th>Dispositivos</th>
            </tr>
          </thead>
          <tbody>
            {byProfile.map((profile) => (
              <tr key={profile.profile_id}>
                <td>{profile.profile_name}</td>
                <td>{profile.device_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Eventos recientes (todos los dispositivos)</h2>
        <ul className="list">
          {events?.map((event) => (
            <li key={event.id}>
              Dispositivo #{event.device_id} — <strong>{event.type}</strong> —{" "}
              {new Date(event.created_at).toLocaleString()}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
