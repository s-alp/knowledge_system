import { useCallback, useEffect, useRef, useState } from "react";

import {
  getKnowledgeEntities,
  getKnowledgeEntity,
  type KnowledgeEntityCatalogResponse,
  type KnowledgeEntityRecord,
  type KnowledgeEntityTargetKey,
} from "../../shared/api/client";

const entityListCache = new Map<string, KnowledgeEntityCatalogResponse>();

function cacheKey(targetKey: KnowledgeEntityTargetKey, query: string, page: number, pageSize: number) {
  return `${targetKey}:${query.trim()}:${page}:${pageSize}`;
}

export function useKnowledgeEntityList(targetKey: KnowledgeEntityTargetKey, query: string, page: number, pageSize = 50) {
  const key = cacheKey(targetKey, query, page, pageSize);
  const [catalog, setCatalog] = useState<KnowledgeEntityCatalogResponse | null>(() => entityListCache.get(key) ?? null);
  const [loading, setLoading] = useState(() => !entityListCache.has(key));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const cached = entityListCache.get(key);
    if (cached) {
      setCatalog(cached);
    }
    setLoading(!cached);
    setError(null);
    getKnowledgeEntities(targetKey, query, page * pageSize, pageSize)
      .then((payload) => {
        entityListCache.set(key, payload);
        if (active) {
          setCatalog(payload);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "ICAD構成情報を取得できませんでした。");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [key, page, pageSize, query, targetKey]);

  return { catalog, loading, error };
}


export function useKnowledgeEntityDetail(entityId: string | null, drawingId: string | null) {
  const [record, setRecord] = useState<KnowledgeEntityRecord | null>(null);
  const [loading, setLoading] = useState(Boolean(entityId));
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const load = useCallback(async () => {
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    if (!entityId) {
      setRecord(null);
      setLoading(false);
      setError("対象のICAD構成IDが指定されていません。");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = await getKnowledgeEntity(entityId, drawingId ?? undefined);
      if (requestId === requestIdRef.current) {
        setRecord(payload);
      }
    } catch (reason: unknown) {
      if (requestId === requestIdRef.current) {
        setError(reason instanceof Error ? reason.message : "ICAD構成詳細を取得できませんでした。");
      }
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [drawingId, entityId]);

  useEffect(() => {
    void load();
    return () => {
      requestIdRef.current += 1;
    };
  }, [load]);

  return { record, loading, error, refresh: load };
}
