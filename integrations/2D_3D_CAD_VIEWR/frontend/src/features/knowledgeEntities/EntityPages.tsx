import { useState } from "react";

import type { DrawingKnowledgeMock, DrawingTagAttributeTarget } from "../../shared/mock/drawingKnowledge";
import type { KnowledgePageKey } from "./types";

type EntityField = {
  label: string;
  value: string;
};

type EntityRelatedItem = {
  title: string;
  subtitle: string;
  description: string;
  chips: string[];
  targetPage?: KnowledgePageKey;
};

type EntityRelatedSection = {
  label: string;
  items: EntityRelatedItem[];
};

type EntityPageKey = "project" | "product" | "part";
export type DetailPageKey = EntityPageKey;

type EntityPageRecord = {
  pageKey: EntityPageKey;
  title: string;
  fields: EntityField[];
  tags: string[];
  attributes: EntityField[];
  relatedSections: EntityRelatedSection[];
};

// ICAD抽出やタグ生成はバックエンド側の責務です。
// このfeatureは生成済み候補を創屋ナレッジ風の対象物画面へ表示します。
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

const entityPageRecords: Record<EntityPageKey, EntityPageRecord> = {
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

function findTagAttributeTargetForEntity(
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

function buildEntityTags(record: EntityPageRecord, target: DrawingTagAttributeTarget | null): string[] {
  return target?.tags.length ? target.tags : record.tags;
}

function buildEntityAttributes(
  record: EntityPageRecord,
  target: DrawingTagAttributeTarget | null,
): EntityField[] {
  if (!target?.attributes.length) {
    return record.attributes;
  }

  return target.attributes.map((attribute, index) => ({
    label: attribute.name !== "-" ? attribute.name : `属性${index + 1}`,
    value: attribute.value,
  }));
}

function findFieldValue(record: EntityPageRecord, label: string): string {
  return record.fields.find((field) => field.label === label)?.value ?? "-";
}

function buildEntitySearchText(record: EntityPageRecord, tags: string[], attributes: EntityField[]): string {
  return [
    record.title,
    ...record.fields.map((field) => `${field.label} ${field.value}`),
    ...tags,
    ...attributes.map((attribute) => `${attribute.label} ${attribute.value}`),
  ]
    .join(" ")
    .toLowerCase();
}

export function EntityListPage({
  pageKey,
  detail,
  onOpenDetail,
}: {
  pageKey: "product" | "part";
  detail: DrawingKnowledgeMock | null;
  onOpenDetail: () => void;
}) {
  const [query, setQuery] = useState("");
  const record = entityPageRecords[pageKey];
  const tagTarget = findTagAttributeTargetForEntity(detail, pageKey);
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

export function EntityDetailPage({
  pageKey,
  detail,
  onNavigate,
}: {
  pageKey: EntityPageKey;
  detail: DrawingKnowledgeMock | null;
  onNavigate: (page: KnowledgePageKey) => void;
}) {
  const record = entityPageRecords[pageKey];
  const tagTarget = findTagAttributeTargetForEntity(detail, pageKey);
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

export function PlaceholderKnowledgePage({ title }: { title: string }) {
  return (
    <section className="panel viewer-page">
      <div className="panel-section workspace-message">
        <h2>{title}</h2>
        <p>現在の確認対象は図面、製品・装置・ユニット、部品です。</p>
      </div>
    </section>
  );
}
