import { Link } from "react-router-dom";

import { useMySites } from "../api/hooks";

export function SitesPage() {
  const { data: sites, isLoading, isError } = useMySites();

  if (isLoading) return <p>Cargando sitios...</p>;
  if (isError) return <p className="error">No se pudieron cargar los sitios.</p>;
  if (!sites || sites.length === 0) return <p>No perteneces a ningún sitio todavía.</p>;

  return (
    <div>
      <h1>Mis sitios</h1>
      <ul className="list">
        {sites.map((site) => (
          <li key={site.id}>
            <Link to={`/sites/${site.id}`}>
              {site.name} <span className="tag">{site.kind}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
