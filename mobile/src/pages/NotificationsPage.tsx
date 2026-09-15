import { useMyNotifications, useNotificationPreferences, useSetNotificationPreference } from "../api/hooks";

const CHANNEL_LABELS: Record<string, string> = {
  in_app: "Avisos dentro de la aplicación",
  push: "Notificaciones push del celular",
};

function PreferencesPanel() {
  const { data: preferences, isLoading } = useNotificationPreferences();
  const setPreference = useSetNotificationPreference();

  if (isLoading) return null;

  return (
    <div className="card">
      <h2>Preferencias</h2>
      {preferences?.map((preference) => (
        <label
          key={preference.channel}
          className="inline-checkbox"
          style={{ display: "flex", marginBottom: "0.5rem" }}
        >
          <input
            type="checkbox"
            checked={preference.enabled}
            onChange={(e) =>
              setPreference.mutate({ channel: preference.channel, enabled: e.target.checked })
            }
          />
          {CHANNEL_LABELS[preference.channel] ?? preference.channel}
        </label>
      ))}
    </div>
  );
}

export function NotificationsPage() {
  const { data: notifications, isLoading, isError } = useMyNotifications();

  return (
    <div>
      <h1>Notificaciones</h1>

      <PreferencesPanel />

      {isLoading && <p>Cargando notificaciones...</p>}
      {isError && <p className="error">No se pudieron cargar las notificaciones.</p>}

      {notifications && notifications.length > 0 ? (
        <ul className="list">
          {notifications.map((notification) => (
            <li key={notification.id}>
              <strong>{notification.title}</strong> — {notification.body}
              <div className="muted">{new Date(notification.created_at).toLocaleString()}</div>
            </li>
          ))}
        </ul>
      ) : (
        !isLoading && <p>Todavía no hay notificaciones.</p>
      )}
    </div>
  );
}
