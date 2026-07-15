import { Suspense, lazy, useEffect, useMemo, useState } from "react";

import { DrawingSupplementPanels } from "./shared/components/DrawingSupplementPanels";
import { DrawingEntryPanel } from "./shared/components/DrawingEntryPanel";
import { LicensePanel } from "./shared/components/LicensePanel";
import { resolveDrawingIdFromLocation, resolveViewerModeFromSearch } from "./shared/drawingRoute";
import { isViewerDebugInputsEnabled } from "./shared/env";
import { useDrawingBootstrap } from "./shared/hooks/useDrawingBootstrap";
import { buildDrawingKnowledgeMock } from "./shared/mock/drawingKnowledge";
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
type NavigationGroup = {
  title: string;
  items: string[];
};

const navigationGroups: NavigationGroup[] = [
  {
    title: "メイン",
    items: ["プロジェクト", "製品", "部品", "図面管理", "文書管理"],
  },
  {
    title: "検索",
    items: ["統合検索", "チャット", "類似検索"],
  },
  {
    title: "営業",
    items: ["顧客管理"],
  },
  {
    title: "管理",
    items: ["お知らせ管理", "マスタ設定", "システム設定"],
  },
];

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
  const detailMock = useMemo(
    () => (bootstrap ? buildDrawingKnowledgeMock(bootstrap) : null),
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
    () => (localBootstrap ? buildDrawingKnowledgeMock(localBootstrap) : null),
    [localBootstrap],
  );
  const activeBootstrap = localBootstrap ?? bootstrap;
  const activeDetailMock = localDetailMock ?? detailMock;
  const has2d = activeBootstrap?.availability.has2d ?? false;
  const has3d = activeBootstrap?.availability.has3d ?? false;

  useEffect(() => {
    if (!activeBootstrap) {
      return;
    }
    setMode(resolveInitialMode(activeBootstrap, requestedMode));
  }, [activeBootstrap, requestedMode]);

  const pageContent = (() => {
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
      return (
        <DrawingEntryPanel
          debugInputsEnabled={debugInputsEnabled}
          initialValue={window.location.href}
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
                      key={item}
                      className={item === "図面管理" ? "sidebar-link active" : "sidebar-link"}
                      type="button"
                    >
                      <span className="sidebar-link-marker" aria-hidden="true" />
                      <span>{item}</span>
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
                  if (!drawingId && localLaunch) {
                    setLocalLaunch(null);
                    return;
                  }
                  window.history.back();
                }}
              >
                ← 戻る
              </button>
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
            </div>

            <div className="page-heading">
              <h1>図面詳細</h1>
            </div>

            <div className="workspace">
              {pageContent}
              {activeDetailMock ? <DrawingSupplementPanels detail={activeDetailMock} /> : null}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
