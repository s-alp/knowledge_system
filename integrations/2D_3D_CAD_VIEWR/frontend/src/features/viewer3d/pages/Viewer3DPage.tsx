import { Suspense, lazy, useCallback, useEffect, useReducer, useRef, useState } from "react";

import { openDrawingViewer3D, openViewer3D, uploadViewer3D } from "../../../shared/api/client";
import { DrawingOverviewPanel } from "../../../shared/components/DrawingOverviewPanel";
import { LoadingNotice } from "../../../shared/components/LoadingNotice";
import { MetadataBar } from "../../../shared/components/MetadataBar";
import { ViewerSourcePanel } from "../../../shared/components/ViewerSourcePanel";
import { getViewer3DLoadingMessage } from "../../../shared/loadingMessages";
import { buildDrawingInfoFields, type DrawingKnowledgeMock } from "../../../shared/mock/drawingKnowledge";
import type { DrawingBootstrapResponse, Open3DResponse } from "../../../shared/types/viewer";
import { useViewerSourceLoader } from "../../../shared/hooks/useViewerSourceLoader";
import { Viewer3DSectionControls } from "../controls/Viewer3DSectionControls";
import { Viewer3DToolbar } from "../controls/Viewer3DToolbar";
import { useViewer3DJob } from "../hooks/useViewer3DJob";
import { clippingReducer, initialClippingState } from "../state/viewer3dState";

const ThreeDViewerScene = lazy(() =>
  import("../components/ThreeDViewerScene").then((module) => ({ default: module.ThreeDViewerScene })),
);

interface Viewer3DPageProps {
  drawingId: string;
  bootstrap: DrawingBootstrapResponse;
  knowledgeMock: DrawingKnowledgeMock;
  debugInputsEnabled: boolean;
  autoOpenDrawingSource?: boolean;
  initialLocalFile?: File | null;
}

type CameraCommand =
  | { kind: "zoomIn"; token: number }
  | { kind: "zoomOut"; token: number }
  | { kind: "reset"; token: number }
  | null;

export function Viewer3DPage({
  drawingId,
  bootstrap,
  knowledgeMock,
  debugInputsEnabled,
  autoOpenDrawingSource = true,
  initialLocalFile = null,
}: Viewer3DPageProps) {
  const [initialJob, setInitialJob] = useState<Open3DResponse | null>(null);
  const [resetSignal, setResetSignal] = useState(0);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [cameraCommand, setCameraCommand] = useState<CameraCommand>(null);
  const autoOpenKeyRef = useRef<string | null>(null);
  const localFileLaunchKeyRef = useRef<string | null>(null);
  // section UI の入力値はページで持ち、Scene には確定済みの props として渡す。
  const [clippingState, dispatchClipping] = useReducer(clippingReducer, initialClippingState);
  const [edgeHighlightEnabled, setEdgeHighlightEnabled] = useState(false);
  const [capSupported, setCapSupported] = useState<boolean | null>(null);
  const { job, error } = useViewer3DJob(initialJob);
  // 3D 固有の違いは ready 条件と scene 周辺だけに寄せる。
  const {
    url,
    selectedFile,
    formError,
    phase,
    localFileStatus,
    setUrl,
    setPhase,
    isBusy,
    handleOpenUrl,
    handleFileChange,
    handlePickStart,
    handlePickComplete,
    handleOpenExternalFile,
  } = useViewerSourceLoader<Open3DResponse>({
    openFromUrl: openViewer3D,
    openFromFile: uploadViewer3D,
    resolveSuccessPhase: (response) => (response.status === "ready" ? "rendering" : "processing"),
    onSuccess: (response) => {
      setRequestError(null);
      setCapSupported(null);
      setInitialJob(response);
    },
    urlErrorMessage: "Failed to open 3D URL",
    fileErrorMessage: "Failed to open local 3D file",
  });
  const handleBoundsResolved = useCallback(
    ({ min, max }: { min: number; max: number }) => {
      dispatchClipping({ type: "setBounds", min, max });
    },
    [dispatchClipping],
  );

  useEffect(() => {
    setInitialJob(null);
    setRequestError(null);
    setCapSupported(null);
    autoOpenKeyRef.current = null;
  }, [drawingId]);

  useEffect(() => {
    if (!autoOpenDrawingSource) {
      return;
    }
    if (!bootstrap.availability.has3d) {
      setPhase("failed");
      setRequestError("この図面に 3D ソースは登録されていません。");
      return;
    }
    if (autoOpenKeyRef.current === drawingId) {
      return;
    }

    autoOpenKeyRef.current = drawingId;
    setRequestError(null);
    setPhase("uploading");
    void openDrawingViewer3D(drawingId)
      .then((response) => {
        setRequestError(null);
        setCapSupported(null);
        setInitialJob(response);
        setPhase(response.status === "ready" ? "rendering" : "processing");
      })
      .catch((nextError) => {
        setRequestError(nextError instanceof Error ? nextError.message : "Failed to open 3D drawing");
        setPhase("failed");
      });
  }, [autoOpenDrawingSource, bootstrap.availability.has3d, drawingId, setPhase]);

  useEffect(() => {
    if (autoOpenDrawingSource || !initialLocalFile) {
      return;
    }

    const fileKey = `${initialLocalFile.name}:${initialLocalFile.size}:${initialLocalFile.lastModified}`;
    if (localFileLaunchKeyRef.current === fileKey) {
      return;
    }

    localFileLaunchKeyRef.current = fileKey;
    handleOpenExternalFile(initialLocalFile);
  }, [autoOpenDrawingSource, handleOpenExternalFile, initialLocalFile]);

  useEffect(() => {
    // 断面表示と輪郭強調を同時に有効にすると見た目が煩雑になるため、断面を優先する。
    if (clippingState.enabled && edgeHighlightEnabled) {
      setEdgeHighlightEnabled(false);
    }
  }, [clippingState.enabled, edgeHighlightEnabled]);

  useEffect(() => {
    // backend job 状態と UI phase を対応付け、LoadingNotice の文言を一貫させる。
    if (job?.status === "queued" || job?.status === "processing") {
      setPhase("processing");
      return;
    }
    if (job?.status === "ready" && phase !== "ready") {
      setPhase("rendering");
      return;
    }
    if (job?.status === "failed") {
      setPhase("failed");
    }
  }, [job?.status, phase, setPhase]);

  useEffect(() => {
    if (error) {
      setPhase("failed");
    }
  }, [error, setPhase]);

  const resolvedError = requestError ?? formError ?? error ?? (job?.status === "failed" ? job.error : null);
  const effectivePhase =
    phase === "uploading"
      ? "uploading"
      : job?.status === "queued" || job?.status === "processing"
        ? "processing"
        : job?.status === "ready" && phase !== "ready"
          ? "rendering"
          : phase;
  const loadingMessage = getViewer3DLoadingMessage(effectivePhase);
  const sectionCapNotice =
    clippingState.enabled && capSupported === false
      ? "このモデルは断面キャップ未対応です。開いたメッシュのため断面内部が見える場合があります。"
      : null;
  const detailItems = buildDrawingInfoFields(bootstrap);
  const infoFooter = (
    <>
      {debugInputsEnabled ? (
        <ViewerSourcePanel
          title="手動入力"
          sectionLabel="Manual"
          description="PDM 連携を使わず、URL やローカルファイルから読み込めます。"
          url={url}
          urlPlaceholder="https://example.com/model.step"
          urlButtonLabel="Open 3D"
          acceptedTypes=".stl,.step,.stp"
          localHelperText="STEP もバックエンド経由で変換します。"
          selectedFileName={selectedFile?.name}
          localFileStatus={localFileStatus ?? undefined}
          openBusy={isBusy}
          onUrlChange={setUrl}
          onOpenUrl={() => void handleOpenUrl()}
          onFileChange={handleFileChange}
          onPickStart={handlePickStart}
          onPickComplete={handlePickComplete}
        />
      ) : null}

      <div className="knowledge-stack">
        <MetadataBar filename={job?.filename} formatLabel={job?.sourceExtension?.toUpperCase()} />
        <div className="status-panel">
          <div className="panel-header panel-header-inline">
            <div>
              <h3>ステータス</h3>
            </div>
          </div>
          <div className="status">
            {loadingMessage ? (
              <LoadingNotice title={loadingMessage.title} detail={loadingMessage.detail} phase={effectivePhase} />
            ) : null}
            {resolvedError ? <span className="error-text">{resolvedError}</span> : null}
            {sectionCapNotice ? <span>{sectionCapNotice}</span> : null}
            {clippingState.enabled && !edgeHighlightEnabled ? <span>断面キャップを優先するため、輪郭強調はOFFです。</span> : null}
            {!resolvedError && job?.status && job.status !== "ready" ? <span>Status: {job.status}</span> : null}
            {!loadingMessage && !resolvedError && !sectionCapNotice && (!job?.status || job.status === "ready") ? (
              <span>{job?.status === "ready" && job.modelUrl ? "表示中" : "待機中"}</span>
            ) : null}
          </div>
        </div>
      </div>
    </>
  );

  return (
    <section className="panel viewer-page">
      <div className="viewer-detail-grid">
        <DrawingOverviewPanel
          version={bootstrap.version}
          fields={detailItems}
          attributes={knowledgeMock.attributes}
          remarks={knowledgeMock.remarks}
          footerContent={infoFooter}
        />

        <div className="panel-section viewer-preview-card">
          <div className="panel-header panel-header-inline viewer-preview-header">
            <div>
              <h2>{job?.filename ?? "モデル"}</h2>
              <p className="section-description">{job?.sourceExtension?.toUpperCase() ?? "3D"}</p>
            </div>
          </div>
          <div className="viewer-preview-toolbar-shell">
            <Viewer3DToolbar
              clippingEnabled={clippingState.enabled}
              edgeHighlightEnabled={edgeHighlightEnabled}
              onReset={() => {
                setResetSignal((value) => value + 1);
                setCameraCommand((current) => ({ kind: "reset", token: (current?.token ?? 0) + 1 }));
              }}
              onZoomIn={() => setCameraCommand((current) => ({ kind: "zoomIn", token: (current?.token ?? 0) + 1 }))}
              onZoomOut={() =>
                setCameraCommand((current) => ({ kind: "zoomOut", token: (current?.token ?? 0) + 1 }))
              }
              onToggleClipping={() => dispatchClipping({ type: "toggle" })}
              onToggleEdgeHighlight={() => setEdgeHighlightEnabled((current) => !current)}
            />
          </div>
          {job?.status === "ready" && job.modelUrl && job.modelFormat ? (
            <Suspense fallback={<div className="viewer-stage viewer-stage-model" />}>
              {/* modelUrl を key にして、別モデルへ切り替わるたび Scene を素直に作り直す。 */}
              <ThreeDViewerScene
                key={job.modelUrl}
                modelUrl={job.modelUrl}
                modelFormat={job.modelFormat}
                clippingEnabled={clippingState.enabled}
                clippingAxis={clippingState.axis}
                clippingValue={clippingState.value}
                edgeHighlightEnabled={edgeHighlightEnabled}
                resetSignal={resetSignal}
                cameraCommand={cameraCommand}
                onBoundsResolved={handleBoundsResolved}
                onCapSupportResolved={setCapSupported}
                onReady={() => setPhase("ready")}
              />
            </Suspense>
          ) : (
            <div className="viewer-stage viewer-stage-model" />
          )}
          <Viewer3DSectionControls
            clippingAxis={clippingState.axis}
            clippingValue={clippingState.value}
            clippingMin={clippingState.min}
            clippingMax={clippingState.max}
            onAxisChange={(axis) => dispatchClipping({ type: "setAxis", axis })}
            onValueChange={(value) => dispatchClipping({ type: "setValue", value })}
          />
        </div>
      </div>
    </section>
  );
}
