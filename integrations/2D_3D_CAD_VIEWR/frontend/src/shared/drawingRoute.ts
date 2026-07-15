const DRAWING_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function normalizeDrawingId(candidate: string | null): string | null {
  if (!candidate) {
    return null;
  }
  const trimmed = candidate.trim();
  return DRAWING_ID_PATTERN.test(trimmed) ? trimmed : null;
}

export function resolveDrawingIdFromCandidate(candidate: string | null): string | null {
  const directDrawingId = normalizeDrawingId(candidate);
  if (directDrawingId) {
    return directDrawingId;
  }

  if (!candidate) {
    return null;
  }

  const trimmed = candidate.trim();
  const pathMatch = trimmed.match(/(?:^|\/)drawing\/([0-9a-f-]{36})(?:\/)?(?:\?.*)?$/i);
  const pathnameDrawingId = normalizeDrawingId(pathMatch?.[1] ?? null);
  if (pathnameDrawingId) {
    return pathnameDrawingId;
  }

  try {
    const url = new URL(trimmed);
    return resolveDrawingIdFromLocation(url.pathname, url.search);
  } catch {
    return null;
  }
}

export function resolveDrawingIdFromLocation(pathname: string, search: string): string | null {
  const pathnameMatch = pathname.match(/(?:^|\/)drawing\/([0-9a-f-]{36})(?:\/)?$/i);
  const pathnameDrawingId = normalizeDrawingId(pathnameMatch?.[1] ?? null);
  if (pathnameDrawingId) {
    return pathnameDrawingId;
  }

  const searchParams = new URLSearchParams(search);
  return normalizeDrawingId(searchParams.get("drawingId"));
}
