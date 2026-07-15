import { useMemo, useState } from "react";

import type {
  KnowledgeEntityRecord,
  KnowledgeEntityRelatedItem,
  KnowledgeEntityTargetKey,
} from "../../shared/api/client";
import type { KnowledgePageKey } from "./types";
import { useKnowledgeEntityDetail, useKnowledgeEntityList } from "./useKnowledgeEntities";


function entityKindLabel(record: KnowledgeEntityRecord): string {
  if (record.entityKind === "assembly") {
    return "アセンブリ";
  }
  if (record.entityKind === "subassembly") {
    return "サブアセンブリ";
  }
  return "部品";
}


function attributeValue(record: KnowledgeEntityRecord, key: string): string {
  return record.attributes.find((attribute) => attribute.key === key)?.value ?? "-";
}


function materialValue(record: KnowledgeEntityRecord): string {
  return attributeValue(record, "materials");
}


function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}


function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}


function confidenceLabel(value: string): string {
  return ({ high: "高", medium: "中", low: "低" } as Record<string, string>)[value] ?? value;
}


function sourceLabel(value: string): string {
  return ({
    "3d_part_tree": "3D構成",
    "3d_part_material": "3D材質",
    "3d_part_extended_info": "パーツ付加情報",
    "composed_2d_3d": "2D/3D照合結果",
    "composed_metadata": "統合結果",
  } as Record<string, string>)[value] ?? value;
}


function historyActorLabel(value: string): string {
  if (!value || value === "api") {
    return "利用者";
  }
  if (value.includes("import_") || value.includes("_2026_") || value === "worker") {
    return "自動取得";
  }
  return value;
}


function historyActionLabel(action: string, mode: string): string {
  const label = ({ extraction: "属性・タグ更新", override: "手直し", requeue: "再抽出", review: "候補レビュー" } as Record<string, string>)[action] ?? action;
  return `${label} (${mode.toUpperCase()})`;
}


function reviewStatusLabel(record: KnowledgeEntityRecord): string {
  if (record.reviewStatus === "confirmed") {
    return "確認済み";
  }
  if (record.reviewStatus === "needs_correction") {
    return "要手直し";
  }
  return "確認待ち";
}


function historyReasonLabel(value: string): string {
  if (!value) {
    return "-";
  }
  if (value === "extractor result saved") {
    return "ICAD抽出結果を反映";
  }
  return value;
}


export function IcadEntityListPage({
  targetKey,
  onOpenDetail,
}: {
  targetKey: KnowledgeEntityTargetKey;
  onOpenDetail: (entityId: string, drawingId: string) => void;
}) {
  const [draftQuery, setDraftQuery] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 50;
  const { catalog, loading, error } = useKnowledgeEntityList(targetKey, query, page, pageSize);
  const listLabel = targetKey === "product" ? "製品・装置・ユニット" : "部品";

  return (
    <section className="knowledge-production-page entity-list-page">
      <div className="knowledge-page-action-row">
        <span />
        <button className="production-primary-button" type="button" disabled>
          新規登録
        </button>
      </div>

      <section className="production-section">
        <h2>検索条件</h2>
        <div className="production-section-divider" />
        <form
          className="production-search-grid"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(0);
            setQuery(draftQuery);
          }}
        >
          <label>
            <span>{targetKey === "product" ? "製品・装置・ユニット名" : "部品番号・部品名"}</span>
            <input
              type="search"
              value={draftQuery}
              onChange={(event) => setDraftQuery(event.target.value)}
            />
          </label>
          <label>
            <span>構成種別</span>
            <select defaultValue="">
              <option value="" />
              {targetKey === "product" ? (
                <>
                  <option>アセンブリ</option>
                  <option>サブアセンブリ</option>
                </>
              ) : (
                <option>部品</option>
              )}
            </select>
          </label>
          <label>
            <span>状態</span>
            <select defaultValue="">
              <option value="" />
              <option>抽出済み</option>
              <option>要レビュー</option>
            </select>
          </label>
          <div className="production-search-actions">
            <button
              className="production-secondary-button"
              type="button"
              onClick={() => {
                setDraftQuery("");
                setQuery("");
                setPage(0);
              }}
            >
              クリア
            </button>
            <button className="production-primary-button" type="submit">
              検索
            </button>
          </div>
        </form>
      </section>

      <section className="production-section">
        <h2>検索結果</h2>
        <div className="production-section-divider" />
        <div className="production-table-shell">
          <table className="production-table">
            <thead>
              <tr>
                <th />
                {targetKey === "product" ? (
                  <>
                    <th>製品・装置・ユニット名</th>
                    <th>構成種別</th>
                    <th>下位ユニット数</th>
                    <th>部品数</th>
                    <th>関連図面</th>
                    <th>状態</th>
                    <th>最終更新日</th>
                  </>
                ) : (
                  <>
                    <th>部品番号</th>
                    <th>部品名</th>
                    <th>材質</th>
                    <th>関連図面</th>
                    <th>状態</th>
                    <th>最終更新日</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={targetKey === "product" ? 8 : 7}>読み込んでいます。</td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={targetKey === "product" ? 8 : 7} className="error-text">{error}</td>
                </tr>
              ) : catalog?.items.length ? (
                catalog.items.map((record) => (
                  <tr
                    key={record.entityId}
                    className="production-clickable-row"
                    onClick={() => onOpenDetail(record.entityId, record.drawingId)}
                  >
                    <td />
                    {targetKey === "product" ? (
                      <>
                        <td>{record.name}</td>
                        <td>{entityKindLabel(record)}</td>
                        <td>{record.childAssemblyCount}</td>
                        <td>{record.descendantPartCount}</td>
                        <td>{record.drawingFilename}</td>
                        <td>{reviewStatusLabel(record)}</td>
                        <td>{formatDate(record.updatedAt)}</td>
                      </>
                    ) : (
                      <>
                        <td>{record.partNumber ?? "-"}</td>
                        <td>{record.name}</td>
                        <td>{materialValue(record)}</td>
                        <td>{record.drawingFilename}</td>
                        <td>{reviewStatusLabel(record)}</td>
                        <td>{formatDate(record.updatedAt)}</td>
                      </>
                    )}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={targetKey === "product" ? 8 : 7}>該当する{listLabel}はありません。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="production-pagination" aria-label="pagination">
          <button type="button" disabled={page === 0} onClick={() => setPage(0)}>«</button>
          <button type="button" disabled={page === 0} onClick={() => setPage((current) => Math.max(0, current - 1))}>‹</button>
          <button type="button" className="active">{page + 1}</button>
          <button
            type="button"
            disabled={!catalog || (page + 1) * pageSize >= catalog.totalCount}
            onClick={() => setPage((current) => current + 1)}
          >
            ›
          </button>
          <button
            type="button"
            disabled={!catalog || (page + 1) * pageSize >= catalog.totalCount}
            onClick={() => setPage(Math.max(0, Math.ceil((catalog?.totalCount ?? 1) / pageSize) - 1))}
          >
            »
          </button>
        </div>
      </section>
    </section>
  );
}


type RelatedSection = {
  label: string;
  items: KnowledgeEntityRelatedItem[];
  drawing?: { drawingId: string; filename: string };
};


function relatedSections(record: KnowledgeEntityRecord): RelatedSection[] {
  const related = record.relatedEntities ?? [];
  const parents = related.filter((item) => item.relationship === "parent");
  const childProducts = related.filter((item) => item.relationship === "child" && item.targetKey === "product");
  const childParts = related.filter((item) => item.relationship === "child" && item.targetKey === "part");
  const sections: RelatedSection[] = [];
  if (parents.length) {
    sections.push({ label: "親製品・装置・ユニット", items: parents });
  }
  if (childProducts.length) {
    sections.push({ label: "下位製品・装置・ユニット", items: childProducts });
  }
  if (childParts.length) {
    sections.push({ label: "部品", items: childParts });
  }
  if (record.relatedDrawing) {
    sections.push({ label: "図面", items: [], drawing: record.relatedDrawing });
  }
  return sections;
}


export function IcadEntityDetailPage({
  entityId,
  drawingId,
  onNavigate,
}: {
  entityId: string | null;
  drawingId: string | null;
  onNavigate: (page: KnowledgePageKey, entityId?: string, drawingId?: string) => void;
}) {
  const { record, loading, error } = useKnowledgeEntityDetail(entityId, drawingId);
  const sections = useMemo(() => (record ? relatedSections(record) : []), [record]);
  const [activeRelatedIndex, setActiveRelatedIndex] = useState(0);

  if (loading) {
    return <section className="production-section workspace-message">読み込んでいます。</section>;
  }
  if (error || !record) {
    return <section className="production-section workspace-message error-panel">{error ?? "詳細が見つかりません。"}</section>;
  }

  const activeSection = sections[Math.min(activeRelatedIndex, Math.max(sections.length - 1, 0))];
  const basicFields = record.targetKey === "product"
    ? [
        ["名称", record.name],
        ["構成種別", entityKindLabel(record)],
        ["構成パス", record.treePath.join(" > ")],
        ["関連図面", record.drawingFilename],
        ["下位ユニット数", String(record.childAssemblyCount)],
        ["末端部品数", String(record.descendantPartCount)],
      ]
    : [
        ["部品番号", record.partNumber ?? "-"],
        ["部品名", record.name],
        ["材質", materialValue(record)],
        ["構成パス", record.treePath.join(" > ")],
        ["関連図面", record.drawingFilename],
        ["コメント", record.comment ?? "-"],
      ];

  return (
    <section className="knowledge-production-page entity-page">
      <section className="production-section production-basic-section">
        <div className="production-section-header">
          <div className="production-section-title-row">
            <h2>基本情報</h2>
            <span className="production-version">ver.1</span>
            <button className="production-icon-button" type="button" aria-label="お気に入り">☆</button>
          </div>
          <div className="production-section-actions">
            <button className="production-icon-button" type="button" disabled>編集</button>
            <button className="production-icon-button" type="button" disabled>削除</button>
          </div>
        </div>
        <div className="production-section-divider" />
        <div className="production-detail-grid">
          {basicFields.map(([label, value]) => (
            <div key={label} className="production-detail-field">
              <span>{label}</span>
              <p>{value}</p>
            </div>
          ))}
        </div>
        <div className="production-attribute-block">
          <span>属性情報</span>
          <div className="production-table-shell">
            <table className="production-table entity-attribute-table">
              <thead>
                <tr>
                  <th>項目</th>
                  <th>値</th>
                  <th>信頼度</th>
                  <th>取得元</th>
                </tr>
              </thead>
              <tbody>
                {record.attributes.map((attribute) => (
                  <tr key={`${attribute.key}-${attribute.value}`}>
                    <th>{attribute.label}</th>
                    <td>{attribute.value}</td>
                    <td>{confidenceLabel(attribute.confidence)}</td>
                    <td>{sourceLabel(attribute.source)}</td>
                  </tr>
                ))}
                <tr>
                  <th>タグ</th>
                  <td colSpan={3}>{record.tags.length ? record.tags.map((tag) => tag.value).join(" / ") : "-"}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div className="production-detail-field">
          <span>状態</span>
          <p>{reviewStatusLabel(record)}</p>
        </div>
      </section>

      <section className="production-section production-related-section">
        <h2>関連情報</h2>
        <div className="production-section-divider" />
        <div className="production-tabs" role="tablist">
          {sections.map((section, index) => (
            <button
              key={section.label}
              className={index === activeRelatedIndex ? "active" : ""}
              type="button"
              role="tab"
              onClick={() => setActiveRelatedIndex(index)}
            >
              {section.label}
            </button>
          ))}
        </div>
        <div className="production-related-body">
          <div className="production-related-heading-row">
            <p>{activeSection?.label ?? "関連"}一覧</p>
          </div>
          <div className="production-table-shell">
            <table className="production-table">
              <thead>
                <tr>
                  <th>{activeSection?.label ?? "関連"}名</th>
                  <th>種別</th>
                  <th>関連</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {activeSection?.drawing ? (
                  <tr
                    className="production-clickable-row"
                    onClick={() => onNavigate("drawing", undefined, activeSection.drawing?.drawingId)}
                  >
                    <td>{activeSection.drawing.filename}</td>
                    <td>図面</td>
                    <td>抽出元</td>
                    <td>詳細</td>
                  </tr>
                ) : activeSection?.items.length ? (
                  activeSection.items.map((item) => (
                    <tr
                      key={item.entityId}
                      className="production-clickable-row"
                      onClick={() => onNavigate(item.targetKey, item.entityId, record.drawingId)}
                    >
                      <td>{item.name}</td>
                      <td>{item.entityKind === "part" ? "部品" : item.entityKind === "assembly" ? "アセンブリ" : "サブアセンブリ"}</td>
                      <td>{item.relationship === "parent" ? "親" : "子"}</td>
                      <td>詳細</td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={4}>関連情報がありません。</td></tr>
                )}
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
              <th>変更日時</th>
              <th>変更者</th>
              <th>操作</th>
              <th>理由</th>
            </tr>
          </thead>
          <tbody>
            {record.history.length ? (
              record.history.slice(0, 10).map((history, index) => (
                <tr key={`${history.executedAt}-${index}`}>
                  <td>{formatDateTime(history.executedAt)}</td>
                  <td>{historyActorLabel(history.executedBy)}</td>
                  <td>{historyActionLabel(history.action, history.mode)}</td>
                  <td>{historyReasonLabel(history.reason)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td>{formatDateTime(record.updatedAt)}</td>
                <td>ICAD抽出</td>
                <td>抽出結果反映</td>
                <td>-</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </section>
  );
}
