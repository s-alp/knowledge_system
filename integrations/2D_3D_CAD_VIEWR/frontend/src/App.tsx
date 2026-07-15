import { Suspense, lazy, useEffect, useMemo, useState } from "react";

import { DrawingSupplementPanels } from "./shared/components/DrawingSupplementPanels";
import { DrawingEntryPanel } from "./shared/components/DrawingEntryPanel";
import { LicensePanel } from "./shared/components/LicensePanel";
import { resolveDrawingIdFromLocation, resolveViewerModeFromSearch } from "./shared/drawingRoute";
import { isViewerDebugInputsEnabled } from "./shared/env";
import { useDrawingBootstrap } from "./shared/hooks/useDrawingBootstrap";
import { buildDrawingKnowledgeMock, type DrawingKnowledgeMock, type DrawingTagAttributeTarget } from "./shared/mock/drawingKnowledge";
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

type EntityPageKey = "project" | "product" | "part";
type DetailPageKey = EntityPageKey;

const entityTargetAliases: Record<EntityPageKey, string[]> = {
  project: ["project", "projects"],
  product: [
    "product",
    "products",
    "product_unit",
    "product_units",
    "equipment",
    "unit",
    "units",
    "device",
    "devices",
  ],
  part: ["part", "parts", "component", "components"],
};

function normalizeEntityTargetKey(value: string): string {
  return value.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function isTargetLabelForPage(label: string, pageKey: EntityPageKey): boolean {
  if (pageKey === "product") {
    return label.includes("製品") || label.includes("装置") || label.includes("ユニット");
  }
  if (pageKey === "part") {
    return label.includes("部品");
  }
  return label.includes("プロジェクト");
}

function findEntityTagTarget(
  detail: DrawingKnowledgeMock | null | undefined,
  pageKey: EntityPageKey,
): DrawingTagAttributeTarget | null {
  const aliases = new Set(entityTargetAliases[pageKey].map(normalizeEntityTargetKey));

  return (
    detail?.tagAttributeTargets.find((target) => {
      const targetKey = normalizeEntityTargetKey(target.targetKey);
      if (aliases.has(targetKey)) {
        return true;
      }

      return isTargetLabelForPage(target.label, pageKey);
    }) ?? null
  );
}

function buildEntityTags(record: KnowledgeEntityRecord, target: DrawingTagAttributeTarget | null): string[] {
  return target?.tags.length ? target.tags : record.tags;
}

function buildEntityAttributes(
  record: KnowledgeEntityRecord,
  target: DrawingTagAttributeTarget | null,
): KnowledgeField[] {
  if (!target?.attributes.length) {
    return record.attributes;
  }

  return target.attributes.map((attribute, index) => ({
    label: attribute.name !== "-" ? attribute.name : `属性${index + 1}`,
    value: attribute.value,
  }));
}

function findFieldValue(record: KnowledgeEntityRecord, label: string): string {
  return record.fields.find((field) => field.label === label)?.value ?? "-";
}

function buildEntitySearchText(record: KnowledgeEntityRecord, tags: string[], attributes: KnowledgeField[]): string {
  return [
    record.title,
    ...record.fields.map((field) => `${field.label} ${field.value}`),
    ...tags,
    ...attributes.map((attribute) => `${attribute.label} ${attribute.value}`),
  ]
    .join(" ")
    .toLowerCase();
}

const knowledgeEntityRecords: Record<EntityPageKey, KnowledgeEntityRecord> = {
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
      { label: "情報源", value: "ICAD抽出・ナレッジ連携候補" },
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

function EntityListPage({
  pageKey,
  detail,
  onOpenDetail,
}: {
  pageKey: "product" | "part";
  detail: DrawingKnowledgeMock | null;
  onOpenDetail: () => void;
}) {
  const [query, setQuery] = useState("");
  const record = knowledgeEntityRecords[pageKey];
  const tagTarget = findEntityTagTarget(detail, pageKey);
  const tags = buildEntityTags(record, tagTarget);
  const attributes = buildEntityAttributes(record, tagTarget);
  const searchText = buildEntitySearchText(record, tags, attributes);
  const shouldShowRow = query.trim().length === 0 || searchText.includes(query.trim().toLowerCase());
  const listLabel = pageKey === "product" ? "製品・装置・ユニット" : "部品";

  return (
    <section className="knowledge-production-page entity-list-page">
      <div className="knowledge-page-action-row">
        <span />
        <button className="production-primary-button" type="button">
          新規登録
        </button>
      </div>

      <section className="production-section">
        <h2>検索条件</h2>
        <div className="production-section-divider" />
        <div className="production-search-grid">
          {pageKey === "product" ? (
            <>
              <label>
                <span>製品・装置・ユニット名</span>
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              <label>
                <span>ステータス</span>
                <select defaultValue="">
                  <option value="" />
                  <option>設計中</option>
                  <option>現行</option>
                  <option>完了</option>
                </select>
              </label>
              <label>
                <span>カテゴリ</span>
                <select defaultValue="">
                  <option value="" />
                  <option>加工機</option>
                  <option>搬送装置</option>
                  <option>治具</option>
                </select>
              </label>
              <label>
                <span>種別</span>
                <select defaultValue="">
                  <option value="" />
                  <option>特注品</option>
                  <option>標準品</option>
                </select>
              </label>
              <label>
                <span>フェーズ</span>
                <select defaultValue="">
                  <option value="" />
                  <option>設計</option>
                  <option>製造・組立</option>
                  <option>検査</option>
                </select>
              </label>
            </>
          ) : (
            <>
              <label>
                <span>部品番号</span>
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              <label>
                <span>部品名</span>
                <input type="search" />
              </label>
              <label>
                <span>カテゴリ</span>
                <select defaultValue="">
                  <option value="" />
                  <option>ブラケット</option>
                  <option>ワッシャー</option>
                  <option>基板</option>
                </select>
              </label>
              <label>
                <span>ステータス</span>
                <select defaultValue="">
                  <option value="" />
                  <option>設計中</option>
                  <option>使用中</option>
                  <option>量産</option>
                </select>
              </label>
            </>
          )}
          <div className="production-search-actions">
            <button className="production-secondary-button" type="button">
              クリア
            </button>
            <button className="production-primary-button" type="button">
              検索
            </button>
            <label className="production-favorite-filter">
              <input type="checkbox" />
              <span>お気に入りのみ</span>
            </label>
          </div>
        </div>
      </section>

      <section className="production-section">
        <h2>検索結果</h2>
        <div className="production-section-divider" />
        <div className="production-table-shell">
          <table className="production-table">
            <thead>
              <tr>
                {pageKey === "product" ? (
                  <>
                    <th />
                    <th>製品・装置・ユニット名</th>
                    <th>カテゴリ</th>
                    <th>種別</th>
                    <th>フェーズ</th>
                    <th>プロジェクト数</th>
                    <th>下位製品・装置・ユニット数</th>
                    <th>上位製品・装置・ユニット数</th>
                    <th>部品数</th>
                    <th>ステータス</th>
                    <th>担当者</th>
                    <th>最終更新日</th>
                  </>
                ) : (
                  <>
                    <th />
                    <th>部品番号</th>
                    <th>部品名</th>
                    <th>カテゴリ</th>
                    <th>ステータス</th>
                    <th>担当者</th>
                    <th>最終更新日</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {shouldShowRow ? (
                <tr onClick={onOpenDetail} className="production-clickable-row">
                  {pageKey === "product" ? (
                    <>
                      <td />
                      <td>{findFieldValue(record, "名称")}</td>
                      <td>{findFieldValue(record, "客先") !== "-" ? findFieldValue(record, "客先") : "加工機"}</td>
                      <td>特注品</td>
                      <td>設計</td>
                      <td>1</td>
                      <td>0</td>
                      <td>0</td>
                      <td>1</td>
                      <td>{findFieldValue(record, "ステータス")}</td>
                      <td>{findFieldValue(record, "担当者")}</td>
                      <td>2026/7/15</td>
                    </>
                  ) : (
                    <>
                      <td />
                      <td>{findFieldValue(record, "部品番号")}</td>
                      <td>{findFieldValue(record, "部品名")}</td>
                      <td>ブラケット</td>
                      <td>{findFieldValue(record, "ステータス") !== "-" ? findFieldValue(record, "ステータス") : "使用中"}</td>
                      <td>設計 二階堂</td>
                      <td>2026/7/15</td>
                    </>
                  )}
                </tr>
              ) : (
                <tr>
                  <td colSpan={pageKey === "product" ? 12 : 7}>該当する{listLabel}はありません。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="production-pagination" aria-label="pagination">
          <button type="button" disabled>
            «
          </button>
          <button type="button" disabled>
            ‹
          </button>
          <button type="button" className="active">
            1
          </button>
          <button type="button" disabled>
            ›
          </button>
          <button type="button" disabled>
            »
          </button>
        </div>
      </section>
    </section>
  );
}

function EntityDetailPage({
  pageKey,
  detail,
  onNavigate,
}: {
  pageKey: EntityPageKey;
  detail: DrawingKnowledgeMock | null;
  onNavigate: (page: KnowledgePageKey) => void;
}) {
  const record = knowledgeEntityRecords[pageKey];
  const tagTarget = findEntityTagTarget(detail, pageKey);
  const tags = buildEntityTags(record, tagTarget);
  const attributes = buildEntityAttributes(record, tagTarget);
  const attributeRows = [
    ...attributes,
    ...(tags.length > 0 ? [{ label: "タグ候補", value: tags.join(" / ") }] : []),
  ];
  const primaryRelatedSection = record.relatedSections[0];

  return (
    <section className="knowledge-production-page entity-page">
      <section className="production-section production-basic-section">
        <div className="production-section-header">
          <div className="production-section-title-row">
            <h2>基本情報</h2>
            <span className="production-version">ver.1</span>
            <button className="production-icon-button" type="button" aria-label="お気に入り">
              ☆
            </button>
          </div>
          <div className="production-section-actions">
            <button className="production-icon-button" type="button" aria-label="編集">
              編集
            </button>
            <button className="production-icon-button" type="button" aria-label="削除">
              削除
            </button>
          </div>
        </div>
        <div className="production-section-divider" />
        <div className="production-detail-grid">
          {record.fields.map((field) => (
            <div key={field.label} className="production-detail-field">
              <span>{field.label}</span>
              <p>{field.value}</p>
            </div>
          ))}
        </div>
        <div className="production-attribute-block">
          <span>属性情報</span>
          <div className="production-table-shell">
            <table className="production-table">
              <tbody>
                {attributeRows.length > 0 ? (
                  attributeRows.map((attribute) => (
                    <tr key={`${attribute.label}-${attribute.value}`}>
                      <th>{attribute.label}</th>
                      <td>{attribute.value}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td>属性情報がありません。</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="production-detail-field">
          <span>備考</span>
          <p>{tagTarget?.notes.length ? tagTarget.notes.join(" / ") : "-"}</p>
        </div>
      </section>

      <section className="production-section production-related-section">
        <h2>関連情報</h2>
        <div className="production-section-divider" />
        <div className="production-tabs" role="tablist">
          {record.relatedSections.map((section, index) => (
            <button key={section.label} className={index === 0 ? "active" : ""} type="button" role="tab">
              {section.label}
            </button>
          ))}
        </div>
        <div className="production-related-body">
          <div className="production-related-heading-row">
            <p>{primaryRelatedSection?.label ?? "関連"}一覧</p>
            <button className="production-secondary-button" type="button">
              {primaryRelatedSection?.label ?? "関連"}を紐づけ
            </button>
          </div>
          <div className="production-table-shell">
            <table className="production-table">
              <thead>
                <tr>
                  <th>{primaryRelatedSection?.label ?? "関連"}名</th>
                  <th>種別</th>
                  <th>担当者</th>
                  <th>件数</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {primaryRelatedSection?.items.map((item) => (
                  <tr
                    key={item.title}
                    onClick={() => {
                      if (item.targetPage) {
                        onNavigate(item.targetPage);
                      }
                    }}
                    className={item.targetPage ? "production-clickable-row" : undefined}
                  >
                    <td>{item.title}</td>
                    <td>{item.chips[0] ?? item.subtitle}</td>
                    <td>-</td>
                    <td>1</td>
                    <td>{item.targetPage ? "詳細" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="production-section production-history-section">
        <h2>変更履歴</h2>
        <div className="production-section-divider" />
        <table className="production-table">
          <thead>
            <tr>
              <th>バージョン</th>
              <th>変更日時</th>
              <th>変更者</th>
              <th>操作</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>1</td>
              <td>2026/7/15 00:00:00</td>
              <td>アルパイン 設計事務所</td>
              <td>作成</td>
              <td />
            </tr>
          </tbody>
        </table>
      </section>
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
  const [detailPage, setDetailPage] = useState<DetailPageKey | null>(null);
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

  function openKnowledgePage(page: KnowledgePageKey, openDetail = false) {
    setActivePage(page);
    setDetailPage(openDetail && (page === "project" || page === "product" || page === "part") ? page : null);
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
            <EntityDetailPage
              pageKey={activePage}
              detail={activeDetailMock}
              onNavigate={(nextPage) => openKnowledgePage(nextPage, true)}
            />
          );
        }

        return (
          <EntityListPage
            pageKey={activePage}
            detail={activeDetailMock}
            onOpenDetail={() => setDetailPage(activePage)}
          />
        );
      }

      if (activePage === "project") {
        return (
          <EntityDetailPage
            pageKey={activePage}
            detail={activeDetailMock}
            onNavigate={(nextPage) => openKnowledgePage(nextPage, true)}
          />
        );
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
                    return;
                  }
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
