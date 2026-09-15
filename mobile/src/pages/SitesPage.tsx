import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { useCreateMySite, useMySites } from "../api/hooks";

export function SitesPage() {
  const { data: sites, isLoading, isError } = useMySites();
  const createSite = useCreateMySite();
  const [name, setName] = useState("");
  const [kind, setKind] = useState("casa");
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await createSite.mutateAsync({ name, kind });
      setName("");
    } catch {
      setError("No se pudo crear el sitio.");
    }
  };

  return (
    <div>
      <h1>Mis sitios</h1>

      <form className="inline-form" onSubmit={handleCreate}>
        <input
          placeholder="Nombre del sitio (ej. Mi casa)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="casa">Casa</option>
          <option value="taller">Taller</option>
          <option value="oficina">Oficina</option>
          <option value="otro">Otro</option>
        </select>
        <button type="submit" disabled={createSite.isPending}>
          {createSite.isPending ? "Creando..." : "Crear sitio"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}

      {isLoading && <p>Cargando sitios...</p>}
      {isError && <p className="error">No se pudieron cargar los sitios.</p>}
      {sites && sites.length === 0 && <p>No tenés ningún sitio todavía — creá uno arriba.</p>}

      <ul className="list">
        {sites?.map((site) => (
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
