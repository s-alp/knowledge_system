import { useEffect, useMemo, useState } from "react";

import {
  applyDrawingMetadataReview,
  applyDrawingMetadataOverrides,
  enqueueDrawingMetadataExtraction,
  getDrawingMetadataRegistration,
  getDrawingMetadataJob,
  registerIcadDrawingMetadataPath,
  uploadIcadDrawingMetadata,
  type DrawingMetadataExtractionMode,
  type DrawingMetadataJobResponse,
  type DrawingMetadataRegistrationResponse,
} from "../../shared/api/client";

interface IcadExtractionReviewPageProps {
  file: File | null;
  sourcePath?: string;
  onBack: () => void;
}

type SourceRow = {
  mode: DrawingMetadataExtractionMode | "part";
  label: string;
  scope: string;
  retryProfile: string;
  retryOptions: Record<string, unknown>;
};

const sourceRows: SourceRow[] = [
  {
    mode: "2d",
    label: "2D",
    scope: "全ビュー、全レイヤー、印刷枠、図枠、寸法、訂正履歴、材質、表面処理、尺度",
    retryProfile: "2d_all_views_layers_print_frame",
    retryOptions: {
      scanAllViews: true,
      scanAllLayers: true,
      classifyPrintFrame: true,
      includeRevisionTable: true,
    },
  },
  {
    mode: "3d",
    label: "3D",
    scope: "図面名、重量、材質、パーツツリー、PRFX、ユニット番号、図面サイズ候補",
    retryProfile: "3d_model_part_attributes",
    retryOptions: {
      scanPartTree: true,
      includeMassProperties: true,
      includePartAttributes: true,
    },
  },
  {
    mode: "part",
    label: "パーツ付加情報",
    scope: "2D/3Dとは別情報源として、客先固有の任意属性を取得・照合",
    retryProfile: "part_attribute_deep_scan",
    retryOptions: {
      includePartAttributes: true,
      preserveCustomerFields: true,
    },
  },
];

const jobErrorDetailLimit = 1200;

function formatSnapshotStatus(registration: DrawingMetadataRegistrationResponse | null, mode: SourceRow["mode"]) {
  if (mode === "part") {
    const hasPartScan =
      registration?.snapshotsByMode["3d"]?.canonicalAttributes &&
      Object.keys(registration.snapshotsByMode["3d"].canonicalAttributes).some((key) =>
        key.toLowerCase().includes("part"),
      );
    return hasPartScan ? "3D抽出結果から確認" : "3D再抽出で取得対象";
  }

  const snapshot = registration?.snapshotsByMode[mode];
  if (snapshot) {
    return "抽出済み";
  }
  const latestJob = registration?.viewerBootstrap.metadata.extractionDiagnostics?.missingModes?.includes(mode)
    ? null
    : undefined;
  return latestJob === undefined ? "登録済み" : "未抽出";
}

function collectCandidateTags(registration: DrawingMetadataRegistrationResponse | null): string[] {
  const tags = registration?.viewerBootstrap.metadata.tags ?? [];
  return tags.length ? tags : ["抽出後に候補表示"];
}

function formatReviewStatus(status: string | undefined) {
  if (status === "confirmed") {
    return "確認済み";
  }
  if (status === "needs_correction") {
    return "要手直し";
  }
  return "未レビュー";
}

function formatJobStatus(status: string) {
  return {
    queued: "待機中",
    processing: "抽出中",
    succeeded: "完了",
    failed: "失敗",
  }[status] ?? status;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function summarizeJobError(value: string | null | undefined, apiSummary?: string) {
  if (apiSummary) {
    return apiSummary;
  }
  if (!value) {
    return "-";
  }
  if (value.includes("指定したファイルは図面ファイルではありません")) {
    return "ICDファイルですが、ICAD/SXNETが図面モデルとして開けません。原本パス、外部参照、ICAD対応版を確認してください。";
  }
  if (value.includes("ICADSXはすでに起動されています")) {
    return "ICAD/SXの多重起動ダイアログが発生しています。既存ICADを閉じて再実行してください。";
  }
  if (value.includes("FileNotFound") || value.includes("ファイルが見つかりません")) {
    return "対象ファイルまたは参照ファイルが見つかりません。保存先パスと参照先を確認してください。";
  }
  const firstLine = value.split(/\r?\n/).find(Boolean) ?? value;
  return firstLine.length > 120 ? `${firstLine.slice(0, 120)}...` : firstLine;
}

function formatJobErrorDetail(job: DrawingMetadataJobResponse) {
  const value = job.errorMessage;
  if (!value) {
    return "";
  }
  if (value.length <= jobErrorDetailLimit) {
    return value;
  }
  const originalLength = job.errorMessageLength ?? value.length;
  return `${value.slice(0, jobErrorDetailLimit)}\n...（失敗理由は全${originalLength}文字のため先頭${jobErrorDetailLimit}文字のみ表示。全文はworkerログまたは診断スクリプトで確認してください。）`;
}

function isActiveJob(job: DrawingMetadataJobResponse) {
  return job.status === "queued" || job.status === "processing";
}

function collectLatestJobs(registration: DrawingMetadataRegistrationResponse | null): DrawingMetadataJobResponse[] {
  if (!registration) {
    return [];
  }
  return (["2d", "3d"] as DrawingMetadataExtractionMode[])
    .map((mode) => registration.latestJobsByMode?.[mode] ?? registration.snapshotsByMode[mode]?.latestJob ?? null)
    .filter((job): job is DrawingMetadataJobResponse => Boolean(job));
}

function mergeJobs(
  currentJobs: DrawingMetadataJobResponse[],
  incomingJobs: DrawingMetadataJobResponse[],
): DrawingMetadataJobResponse[] {
  const nextJobs = [...currentJobs];
  for (const incomingJob of incomingJobs) {
    const existingIndex = nextJobs.findIndex((job) => job.jobId === incomingJob.jobId);
    if (existingIndex >= 0) {
      nextJobs[existingIndex] = incomingJob;
    } else {
      nextJobs.unshift(incomingJob);
    }
  }
  return nextJobs;
}

export function IcadExtractionReviewPage({ file, sourcePath = "", onBack }: IcadExtractionReviewPageProps) {
  const [registration, setRegistration] = useState<DrawingMetadataRegistrationResponse | null>(null);
  const [jobs, setJobs] = useState<DrawingMetadataJobResponse[]>([]);
  const [phase, setPhase] = useState<"idle" | "uploading" | "ready" | "extracting" | "saving">("idle");
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [manualMode, setManualMode] = useState<DrawingMetadataExtractionMode>("2d");
  const [manualFields, setManualFields] = useState<Record<string, string>>({});
  const [manualTags, setManualTags] = useState("");
  const selectedSourceLabel = sourcePath.trim() || file?.name || "未選択";

  useEffect(() => {
    let cancelled = false;
    const trimmedSourcePath = sourcePath.trim();
    if (!file && !trimmedSourcePath) {
      setPhase("idle");
      setMessage("ICAD原本パスを入力するか、ICADファイルを選択してください。");
      return;
    }

    setPhase("uploading");
    setMessage("ICADファイルを登録しています。");
    setError(null);
    const request = trimmedSourcePath
      ? registerIcadDrawingMetadataPath(trimmedSourcePath)
      : uploadIcadDrawingMetadata(file as File);
    void request
      .then((nextRegistration) => {
        if (cancelled) {
          return;
        }
        setRegistration(nextRegistration);
        setPhase("ready");
        setMessage("登録しました。抽出開始または条件付き再抽出を実行できます。");
      })
      .catch((nextError: unknown) => {
        if (cancelled) {
          return;
        }
        setPhase("idle");
        setError(nextError instanceof Error ? nextError.message : "ICAD登録に失敗しました。");
      });

    return () => {
      cancelled = true;
    };
  }, [file, sourcePath]);

  const candidateTags = useMemo(() => collectCandidateTags(registration), [registration]);
  const activeSnapshot = registration?.snapshotsByMode[manualMode];
  const activeJobs = useMemo(() => jobs.filter(isActiveJob), [jobs]);
  const isRegisteringOrQueueing = phase === "uploading" || phase === "extracting";
  const hasActiveJobForMode = (mode: DrawingMetadataExtractionMode) =>
    activeJobs.some((job) => job.extractionMode === mode);
  const activeTagValues = useMemo(
    () => (activeSnapshot?.derivedTags ?? [])
      .map((item) => typeof item === "object" && item !== null && "tag" in item ? String((item as { tag: unknown }).tag) : "")
      .filter(Boolean),
    [activeSnapshot],
  );

  useEffect(() => {
    const canonical = activeSnapshot?.canonicalAttributes ?? {};
    setManualFields(Object.fromEntries(
      ["drawing_number", "drawing_name", "material", "surface_treatment", "paint", "mass_value", "weight_value", "scale", "drawing_size", "prfx", "unit_number"]
        .map((key) => [key, canonical[key] == null ? "" : String(canonical[key])]),
    ));
    setManualTags(activeTagValues.join("、"));
  }, [activeSnapshot, activeTagValues, manualMode]);

  useEffect(() => {
    const latestJobs = collectLatestJobs(registration);
    if (latestJobs.length) {
      setJobs((currentJobs) => mergeJobs(currentJobs, latestJobs));
    }
  }, [registration]);

  const activeJobIds = jobs
    .filter(isActiveJob)
    .map((job) => job.jobId)
    .join(",");

  useEffect(() => {
    if (!activeJobIds || !registration) {
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const nextJobs = await Promise.all(jobs.map((job) => getDrawingMetadataJob(job.jobId)));
        if (cancelled) {
          return;
        }
        setJobs((currentJobs) => mergeJobs(currentJobs, nextJobs));
        if (!nextJobs.some(isActiveJob)) {
          const nextRegistration = await getDrawingMetadataRegistration(registration.drawingId);
          if (!cancelled) {
            const failedJob = nextJobs.find((job) => job.status === "failed");
            setRegistration(nextRegistration);
            setPhase("ready");
            if (failedJob) {
              setMessage("抽出が失敗しました。エラー内容を確認して条件を変えて再抽出してください。");
              setError(summarizeJobError(failedJob.errorMessage || "抽出ジョブが失敗しました。"));
            } else {
              setMessage("抽出が完了しました。候補内容を確認してください。");
            }
          }
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "抽出状態を確認できませんでした。");
        }
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 1500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [activeJobIds, registration?.drawingId]);

  async function refreshRegistration() {
    if (!registration) {
      return;
    }
    const nextRegistration = await getDrawingMetadataRegistration(registration.drawingId);
    setRegistration(nextRegistration);
  }

  async function enqueueExtraction(mode: DrawingMetadataExtractionMode, profile: string, options: Record<string, unknown>) {
    if (!registration) {
      setError("ICADファイルの登録後に抽出できます。");
      return;
    }
    if (phase === "extracting" || hasActiveJobForMode(mode)) {
      setError(`${mode.toUpperCase()} 抽出ジョブはすでに起票済みです。現在の状態を確認してください。`);
      return;
    }

    setPhase("extracting");
    setError(null);
    setMessage(`${mode.toUpperCase()} 抽出ジョブを起票しています。`);
    try {
      const job = await enqueueDrawingMetadataExtraction(registration.drawingId, mode, profile, options);
      setJobs((currentJobs) => mergeJobs(currentJobs, [job]));
      await refreshRegistration();
      setPhase("ready");
      setMessage(`${mode.toUpperCase()} 抽出ジョブを起票しました。`);
    } catch (nextError) {
      setPhase("ready");
      setError(nextError instanceof Error ? nextError.message : "抽出ジョブの起票に失敗しました。");
    }
  }

  async function enqueueAllExtractions() {
    const twoD = sourceRows[0];
    const threeD = sourceRows[1];
    await enqueueExtraction("2d", twoD.retryProfile, twoD.retryOptions);
    await enqueueExtraction("3d", threeD.retryProfile, threeD.retryOptions);
  }

  async function saveManualOverride() {
    if (!registration) {
      setError("ICADファイルの登録後に手直しできます。");
      return;
    }

    setPhase("saving");
    setError(null);
    try {
      await applyDrawingMetadataOverrides(
        registration.drawingId,
        manualMode,
        manualFields,
        "図面管理からの手直し",
        {
          derivedTags: {
            added: [...new Set(manualTags.split(/[、,\n]/).map((value) => value.trim()).filter(Boolean))]
              .filter((value) => !activeTagValues.includes(value)),
            removed: activeTagValues.filter((value) => !manualTags.split(/[、,\n]/).map((item) => item.trim()).includes(value)),
          },
        },
      );
      await refreshRegistration();
      setPhase("ready");
      setMessage(`${manualMode.toUpperCase()} の手直しを保存しました。`);
    } catch (nextError) {
      setPhase("ready");
      setError(nextError instanceof Error ? nextError.message : "手直し保存に失敗しました。");
    }
  }

  async function saveReviewDecision(
    mode: DrawingMetadataExtractionMode,
    decision: "confirmed" | "needs_correction",
  ) {
    if (!registration) {
      setError("ICADファイルの登録後にレビューできます。");
      return;
    }
    setPhase("saving");
    setError(null);
    try {
      await applyDrawingMetadataReview(
        registration.drawingId,
        mode,
        decision,
        decision === "confirmed" ? "図面管理で候補内容を確認" : "図面管理で手直しが必要と判断",
      );
      await refreshRegistration();
      setPhase("ready");
      setMessage(`${mode.toUpperCase()} のレビュー状態を保存しました。`);
    } catch (nextError) {
      setPhase("ready");
      setError(nextError instanceof Error ? nextError.message : "レビュー状態の保存に失敗しました。");
    }
  }

  return (
    <section className="knowledge-production-page entity-page">
      <section className="production-section production-basic-section">
        <div className="production-section-header">
          <div>
            <h2>ICADタグ・属性取得</h2>
            <p className="production-section-note">
              図面管理でICAD抽出結果を確認し、必要に応じて再抽出・手直しを行います。
            </p>
          </div>
          <button className="secondary-button" type="button" onClick={onBack}>
            図面管理に戻る
          </button>
        </div>
        <div className="production-section-divider" />
        <div className="production-detail-grid">
          <div className="production-detail-field">
            <span>選択ファイル</span>
            <p>{selectedSourceLabel}</p>
          </div>
          <div className="production-detail-field">
            <span>登録ID</span>
            <p>{registration?.drawingId ?? "-"}</p>
          </div>
          <div className="production-detail-field">
            <span>保存先</span>
            <p>{registration?.sourcePath ?? "-"}</p>
          </div>
          <div className="production-detail-field">
            <span>状態</span>
            <p>{message || phase}</p>
          </div>
          <div className="production-detail-field">
            <span>更新後の確認先</span>
            <p>この画面のジョブ履歴 / システム設定のICAD抽出管理</p>
          </div>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="production-section">
        <div className="production-section-header">
          <div>
            <h2>抽出・再抽出</h2>
            <p className="production-section-note">
              未抽出や条件違いは同じ図面管理画面で条件を変えて再実行します。
            </p>
          </div>
          <button
            className="primary-button"
            type="button"
            disabled={!registration || isRegisteringOrQueueing || hasActiveJobForMode("2d") || hasActiveJobForMode("3d")}
            onClick={enqueueAllExtractions}
          >
            2D/3Dを抽出
          </button>
        </div>
        <div className="production-section-divider" />
        <div className="production-table-shell">
          <table className="production-table">
            <thead>
              <tr>
                <th>情報源</th>
                <th>取得範囲</th>
                <th>状態</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {sourceRows.map((row) => (
                <tr key={row.mode}>
                  <th>{row.label}</th>
                  <td>{row.scope}</td>
                  <td>{formatSnapshotStatus(registration, row.mode)}</td>
                  <td>
                    {row.mode === "part" ? (
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={!registration || isRegisteringOrQueueing || hasActiveJobForMode("3d")}
                        onClick={() => enqueueExtraction("3d", row.retryProfile, row.retryOptions)}
                      >
                        3D条件で再抽出
                      </button>
                    ) : (
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={
                          !registration ||
                          isRegisteringOrQueueing ||
                          hasActiveJobForMode(row.mode as DrawingMetadataExtractionMode)
                        }
                        onClick={() =>
                          enqueueExtraction(row.mode as DrawingMetadataExtractionMode, row.retryProfile, row.retryOptions)
                        }
                      >
                        再抽出
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="production-section">
        <h2>レビュー</h2>
        <div className="production-section-divider" />
        <div className="production-detail-grid">
          <div className="production-detail-field">
            <span>2D</span>
            <p>
              {formatSnapshotStatus(registration, "2d")} / {formatReviewStatus(registration?.snapshotsByMode["2d"]?.reviewStatus)}
            </p>
            <div className="production-inline-actions">
              <button
                className="secondary-button"
                type="button"
                disabled={!registration?.snapshotsByMode["2d"] || phase === "saving"}
                onClick={() => saveReviewDecision("2d", "confirmed")}
              >
                候補を確定
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={!registration?.snapshotsByMode["2d"] || phase === "saving"}
                onClick={() => saveReviewDecision("2d", "needs_correction")}
              >
                要手直し
              </button>
            </div>
          </div>
          <div className="production-detail-field">
            <span>3D</span>
            <p>
              {formatSnapshotStatus(registration, "3d")} / {formatReviewStatus(registration?.snapshotsByMode["3d"]?.reviewStatus)}
            </p>
            <div className="production-inline-actions">
              <button
                className="secondary-button"
                type="button"
                disabled={!registration?.snapshotsByMode["3d"] || phase === "saving"}
                onClick={() => saveReviewDecision("3d", "confirmed")}
              >
                候補を確定
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={!registration?.snapshotsByMode["3d"] || phase === "saving"}
                onClick={() => saveReviewDecision("3d", "needs_correction")}
              >
                要手直し
              </button>
            </div>
          </div>
          <div className="production-detail-field">
            <span>タグ候補</span>
            <p>{candidateTags.join(", ")}</p>
          </div>
          <div className="production-detail-field">
            <span>表示先</span>
            <p>図面詳細 / 製品・装置・ユニット詳細 / 部品詳細</p>
          </div>
        </div>
      </section>

      <section className="production-section">
        <h2>手直し</h2>
        <div className="production-section-divider" />
        <div className="form-grid launcher-form">
          <label className="input-stack">
            <span className="field-label">対象</span>
            <select value={manualMode} onChange={(event) => setManualMode(event.target.value as DrawingMetadataExtractionMode)}>
              <option value="2d">2D</option>
              <option value="3d">3D</option>
            </select>
          </label>
          <button
            className="primary-button"
            type="button"
            disabled={!registration || phase === "saving" || phase === "uploading"}
            onClick={saveManualOverride}
          >
            手直しを保存
          </button>
        </div>
        <div className="production-edit-grid drawing-metadata-edit-grid">
          {[
            ["drawing_number", "図番"], ["drawing_name", "図面名"], ["material", "材質"],
            ["surface_treatment", "表面処理"], ["paint", "塗装"], ["mass_value", "質量 (kg)"],
            ["weight_value", "重量 (kg)"], ["scale", "尺度"], ["drawing_size", "図面サイズ"],
            ["prfx", "PRFX"], ["unit_number", "ユニット番号"],
          ].map(([key, label]) => (
            <label key={key} className="production-form-field"><span>{label}</span><input value={manualFields[key] ?? ""} onChange={(event) => setManualFields((current) => ({ ...current, [key]: event.target.value }))} /></label>
          ))}
          <label className="production-form-field production-form-field-wide"><span>タグ</span><textarea value={manualTags} onChange={(event) => setManualTags(event.target.value)} /><small>読点または改行で区切ります。</small></label>
        </div>
      </section>

      {jobs.length > 0 ? (
        <section className="production-section">
          <h2>ジョブ履歴</h2>
          <div className="production-section-divider" />
          <table className="production-table">
            <thead>
              <tr>
                <th>ジョブID</th>
                <th>対象</th>
                <th>状態</th>
                <th>条件</th>
                <th>起票日時</th>
                <th>開始日時</th>
                <th>完了日時</th>
                <th>失敗理由</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.jobId}>
                  <td>{job.jobId}</td>
                  <td>{job.extractionMode.toUpperCase()}</td>
                  <td>{formatJobStatus(job.status)}</td>
                  <td>{job.extractionProfile}</td>
                  <td>{formatDateTime(job.createdAt)}</td>
                  <td>{formatDateTime(job.startedAt)}</td>
                  <td>{formatDateTime(job.finishedAt ?? job.updatedAt)}</td>
                  <td>
                    {job.errorMessage ? (
                      <details>
                        <summary>{summarizeJobError(job.errorMessage, job.errorMessageSummary)}</summary>
                        <pre>{formatJobErrorDetail(job)}</pre>
                        {job.errorMessageTruncated || job.errorMessage.length > jobErrorDetailLimit ? (
                          <p className="production-section-note">全文は長すぎるため画面では省略しています。</p>
                        ) : null}
                      </details>
                    ) : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </section>
  );
}
