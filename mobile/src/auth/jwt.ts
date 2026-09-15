// Decodifica el payload de un JWT del lado del cliente solo para lectura
// (rol, id de usuario) — nunca para validar la firma, eso ya lo hizo el
// backend al emitirlo. No hay endpoint "/me" en la API.
export interface DecodedToken {
  sub: string;
  role: string;
  exp: number;
}

export function decodeJwt(token: string): DecodedToken | null {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(normalized);
    return JSON.parse(decoded) as DecodedToken;
  } catch {
    return null;
  }
}

export function isTokenExpired(decoded: DecodedToken): boolean {
  return decoded.exp * 1000 < Date.now();
}
