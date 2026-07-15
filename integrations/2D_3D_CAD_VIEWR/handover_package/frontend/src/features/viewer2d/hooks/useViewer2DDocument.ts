import { useEffect, useState } from "react";

import type { Open2DResponse } from "../../../shared/types/viewer";
import { createPdfAdapter } from "../adapters/pdfAdapter";
import { createRasterAdapter } from "../adapters/rasterAdapter";
import { createTiffAdapter } from "../adapters/tiffAdapter";
import type { TwoDDocumentAdapter } from "../adapters/types";

export function useViewer2DDocument(documentInfo: Open2DResponse | null) {
  const [adapter, setAdapter] = useState<TwoDDocumentAdapter | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const previousAdapter = adapter;

    async function load() {
      if (!documentInfo) {
        // 参照中ドキュメントが無くなったら、以前の adapter を破棄して画面を空に戻す。
        previousAdapter?.dispose?.();
        setAdapter(null);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        // API は sourceUrl を返すだけにとどめ、描画方式ごとの差分は adapter 側へ閉じ込める。
        const response = await fetch(documentInfo.sourceUrl);
        const blob = await response.blob();
        const buffer = await blob.arrayBuffer();
        const nextAdapter =
          documentInfo.extension === "pdf"
            ? await createPdfAdapter(buffer)
            : documentInfo.extension === "tiff"
              ? await createTiffAdapter(documentInfo.pageImageUrls)
              : await createRasterAdapter(blob);
        if (!cancelled) {
          // 切り替えが成功した時点で古い adapter を破棄し、表示資源を溜め込まない。
          previousAdapter?.dispose?.();
          setAdapter(nextAdapter);
        } else {
          nextAdapter.dispose?.();
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Failed to open 2D document");
          setAdapter(null);
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
  }, [documentInfo]);

  useEffect(
    () =>
      () => {
        // コンポーネント破棄時にも adapter を解放し、PDF worker や object URL を残さない。
        adapter?.dispose?.();
      },
    [adapter],
  );

  return {
    adapter,
    pageCount: adapter?.pageCount ?? 0,
    loading,
    error,
  };
}
