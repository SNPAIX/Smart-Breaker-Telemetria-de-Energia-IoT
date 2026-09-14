import { useMyNotifications } from "../api/hooks";

export function NotificationsPage() {
  const { data: notifications, isLoading, isError } = useMyNotifications();

  if (isLoading) return <p>Cargando notificaciones...</p>;
  if (isError) return <p className="error">No se pudieron cargar las notificaciones.</p>;

  return (
    <div>
      <h1>Notificaciones</h1>
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
        <p>No tienes notificaciones.</p>
      )}
    </div>
  );
}
