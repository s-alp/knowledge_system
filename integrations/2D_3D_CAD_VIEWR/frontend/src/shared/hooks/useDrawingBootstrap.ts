import { useEffect, useState } from "react";

import { getDrawingBootstrap } from "../api/client";
import type { DrawingBootstrapResponse } from "../types/viewer";

export function useDrawingBootstrap(drawingId: string | null) {
  const [bootstrap, setBootstrap] = useState<DrawingBootstrapResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!drawingId) {
        setBootstrap(null);
        setError(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const response = await getDrawingBootstrap(drawingId);
        if (!cancelled) {
          setBootstrap(response);
        }
      } catch (nextError) {
        if (!cancelled) {
          setBootstrap(null);
          setError(nextError instanceof Error ? nextError.message : "Failed to load drawing detail");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [drawingId]);

  return { bootstrap, loading, error };
}
