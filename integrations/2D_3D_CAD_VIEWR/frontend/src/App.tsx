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
type KnowledgePageKey =
  | "project"
  | "product"
  | "part"
  | "drawing"
  | "document"
  | "search"
  | "chat"
  | "similar"
  | "customer"
  | "notice"
  | "master"
  | "system";
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
  product: "製品・装置・ユニット詳細",
  part: "部品詳細",
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

type KnowledgeField = {
  label: string;
  value: string;
};

type KnowledgeRelatedItem = {
  title: string;
  subtitle: string;
  description: string;
  chips: string[];
  targetPage?: KnowledgePageKey;
};

type KnowledgeRelatedSection = {
  label: string;
  items: KnowledgeRelatedItem[];
};

type KnowledgeEntityRecord = {
  pageKey: "project" | "product" | "part";
  title: string;
  fields: KnowledgeField[];
  tags: string[];
  attributes: KnowledgeField[];
  relatedSections: KnowledgeRelatedSection[];
};

const knowledgeEntityRecords: Record<"project" | "product" | "part", KnowledgeEntityRecord> = {
  project: {
    pageKey: "project",
    title: "PRJ-OP30 ライン改善",
    fields: [
      { label: "プロジェクト番号", value: "PRJ-OP30-2026" },
      { label: "ステータス", value: "進行中" },
      { label: "担当者", value: "設計 二階堂" },
      { label: "関連客先", value: "澁谷工業" },
    ],
    tags: [],
    attributes: [
      { label: "案件分類", value: "工程改善" },
      { label: "登録元", value: "ナレッジシステム画面確認に基づくモック" },
    ],
    relatedSections: [
      {
        label: "製品・装置・ユニット",
        items: [
          {
            title: "OP30 カセット",
            subtitle: "製品・装置・ユニット",
            description: "プロジェクトに紐づく装置・ユニットの詳細へ接続します。",
            chips: ["製品・装置・ユニット", "進行中"],
            targetPage: "product",
          },
        ],
      },
      {
        label: "図面",
        items: [
          {
            title: "TR1D9K99027",
            subtitle: "図面管理",
            description: "2D画像図、3D中間ファイル、図面タグを扱う図面管理へ接続します。",
            chips: ["図面", "2D/3D"],
            targetPage: "drawing",
          },
        ],
      },
    ],
  },
  product: {
    pageKey: "product",
    title: "OP30 カセット",
    fields: [
      { label: "名称", value: "OP30 カセット" },
      { label: "管理番号", value: "UNIT-OP30-0001" },
      { label: "区分", value: "製品・装置・ユニット" },
      { label: "担当者", value: "設計 二階堂" },
      { label: "ステータス", value: "現行" },
      { label: "関連プロジェクト", value: "PRJ-OP30 ライン改善" },
    ],
    tags: ["OP30", "カセット", "ユニット", "標準", "工程改善"],
    attributes: [
      { label: "PRFX", value: "TR1D9" },
      { label: "ユニット番号", value: "OP30" },
      { label: "客先", value: "澁谷工業" },
      { label: "抽出元候補", value: "3Dトップ任意情報 / 2D図枠 / 保存フォルダ" },
    ],
    relatedSections: [
      {
        label: "親製品・装置・ユニット",
        items: [
          {
            title: "包装ライン本体",
            subtitle: "上位ユニット",
            description: "本家ナレッジシステムの親ユニットタブに相当する紐づきです。",
            chips: ["親ユニット"],
          },
        ],
      },
      {
        label: "部品",
        items: [
          {
            title: "TR1D9K99027 ブラケット",
            subtitle: "部品詳細",
            description: "部品詳細ページへ接続し、材質・表面処理・重量・タグを確認します。",
            chips: ["部品", "材質"],
            targetPage: "part",
          },
        ],
      },
      {
        label: "図面",
        items: [
          {
            title: "TR1D9K99027",
            subtitle: "図面管理",
            description: "2D画像図と3D中間ファイルのビューワー、図面タグ表示へ接続します。",
            chips: ["図面", "2D/3D"],
            targetPage: "drawing",
          },
        ],
      },
    ],
  },
  part: {
    pageKey: "part",
    title: "TR1D9K99027 ブラケット",
    fields: [
      { label: "部品番号", value: "TR1D9K99027" },
      { label: "部品名", value: "ブラケット" },
      { label: "材質", value: "SS400" },
      { label: "表面処理", value: "黒染め" },
      { label: "重量", value: "0.42 kg" },
      { label: "関連ユニット", value: "OP30 カセット" },
    ],
    tags: ["ブラケット", "SS400", "黒染め", "購入/製作判定要確認"],
    attributes: [
      { label: "PRFX", value: "TR1D9K" },
      { label: "材質", value: "SS400" },
      { label: "表面処理", value: "黒染め" },
      { label: "重量", value: "2D図枠/3D重量情報の照合対象" },
      { label: "抽出元候補", value: "2D図枠 / 2D注記 / 3D材質 / パーツ付加情報" },
    ],
    relatedSections: [
      {
        label: "製品・装置・ユニット",
        items: [
          {
            title: "OP30 カセット",
            subtitle: "製品・装置・ユニット詳細",
            description: "部品が属する製品・装置・ユニットへ接続します。",
            chips: ["ユニット", "親"],
            targetPage: "product",
          },
        ],
      },
      {
        label: "図面",
        items: [
          {
            title: "TR1D9K99027",
            subtitle: "図面管理",
            description: "図面管理で2D画像図、3D中間ファイル、図面タグを確認します。",
            chips: ["図面", "照合"],
            targetPage: "drawing",
          },
        ],
      },
      {
        label: "文書",
        items: [
          {
            title: "加工・表面処理指示",
            subtitle: "文書管理",
            description: "部品属性と照合する文書情報の接続先です。",
            chips: ["文書", "表面処理"],
            targetPage: "document",
          },
        ],
      },
    ],
  },
};

function RelatedCard({
  item,
  sectionLabel,
  onNavigate,
}: {
  item: KnowledgeRelatedItem;
  sectionLabel: string;
  onNavigate: (page: KnowledgePageKey) => void;
}) {
  const content = (
    <>
      <div className="related-card-header">
        <div>
          <strong>{item.title}</strong>
          <p>{item.subtitle}</p>
        </div>
      </div>
      <p className="related-card-description">{item.description}</p>
      <div className="related-card-chips">
        {item.chips.map((chip) => (
          <span key={chip} className="related-chip">
            {chip}
          </span>
        ))}
      </div>
    </>
  );

  if (!item.targetPage) {
    return (
      <article className="related-card">
        {content}
      </article>
    );
  }

  return (
    <button
      className="related-card related-card-button"
      type="button"
      onClick={() => onNavigate(item.targetPage!)}
      aria-label={`${sectionLabel}: ${item.title} を開く`}
    >
      {content}
    </button>
  );
}

function EntityDetailPage({
  pageKey,
  onNavigate,
}: {
  pageKey: "project" | "product" | "part";
  onNavigate: (page: KnowledgePageKey) => void;
}) {
  const record = knowledgeEntityRecords[pageKey];

  return (
    <section className="panel viewer-page entity-page">
      <div className="panel-section knowledge-info-card">
        <h2>{record.title}</h2>
        <div className="detail-field-grid">
          {record.fields.map((field) => (
            <div key={field.label} className="detail-field">
              <span className="detail-field-label">{field.label}</span>
              <span className="detail-field-value">{field.value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="panel-section">
        <h2>タグ・属性</h2>
        <div className="tag-target-card">
          <div className="tag-chip-row">
            {record.tags.length > 0 ? (
              record.tags.map((tag) => (
                <span key={tag} className="tag-chip">
                  {tag}
                </span>
              ))
            ) : (
              <span className="tag-target-empty">タグなし</span>
            )}
          </div>
          <dl className="tag-attribute-list">
            {record.attributes.map((attribute) => (
              <div key={attribute.label}>
                <dt>{attribute.label}</dt>
                <dd>
                  <span className="attribute-value-preview">{attribute.value}</span>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      <div className="panel-section">
        <h2>紐づき</h2>
        <div className="knowledge-stack">
          {record.relatedSections.map((section) => (
            <section key={section.label} className="entity-related-section">
              <h3>{section.label}</h3>
              <div className="related-card-grid">
                {section.items.map((item) => (
                  <RelatedCard
                    key={`${section.label}-${item.title}`}
                    item={item}
                    sectionLabel={section.label}
                    onNavigate={onNavigate}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </section>
  );
}

function PlaceholderKnowledgePage({ title }: { title: string }) {
  return (
    <section className="panel viewer-page">
      <div className="panel-section workspace-message">
        <h2>{title}</h2>
        <p>現在の確認対象は図面、製品・装置・ユニット、部品です。</p>
      </div>
    </section>
  );
}

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
  const [activePage, setActivePage] = useState<KnowledgePageKey>("drawing");
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
    if (activePage !== "drawing") {
      if (activePage === "project" || activePage === "product" || activePage === "part") {
        return <EntityDetailPage pageKey={activePage} onNavigate={setActivePage} />;
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
                      key={item.key}
                      className={item.key === activePage ? "sidebar-link active" : "sidebar-link"}
                      type="button"
                      onClick={() => setActivePage(item.key)}
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
                  if (!drawingId && localLaunch) {
                    setLocalLaunch(null);
                    return;
                  }
                  window.history.back();
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
              <h1>{pageTitles[activePage]}</h1>
            </div>

            <div className="workspace">
              {pageContent}
              {activePage === "drawing" && activeDetailMock ? <DrawingSupplementPanels detail={activeDetailMock} /> : null}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
