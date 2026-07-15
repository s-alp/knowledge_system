import { useEffect, useState } from "react";

import { getViewer3DJob } from "../../../shared/api/client";
import type { Open3DResponse } from "../../../shared/types/viewer";

export function useViewer3DJob(initialJob: Open3DResponse | null) {
  // upload/open 直後のレスポンスを初期値にしつつ、必要な間だけ polling で追従する。
  const [job, setJob] = useState<Open3DResponse | null>(initialJob);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setJob(initialJob);
    setError(null);
  }, [initialJob]);

  useEffect(() => {
    if (!job || job.status === "ready" || job.status === "failed") {
      return;
    }

    // STEP 変換の完了時刻は読めないため、ジョブ API を薄く poll して UI 状態へ反映する。
    const timer = window.setInterval(async () => {
      try {
        const nextJob = await getViewer3DJob(job.jobId);
        setJob(nextJob);
        if (nextJob.status === "failed") {
          setError(nextJob.error || "3D conversion failed");
        }
      } catch (nextError) {
        // poll 失敗も利用者には通常のエラー文言として見せ、画面側の分岐を増やさない。
        setError(nextError instanceof Error ? nextError.message : "Failed to poll 3D job");
      }
    }, 1200);

    return () => window.clearInterval(timer);
  }, [job]);

  return { job, error };
}
