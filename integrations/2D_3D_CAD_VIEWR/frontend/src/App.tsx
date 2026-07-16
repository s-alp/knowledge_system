import { Suspense, lazy, useEffect, useMemo, useState } from "react";

import { DrawingSupplementPanels } from "./shared/components/DrawingSupplementPanels";
import { DrawingEntryPanel } from "./shared/components/DrawingEntryPanel";
import { LicensePanel } from "./shared/components/LicensePanel";
import { PlaceholderKnowledgePage, type DetailPageKey } from "./features/knowledgeEntities/EntityPages";
import { IcadEntityDetailPage, IcadEntityListPage } from "./features/knowledgeEntities/IcadEntityPages";
import { IcadExtractionReviewPage } from "./features/drawingMetadata/IcadExtractionReviewPage";
import type { KnowledgePageKey } from "./features/knowledgeEntities/types";
import { TagAutomationSettingsPage } from "./features/knowledgeSettings/TagAutomationSettingsPage";
import { resolveDrawingIdFromLocation, resolveViewerModeFromSearch } from "./shared/drawingRoute";
import { isViewerDebugInputsEnabled } from "./shared/env";
import { useDrawingBootstrap } from "./shared/hooks/useDrawingBootstrap";
import { buildDrawingKnowledgeDetail } from "./shared/knowledge/drawingKnowledge";
import type { DrawingBootstrapResponse } from "./shared/types/viewer";

const Viewer2DPage = lazy(() =>
  import("./features/viewer2d/pages/Viewer2DPage").then((module) => ({ default: module.Viewer2DPage })),
);
const Viewer3DPage = lazy(() =>
  import("./features/viewer3d/pages/Viewer3DPage").then((module) => ({ default: module.Viewer3DPage })),
);

type ViewMode = "2d" | "3d";
type LocalLaunchState = {
  mode: ViewMode;
  file: File;
};
type NavigationItem = {
  key: KnowledgePageKey;
  label: string;
};
type NavigationGroup = {
  title: string;
  items: NavigationItem[];
};

const navigationGroups: NavigationGroup[] = [
  {
    title: "メイン",
    items: [
      { key: "project", label: "プロジェクト" },
      { key: "product", label: "製品・装置・ユニット" },
      { key: "part", label: "部品" },
      { key: "drawing", label: "図面管理" },
      { key: "document", label: "文書管理" },
    ],
  },
  {
    title: "検索",
    items: [
      { key: "search", label: "統合検索" },
      { key: "chat", label: "チャット" },
      { key: "similar", label: "類似検索" },
    ],
  },
  {
    title: "営業",
    items: [{ key: "customer", label: "顧客管理" }],
  },
  {
    title: "管理",
    items: [
      { key: "notice", label: "お知らせ管理" },
      { key: "master", label: "マスタ設定" },
      { key: "system", label: "システム設定" },
    ],
  },
];

const pageTitles: Record<KnowledgePageKey, string> = {
  project: "プロジェクト詳細",
  product: "製品・装置・ユニット一覧",
  part: "部品一覧",
  drawing: "図面管理",
  document: "文書管理",
  search: "統合検索",
  chat: "チャット",
  similar: "類似検索",
  customer: "顧客管理",
  notice: "お知らせ管理",
  master: "マスタ設定",
  system: "システム設定",
};

function resolveInitialMode(bootstrap: DrawingBootstrapResponse, requestedMode: ViewMode | null): ViewMode {
  if (requestedMode === "2d" && bootstrap.availability.has2d) {
    return "2d";
  }
  if (requestedMode === "3d" && bootstrap.availability.has3d) {
    return "3d";
  }
  if (bootstrap.defaultMode === "3d" && bootstrap.availability.has3d) {
    return "3d";
  }
  if (bootstrap.availability.has2d) {
    return "2d";
  }
  return "3d";
}

export default function App() {
  const drawingId = useMemo(
    () => resolveDrawingIdFromLocation(window.location.pathname, window.location.search),
    [],
  );
  const requestedMode = useMemo(() => resolveViewerModeFromSearch(window.location.search), []);
  const debugInputsEnabled = useMemo(() => isViewerDebugInputsEnabled(), []);
  const { bootstrap, loading, error } = useDrawingBootstrap(drawingId);
  const [localLaunch, setLocalLaunch] = useState<LocalLaunchState | null>(null);
  const [icadExtractionFile, setIcadExtractionFile] = useState<File | null>(null);
  const [showIcadExtractionReview, setShowIcadExtractionReview] = useState(false);
  const [activePage, setActivePage] = useState<KnowledgePageKey>("drawing");
  const [detailPage, setDetailPage] = useState<DetailPageKey | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<{ entityId: string; drawingId: string } | null>(null);
  const detailMock = useMemo(
    () => (bootstrap ? buildDrawingKnowledgeDetail(bootstrap) : null),
    [bootstrap],
  );
  const [mode, setMode] = useState<ViewMode>("2d");
  const localBootstrap = useMemo<DrawingBootstrapResponse | null>(() => {
    if (!localLaunch) {
      return null;
    }

    return {
      drawingId: "00000000-0000-4000-8000-000000000000",
      title: "",
      version: null,
      defaultMode: localLaunch.mode,
      availability: {
        has2d: localLaunch.mode === "2d",
        has3d: localLaunch.mode === "3d",
      },
      metadata: {},
    };
  }, [localLaunch]);
  const localDetailMock = useMemo(
    () => (localBootstrap ? buildDrawingKnowledgeDetail(localBootstrap) : null),
    [localBootstrap],
  );
  const activeBootstrap = localBootstrap ?? bootstrap;
  const activeDetailMock = localDetailMock ?? detailMock;
  const has2d = activeBootstrap?.availability.has2d ?? false;
  const has3d = activeBootstrap?.availability.has3d ?? false;

  function openKnowledgePage(page: KnowledgePageKey, openDetail = false, entityId?: string, entityDrawingId?: string) {
    setActivePage(page);
    setDetailPage(openDetail && (page === "product" || page === "part") ? page : null);
    setSelectedEntity(
      openDetail && (page === "product" || page === "part") && entityId && entityDrawingId
        ? { entityId, drawingId: entityDrawingId }
        : null,
    );
  }

  function navigateFromEntity(page: KnowledgePageKey, entityId?: string, entityDrawingId?: string) {
    if (page === "drawing" && entityDrawingId) {
      const drawingUrl = new URL("/", window.location.origin);
      drawingUrl.searchParams.set("drawingId", entityDrawingId);
      window.location.assign(drawingUrl.toString());
      return;
    }
    openKnowledgePage(page, page === "product" || page === "part", entityId, entityDrawingId);
  }

  const pageTitle = detailPage ? pageTitles[detailPage].replace("一覧", "詳細") : pageTitles[activePage];

  useEffect(() => {
    if (!activeBootstrap) {
      return;
    }
    setMode(resolveInitialMode(activeBootstrap, requestedMode));
  }, [activeBootstrap, requestedMode]);

  const pageContent = (() => {
    if (activePage !== "drawing") {
      if (activePage === "product" || activePage === "part") {
        if (detailPage === activePage) {
          return (
            <IcadEntityDetailPage
              entityId={selectedEntity?.entityId ?? null}
              drawingId={selectedEntity?.drawingId ?? null}
              onNavigate={navigateFromEntity}
            />
          );
        }

        return (
          <IcadEntityListPage
            targetKey={activePage}
            onOpenDetail={(entityId, entityDrawingId) => {
              setSelectedEntity({ entityId, drawingId: entityDrawingId });
              setDetailPage(activePage);
            }}
          />
        );
      }

      if (activePage === "system") {
        return <TagAutomationSettingsPage />;
      }

      return <PlaceholderKnowledgePage title={pageTitles[activePage]} />;
    }

    if (!drawingId && localLaunch && localBootstrap && localDetailMock) {
      return (
        <Suspense
          fallback={
            <section className="panel viewer-page">
              <div className="panel-section">Loading viewer...</div>
            </section>
          }
        >
          {localLaunch.mode === "2d" ? (
            <Viewer2DPage
              drawingId={localBootstrap.drawingId}
              bootstrap={localBootstrap}
              knowledgeMock={localDetailMock}
              debugInputsEnabled={false}
              autoOpenDrawingSource={false}
              initialLocalFile={localLaunch.file}
            />
          ) : (
            <Viewer3DPage
              drawingId={localBootstrap.drawingId}
              bootstrap={localBootstrap}
              knowledgeMock={localDetailMock}
              debugInputsEnabled={false}
              autoOpenDrawingSource={false}
              initialLocalFile={localLaunch.file}
            />
          )}
        </Suspense>
      );
    }

    if (!drawingId) {
      if (showIcadExtractionReview) {
        return (
          <IcadExtractionReviewPage
            file={icadExtractionFile}
            onBack={() => {
              setShowIcadExtractionReview(false);
            }}
          />
        );
      }

      return (
        <DrawingEntryPanel
          debugInputsEnabled={debugInputsEnabled}
          initialValue={window.location.href}
          onIcadMetadataLaunch={(file) => {
            setIcadExtractionFile(file);
            setShowIcadExtractionReview(true);
            openKnowledgePage("drawing");
          }}
          onLocalFileLaunch={(nextMode, file) => {
            setLocalLaunch({ mode: nextMode, file });
            setMode(nextMode);
          }}
        />
      );
    }

    if (loading) {
      return (
        <section className="panel viewer-page">
          <div className="panel-section workspace-message">
            <h2>図面情報を読み込んでいます</h2>
            <p>drawingId から PDM の図面詳細を解決しています。</p>
          </div>
        </section>
      );
    }

    if (error || !bootstrap || !detailMock) {
      return (
        <section className="panel viewer-page">
          <div className="panel-section workspace-message error-panel">
            <h2>図面情報を取得できませんでした</h2>
            <p>{error ?? "drawingId に対応する図面情報が見つかりません。"}</p>
          </div>
        </section>
      );
    }

    return (
      <Suspense
        fallback={
          <section className="panel viewer-page">
            <div className="panel-section">Loading viewer...</div>
          </section>
        }
      >
        {mode === "2d" ? (
          <Viewer2DPage
            drawingId={drawingId}
            bootstrap={bootstrap}
            knowledgeMock={detailMock}
            debugInputsEnabled={debugInputsEnabled}
          />
        ) : (
          <Viewer3DPage
            drawingId={drawingId}
            bootstrap={bootstrap}
            knowledgeMock={detailMock}
            debugInputsEnabled={debugInputsEnabled}
          />
        )}
      </Suspense>
    );
  })();

  return (
    <div className="app-shell">
      <div className="app-frame">
        <aside className="app-sidebar">
          <div className="sidebar-brand">
            <div className="sidebar-logo" aria-hidden="true">
              N
            </div>
            <div className="sidebar-brand-copy">
              <strong>PDM＋ナレッジ管理</strong>
            </div>
          </div>

          <nav className="sidebar-nav" aria-label="primary">
            {navigationGroups.map((group) => (
              <section key={group.title} className="sidebar-group">
                <h2 className="sidebar-group-title">{group.title}</h2>
                <div className="sidebar-links">
                  {group.items.map((item) => (
                    <button
                      key={item.key}
                      className={item.key === activePage ? "sidebar-link active" : "sidebar-link"}
                      type="button"
                      onClick={() => openKnowledgePage(item.key)}
                    >
                      <span className="sidebar-link-marker" aria-hidden="true" />
                      <span>{item.label}</span>
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </nav>

          <div className="sidebar-user">
            <span className="sidebar-link-marker" aria-hidden="true" />
            <span>創屋　太郎</span>
          </div>
        </aside>

        <div className="app-main">
          <header className="topbar">
            <div className="topbar-actions">
              <LicensePanel />
              <button className="ai-button" type="button">
                AI検索
              </button>
            </div>
          </header>

          <main className="content-shell">
            <div className="page-tools">
              <button
                className="back-link"
                type="button"
                onClick={() => {
                  if (detailPage) {
                    setDetailPage(null);
                    setSelectedEntity(null);
                    return;
                  }
                  if (!drawingId && localLaunch) {
                    setLocalLaunch(null);
                    return;
                  }
                  openKnowledgePage("drawing");
                }}
              >
                ← 戻る
              </button>
              {activePage === "drawing" ? (
                <div className="mode-switch" role="radiogroup" aria-label="viewer mode">
                  {(["2d", "3d"] as ViewMode[]).map((tabMode) => (
                    <label
                      key={tabMode}
                      className={tabMode === mode ? "mode-option active" : "mode-option"}
                    >
                      <input
                        className="mode-option-input"
                        type="radio"
                        name="viewer-mode"
                        checked={tabMode === mode}
                        onChange={() => setMode(tabMode)}
                        disabled={tabMode === "2d" ? !has2d : !has3d}
                      />
                      <span className="mode-option-indicator" aria-hidden="true" />
                      <span>{tabMode === "2d" ? "2D" : "3D"}</span>
                    </label>
                  ))}
                </div>
              ) : null}
            </div>

            <div className="page-heading">
              <h1>{pageTitle}</h1>
            </div>

            <div className="workspace">
              {pageContent}
              {activePage === "drawing" && activeDetailMock ? (
                <DrawingSupplementPanels detail={activeDetailMock} />
              ) : null}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
