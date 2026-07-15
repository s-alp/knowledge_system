import { useEffect, useRef, useState } from "react";

import { openDrawingViewer2D, openViewer2D, uploadViewer2D } from "../../../shared/api/client";
import { DrawingOverviewPanel } from "../../../shared/components/DrawingOverviewPanel";
import { ViewerSourcePanel } from "../../../shared/components/ViewerSourcePanel";
import { getViewer2DLoadingMessage } from "../../../shared/loadingMessages";
import { LoadingNotice } from "../../../shared/components/LoadingNotice";
import { MetadataBar } from "../../../shared/components/MetadataBar";
import { buildDrawingInfoFields, type DrawingKnowledgeMock } from "../../../shared/mock/drawingKnowledge";
import type { DrawingBootstrapResponse, Open2DResponse } from "../../../shared/types/viewer";
import { useViewerSourceLoader } from "../../../shared/hooks/useViewerSourceLoader";
import { Viewer2DPreviewPane } from "../components/Viewer2DPreviewPane";
import { useViewer2DDocument } from "../hooks/useViewer2DDocument";

interface Viewer2DPageProps {
  drawingId: string;
  bootstrap: DrawingBootstrapResponse;
  knowledgeMock: DrawingKnowledgeMock;
  debugInputsEnabled: boolean;
  autoOpenDrawingSource?: boolean;
  initialLocalFile?: File | null;
}

export function Viewer2DPage({
  drawingId,
  bootstrap,
  knowledgeMock,
  debugInputsEnabled,
  autoOpenDrawingSource = true,
  initialLocalFile = null,
}: Viewer2DPageProps) {
  const [documentInfo, setDocumentInfo] = useState<Open2DResponse | null>(null);
  const [pageCount, setPageCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [requestError, setRequestError] = useState<string | null>(null);
  const autoOpenKeyRef = useRef<string | null>(null);
  const localFileLaunchKeyRef = useRef<string | null>(null);
  const { adapter, loading, error } = useViewer2DDocument(documentInfo);
  // URL / upload の開始処理だけを共通化し、2D 固有の描画制御はページ側へ残す。
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
  } = useViewerSourceLoader<Open2DResponse>({
    openFromUrl: openViewer2D,
    openFromFile: uploadViewer2D,
    resolveSuccessPhase: () => "processing",
    onSuccess: (response) => {
      setRequestError(null);
      setDocumentInfo(response);
      setCurrentPage(1);
    },
    urlErrorMessage: "Failed to open URL",
    fileErrorMessage: "Failed to open local file",
  });

  useEffect(() => {
    setDocumentInfo(null);
    setPageCount(0);
    setCurrentPage(1);
    setRequestError(null);
    autoOpenKeyRef.current = null;
  }, [drawingId]);

  useEffect(() => {
    if (!autoOpenDrawingSource) {
      return;
    }
    if (!bootstrap.availability.has2d) {
      setPhase("failed");
      setRequestError("この図面に 2D ソースは登録されていません。");
      return;
    }
    if (autoOpenKeyRef.current === drawingId) {
      return;
    }

    autoOpenKeyRef.current = drawingId;
    setRequestError(null);
    setPhase("uploading");
    void openDrawingViewer2D(drawingId)
      .then((response) => {
        setRequestError(null);
        setDocumentInfo(response);
        setCurrentPage(1);
        setPhase("processing");
      })
      .catch((nextError) => {
        setRequestError(nextError instanceof Error ? nextError.message : "Failed to open 2D drawing");
        setPhase("failed");
      });
  }, [autoOpenDrawingSource, bootstrap.availability.has2d, drawingId, setPhase]);

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
    // source の取得完了後も adapter 初期化が残るため、描画準備中へ phase を進める。
    if (phase === "processing" && loading) {
      setPhase("rendering");
    }
  }, [loading, phase, setPhase]);

  useEffect(() => {
    if (error) {
      setPhase("failed");
    }
  }, [error, setPhase]);

  const resolvedError = requestError ?? formError ?? error;
  const effectivePhase =
    loading && phase !== "uploading" && phase !== "failed" && phase !== "ready" ? "rendering" : phase;
  const loadingMessage = getViewer2DLoadingMessage(effectivePhase);
  const detailItems = buildDrawingInfoFields(bootstrap);
  const infoFooter = (
    <>
      {debugInputsEnabled ? (
        <ViewerSourcePanel
          title="手動入力"
          sectionLabel="Manual"
          description="PDM 連携を使わず、URL やローカルファイルから読み込めます。"
          url={url}
          urlPlaceholder="https://example.com/file.pdf"
          urlButtonLabel="Open 2D"
          acceptedTypes=".pdf,.jpg,.jpeg,.tif,.tiff"
          localHelperText="必要なときだけローカルファイルを選択してください。"
          selectedFileName={selectedFile?.name}
          localFileStatus={localFileStatus ?? undefined}
          openBusy={loading || isBusy}
          onUrlChange={setUrl}
          onOpenUrl={() => void handleOpenUrl()}
          onFileChange={handleFileChange}
          onPickStart={handlePickStart}
          onPickComplete={handlePickComplete}
        />
      ) : null}

      <div className="knowledge-stack">
        <MetadataBar
          filename={documentInfo?.filename}
          currentPage={currentPage}
          pageCount={pageCount}
          formatLabel={documentInfo?.extension?.toUpperCase()}
        />

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
            {resolvedError ? <span className="error-text">{resolvedError}</span> : <span>待機中</span>}
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
              <h2>{documentInfo?.filename ?? "ドキュメント"}</h2>
              <p className="section-description">ページ: {pageCount === 0 ? 0 : currentPage}/{pageCount}</p>
            </div>
          </div>
          <Viewer2DPreviewPane
            adapter={adapter}
            pageIndex={Math.max(currentPage - 1, 0)}
            currentPage={currentPage}
            pageCount={pageCount}
            onPreviousPage={() => setCurrentPage((page) => Math.max(1, page - 1))}
            onNextPage={() => setCurrentPage((page) => Math.min(pageCount, page + 1))}
            onPageCountResolved={(resolvedPageCount) => {
              // TIFF / PDF のページ数確定後も、現在ページが範囲外へ出ないように丸める。
              setPageCount(resolvedPageCount);
              setCurrentPage((page) => Math.min(Math.max(page, 1), Math.max(resolvedPageCount, 1)));
            }}
            onRendered={() => setPhase("ready")}
          />
        </div>
      </div>
    </section>
  );
}
