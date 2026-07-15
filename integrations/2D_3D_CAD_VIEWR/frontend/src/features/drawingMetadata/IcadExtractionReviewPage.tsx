import { useEffect, useMemo, useState } from "react";

import {
  applyDrawingMetadataOverrides,
  enqueueDrawingMetadataExtraction,
  getDrawingMetadataRegistration,
  uploadIcadDrawingMetadata,
  type DrawingMetadataExtractionMode,
  type DrawingMetadataJobResponse,
  type DrawingMetadataRegistrationResponse,
} from "../../shared/api/client";

interface IcadExtractionReviewPageProps {
  file: File | null;
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

export function IcadExtractionReviewPage({ file, onBack }: IcadExtractionReviewPageProps) {
  const [registration, setRegistration] = useState<DrawingMetadataRegistrationResponse | null>(null);
  const [jobs, setJobs] = useState<DrawingMetadataJobResponse[]>([]);
  const [phase, setPhase] = useState<"idle" | "uploading" | "ready" | "extracting" | "saving">("idle");
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [manualMode, setManualMode] = useState<DrawingMetadataExtractionMode>("2d");
  const [manualJson, setManualJson] = useState("{\n  \"material\": \"\",\n  \"surface_treatment\": \"\"\n}");

  useEffect(() => {
    let cancelled = false;
    if (!file) {
      setPhase("idle");
      setMessage("ICADファイルを選択してください。");
      return;
    }

    setPhase("uploading");
    setMessage("ICADファイルを登録しています。");
    setError(null);
    void uploadIcadDrawingMetadata(file)
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
  }, [file]);

  const candidateTags = useMemo(() => collectCandidateTags(registration), [registration]);

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

    setPhase("extracting");
    setError(null);
    setMessage(`${mode.toUpperCase()} 抽出ジョブを起票しています。`);
    try {
      const job = await enqueueDrawingMetadataExtraction(registration.drawingId, mode, profile, options);
      setJobs((current) => [job, ...current]);
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

    let canonicalAttributes: Record<string, unknown>;
    try {
      canonicalAttributes = JSON.parse(manualJson) as Record<string, unknown>;
    } catch {
      setError("手直しJSONの形式が不正です。");
      return;
    }

    setPhase("saving");
    setError(null);
    try {
      await applyDrawingMetadataOverrides(
        registration.drawingId,
        manualMode,
        canonicalAttributes,
        "図面管理からの手直し",
      );
      await refreshRegistration();
      setPhase("ready");
      setMessage(`${manualMode.toUpperCase()} の手直しを保存しました。`);
    } catch (nextError) {
      setPhase("ready");
      setError(nextError instanceof Error ? nextError.message : "手直し保存に失敗しました。");
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
            <p>{file?.name ?? "未選択"}</p>
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
            disabled={!registration || phase === "extracting" || phase === "uploading"}
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
                        disabled={!registration || phase === "extracting" || phase === "uploading"}
                        onClick={() => enqueueExtraction("3d", row.retryProfile, row.retryOptions)}
                      >
                        3D条件で再抽出
                      </button>
                    ) : (
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={!registration || phase === "extracting" || phase === "uploading"}
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
            <p>{formatSnapshotStatus(registration, "2d")}</p>
          </div>
          <div className="production-detail-field">
            <span>3D</span>
            <p>{formatSnapshotStatus(registration, "3d")}</p>
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
        <textarea
          value={manualJson}
          onChange={(event) => setManualJson(event.target.value)}
          aria-label="手直しJSON"
        />
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
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.jobId}>
                  <td>{job.jobId}</td>
                  <td>{job.extractionMode.toUpperCase()}</td>
                  <td>{job.status}</td>
                  <td>{job.extractionProfile}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </section>
  );
}
