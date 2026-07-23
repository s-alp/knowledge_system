import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  IconLink,
  IconPencil,
  IconStar,
  IconTrash,
  IconUnlink,
  IconX,
} from "@tabler/icons-react";

import {
  applyDrawingMetadataOverrides,
  getDrawingOptions,
  type DrawingOption,
  type KnowledgeEntityKind,
  type KnowledgeEntityRecord,
  type KnowledgeEntityRelatedItem,
  type KnowledgeEntityTargetKey,
} from "../../shared/api/client";
import type { KnowledgePageKey } from "./types";
import { useKnowledgeEntityDetail, useKnowledgeEntityList } from "./useKnowledgeEntities";


function entityKindLabel(record: KnowledgeEntityRecord): string {
  if (record.entityKind === "assembly") return "アセンブリ";
  if (record.entityKind === "subassembly") return "サブアセンブリ";
  return "部品";
}


function attributeValue(record: KnowledgeEntityRecord, key: string): string {
  return record.attributes.find((attribute) => attribute.key === key)?.value ?? "-";
}


function businessValue(record: KnowledgeEntityRecord, key: string): string {
  return record.businessFields?.[key]?.trim() || "-";
}


function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("ja-JP", { year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
}


function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("ja-JP", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(date);
}


function sourceLabel(value: string): string {
  return ({
    "3d_part_tree": "3D構成",
    "3d_part_material": "3D材質API",
    "3d_part_extended_info": "パーツ付加情報",
    "3d_mass_properties": "3Dマスプロパティ",
    "2d_title_block": "2D図枠",
    "composed_2d_3d": "2D・3D照合結果",
    "composed_metadata": "統合結果",
    "manual_override": "手動編集",
    "icad_extraction": "ICAD抽出",
    "file": "登録ファイル",
  } as Record<string, string>)[value] ?? value;
}


function confidenceLabel(value: string): string {
  return ({ high: "高", medium: "中", low: "低" } as Record<string, string>)[value] ?? value;
}


const COMPACT_VALUE_MAX_LENGTH = 120;

function rawCompactValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (Array.isArray(value)) return value.length ? value.map((item) => rawCompactValue(item)).join(", ") : "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function compactValue(value: unknown): string {
  // 2D抽出根拠などの長い診断文字列がテーブル幅を押し広げないよう表示用に省略する。
  // 全文は取得元・採用根拠ダイアログで確認できる。
  const text = rawCompactValue(value);
  return text.length > COMPACT_VALUE_MAX_LENGTH ? `${text.slice(0, COMPACT_VALUE_MAX_LENGTH)}…` : text;
}


function reconciliationStatusLabel(value: string): string {
  return ({
    matched: "一致",
    conflict: "差異あり",
    merged: "統合",
    only_2d: "2Dのみ",
    only_3d: "3Dのみ",
    manual_override: "手動上書き",
    empty: "空",
  } as Record<string, string>)[value] ?? value;
}


function historyActorLabel(value: string): string {
  if (!value || value === "api") return "利用者";
  if (value.includes("import_") || value.includes("_2026_") || value === "worker") return "自動取得";
  return value;
}


function historyActionLabel(action: string, mode: string): string {
  const label = ({ extraction: "属性・タグ更新", override: "登録情報編集", requeue: "再抽出", review: "抽出結果レビュー" } as Record<string, string>)[action] ?? action;
  return `${label} (${mode.toUpperCase()})`;
}


function historyReasonLabel(value: string): string {
  return value === "extractor result saved" ? "ICAD抽出結果を反映" : value || "-";
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
            <input type="search" value={draftQuery} onChange={(event) => setDraftQuery(event.target.value)} />
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
            <button className="production-primary-button" type="submit">検索</button>
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
                    <th>製品・装置・ユニット名</th><th>種別</th><th>担当者</th><th>部品数</th><th>ステータス</th><th>最終更新日</th>
                  </>
                ) : (
                  <>
                    <th>部品番号</th><th>部品名</th><th>カテゴリ</th><th>材質</th><th>担当者</th><th>ステータス</th><th>最終更新日</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={targetKey === "product" ? 7 : 8}>読み込んでいます。</td></tr>
              ) : error ? (
                <tr><td colSpan={targetKey === "product" ? 7 : 8} className="error-text">{error}</td></tr>
              ) : catalog?.items.length ? (
                catalog.items.map((record) => (
                  <tr key={record.entityId} className="production-clickable-row" onClick={() => onOpenDetail(record.entityId, record.drawingId)}>
                    <td />
                    {targetKey === "product" ? (
                      <>
                        <td>{record.name}</td><td>{entityKindLabel(record)}</td><td>{businessValue(record, "owner")}</td><td>{record.descendantPartCount}</td><td>{businessValue(record, "status")}</td><td>{formatDate(record.updatedAt)}</td>
                      </>
                    ) : (
                      <>
                        <td>{record.partNumber ?? "-"}</td><td>{record.name}</td><td>{businessValue(record, "category")}</td><td>{attributeValue(record, "materials")}</td><td>{businessValue(record, "owner")}</td><td>{businessValue(record, "status")}</td><td>{formatDate(record.updatedAt)}</td>
                      </>
                    )}
                  </tr>
                ))
              ) : (
                <tr><td colSpan={targetKey === "product" ? 7 : 8}>該当する{listLabel}はありません。</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="production-pagination" aria-label="pagination">
          <button type="button" disabled={page === 0} onClick={() => setPage(0)}>«</button>
          <button type="button" disabled={page === 0} onClick={() => setPage((current) => Math.max(0, current - 1))}>‹</button>
          <button type="button" className="active">{page + 1}</button>
          <button type="button" disabled={!catalog || (page + 1) * pageSize >= catalog.totalCount} onClick={() => setPage((current) => current + 1)}>›</button>
          <button type="button" disabled={!catalog || (page + 1) * pageSize >= catalog.totalCount} onClick={() => setPage(Math.max(0, Math.ceil((catalog?.totalCount ?? 1) / pageSize) - 1))}>»</button>
        </div>
      </section>
    </section>
  );
}


type RelatedTabId = "project" | "parent" | "child" | "part" | "product" | "drawing" | "document" | "conversation";

type RelatedTab = { id: RelatedTabId; label: string };

const productTabs: RelatedTab[] = [
  { id: "project", label: "プロジェクト" },
  { id: "parent", label: "親製品・装置・ユニット" },
  { id: "child", label: "子製品・装置・ユニット" },
  { id: "part", label: "部品" },
  { id: "drawing", label: "図面" },
  { id: "document", label: "文書" },
  { id: "conversation", label: "会話ログ" },
];

const partTabs: RelatedTab[] = [
  { id: "product", label: "製品・装置・ユニット" },
  { id: "drawing", label: "図面" },
  { id: "document", label: "文書" },
  { id: "conversation", label: "会話ログ" },
];


function relatedItems(record: KnowledgeEntityRecord, tabId: RelatedTabId): KnowledgeEntityRelatedItem[] {
  const related = record.relatedEntities ?? [];
  if (tabId === "parent") return related.filter((item) => item.relationship === "parent");
  if (tabId === "child") return related.filter((item) => item.relationship === "child" && item.targetKey === "product");
  if (tabId === "part") return related.filter((item) => item.targetKey === "part");
  if (tabId === "product") return related.filter((item) => item.targetKey === "product");
  return [];
}


function ModalShell({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="production-modal-backdrop" role="presentation">
      <section className="production-modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="production-modal-header">
          <h2>{title}</h2>
          <button className="production-icon-button" type="button" onClick={onClose} aria-label="閉じる" title="閉じる"><IconX size={20} /></button>
        </div>
        <div className="production-section-divider" />
        {children}
      </section>
    </div>
  );
}


function EntityEditDialog({ record, onClose, onSaved }: { record: KnowledgeEntityRecord; onClose: () => void; onSaved: () => Promise<void> }) {
  const [fields, setFields] = useState({ ...record.businessFields });
  const [tagText, setTagText] = useState(record.tags.map((tag) => tag.value).join("、"));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isProduct = record.targetKey === "product";

  const input = (key: string, label: string, type = "text") => (
    <label className="production-form-field">
      <span>{label}</span>
      <input type={type} value={fields[key] ?? ""} onChange={(event) => setFields((current) => ({ ...current, [key]: event.target.value }))} />
    </label>
  );

  async function save() {
    setSaving(true);
    setError(null);
    const nextTags = [...new Set(tagText.split(/[、,\n]/).map((value) => value.trim()).filter(Boolean))];
    const currentTags = record.tags.map((tag) => tag.value);
    try {
      await applyDrawingMetadataOverrides(record.drawingId, "3d", {}, "製品・部品の登録情報を編集", {
        businessFields: fields,
        knowledgeEntityTarget: record.targetKey,
        knowledgeEntityKind: (isProduct ? fields.entityKind || record.entityKind : "part") as KnowledgeEntityKind,
        derivedTags: {
          added: nextTags.filter((value) => !currentTags.includes(value)),
          removed: currentTags.filter((value) => !nextTags.includes(value)),
        },
      });
      await onSaved();
      onClose();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "登録情報を保存できませんでした。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell title="登録情報を編集" onClose={onClose}>
      <div className="production-edit-grid">
        {isProduct ? input("name", "製品・装置・ユニット名") : <>{input("partNumber", "部品番号")}{input("name", "部品名")}</>}
        {input("category", "カテゴリ")}
        {isProduct ? (
          <label className="production-form-field"><span>種別</span><select value={fields.entityKind || record.entityKind} onChange={(event) => setFields((current) => ({ ...current, entityKind: event.target.value }))}><option value="assembly">アセンブリ</option><option value="subassembly">サブアセンブリ</option></select></label>
        ) : <>{input("supplier", "仕入先")}{input("unitPrice", "単価", "number")}{input("unit", "単位")}</>}
        {isProduct ? input("phase", "フェーズ") : null}
        {input("status", "ステータス")}
        {input("owner", "担当者")}
        <label className="production-form-field production-form-field-wide"><span>タグ</span><textarea value={tagText} onChange={(event) => setTagText(event.target.value)} /><small>読点または改行で区切ります。</small></label>
        <label className="production-form-field production-form-field-wide"><span>備考</span><textarea value={fields.remarks ?? ""} onChange={(event) => setFields((current) => ({ ...current, remarks: event.target.value }))} /></label>
      </div>
      {error ? <p className="error-text">{error}</p> : null}
      <div className="production-modal-actions"><button className="production-secondary-button" type="button" onClick={onClose}>キャンセル</button><button className="production-primary-button" type="button" disabled={saving} onClick={() => void save()}>{saving ? "保存しています。" : "保存"}</button></div>
    </ModalShell>
  );
}


function ProvenanceDialog({ record, onClose }: { record: KnowledgeEntityRecord; onClose: () => void }) {
  return (
    <ModalShell title="取得元・採用根拠" onClose={onClose}>
      <p className="production-modal-note">表示中の属性・タグが、ICADのどの情報を根拠に採用されたかを確認できます。</p>
      <div className="production-table-shell production-provenance-table">
        <table className="production-table"><thead><tr><th>種別</th><th>項目・タグ</th><th>値</th><th>取得元</th><th>信頼度</th><th>根拠位置</th><th>採用理由</th></tr></thead><tbody>
          {(record.provenance ?? []).map((item, index) => <tr key={`${item.kind}-${item.name}-${index}`}><td>{item.kind === "tag" ? "タグ" : "属性"}</td><td>{item.name}</td><td>{item.value}</td><td>{sourceLabel(item.source)}</td><td>{confidenceLabel(item.confidence)}</td><td>{item.evidence}</td><td>{item.reason}</td></tr>)}
        </tbody></table>
      </div>
      <div className="production-extraction-review">
        <strong>ICAD抽出根拠</strong>
        <p>抽出レビュー状態は図面管理側で扱い、この画面では採用済みの取得元・信頼度・採用理由だけを確認します。</p>
      </div>
    </ModalShell>
  );
}


function ReconciliationPanel({ record }: { record: KnowledgeEntityRecord }) {
  const rows = (record.reconciledAttributes ?? []).filter((item) => item.status !== "empty").slice(0, 12);
  if (!rows.length && !(record.diagnosticConflicts ?? []).length) return null;
  return (
    <section className="production-section production-reconciliation-section">
      <h2>2D/3D照合</h2>
      <div className="production-section-divider" />
      <div className="production-table-shell">
        <table className="production-table">
          <thead><tr><th>項目</th><th>状態</th><th>2D</th><th>3D</th><th>採用候補</th><th>根拠</th></tr></thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.attribute}>
                <td>{item.attribute}</td>
                <td>{reconciliationStatusLabel(item.status)}</td>
                <td>{compactValue(item.value2d)}</td>
                <td>{compactValue(item.value3d)}</td>
                <td>{compactValue(item.chosenValue)}</td>
                <td>{item.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(record.diagnosticConflicts ?? []).length ? <p className="production-section-note">診断差分: {(record.diagnosticConflicts ?? []).length}件。内部件数や抽出元差分のため、タグ確定前レビュー対象とは分けて扱います。</p> : null}
    </section>
  );
}


function DrawingLinkDialog({ record, onClose, onSaved }: { record: KnowledgeEntityRecord; onClose: () => void; onSaved: () => Promise<void> }) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<DrawingOption[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set((record.relatedDrawings ?? []).filter((item) => item.relationship === "linked").map((item) => item.drawingId)));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(search: string) {
    setLoading(true);
    setError(null);
    try {
      const payload = await getDrawingOptions(search);
      setOptions(payload.items.filter((item) => item.drawingId !== record.drawingId));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "図面一覧を取得できませんでした。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(""); }, []);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await applyDrawingMetadataOverrides(record.drawingId, "3d", {}, "関連図面を更新", { relatedDrawingIds: [...selected] });
      await onSaved();
      onClose();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "関連図面を保存できませんでした。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell title="図面を紐づける" onClose={onClose}>
      <form className="production-link-search" onSubmit={(event) => { event.preventDefault(); void load(query); }}><label><span>図面名・ICADファイル</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="production-primary-button" type="submit">検索</button></form>
      {error ? <p className="error-text">{error}</p> : null}
      <div className="production-table-shell production-link-table"><table className="production-table"><thead><tr><th>選択</th><th>図面名</th><th>抽出で使うICADファイル</th></tr></thead><tbody>
        {loading ? <tr><td colSpan={3}>読み込んでいます。</td></tr> : options.length ? options.map((item) => <tr key={item.drawingId}><td><input aria-label={`${item.filename}を選択`} type="checkbox" checked={selected.has(item.drawingId)} onChange={(event) => setSelected((current) => { const next = new Set(current); if (event.target.checked) next.add(item.drawingId); else next.delete(item.drawingId); return next; })} /></td><td>{item.filename}</td><td>{item.sourcePath}</td></tr>) : <tr><td colSpan={3}>紐づけ可能な図面がありません。</td></tr>}
      </tbody></table></div>
      <div className="production-modal-actions"><span>{selected.size}件を選択中</span><button className="production-secondary-button" type="button" onClick={onClose}>キャンセル</button><button className="production-primary-button" type="button" disabled={saving} onClick={() => void save()}>{saving ? "保存しています。" : "紐づけを保存"}</button></div>
    </ModalShell>
  );
}


export function IcadEntityDetailPage({ entityId, drawingId, onNavigate }: { entityId: string | null; drawingId: string | null; onNavigate: (page: KnowledgePageKey, entityId?: string, drawingId?: string) => void }) {
  const { record, loading, error, refresh } = useKnowledgeEntityDetail(entityId, drawingId);
  const [activeTabId, setActiveTabId] = useState<RelatedTabId>("project");
  const [editOpen, setEditOpen] = useState(false);
  const [provenanceOpen, setProvenanceOpen] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);

  useEffect(() => {
    if (record?.targetKey === "part") setActiveTabId("product");
  }, [record?.targetKey]);

  const tabs = record?.targetKey === "part" ? partTabs : productTabs;
  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0];
  const activeItems = useMemo(() => record ? relatedItems(record, activeTab.id) : [], [activeTab.id, record]);

  if (loading) return <section className="production-section workspace-message">読み込んでいます。</section>;
  if (error || !record) return <section className="production-section workspace-message error-panel">{error ?? "詳細が見つかりません。"}</section>;

  const isProduct = record.targetKey === "product";
  const basicFields = isProduct
    ? [["製品・装置・ユニット名", businessValue(record, "name")], ["カテゴリ", businessValue(record, "category")], ["種別", entityKindLabel(record)], ["フェーズ", businessValue(record, "phase")], ["ステータス", businessValue(record, "status")], ["担当者", businessValue(record, "owner")]]
    : [["部品番号", businessValue(record, "partNumber")], ["部品名", businessValue(record, "name")], ["カテゴリ", businessValue(record, "category")], ["仕入先", businessValue(record, "supplier")], ["単価", businessValue(record, "unitPrice")], ["単位", businessValue(record, "unit")], ["担当者", businessValue(record, "owner")], ["ステータス", businessValue(record, "status")]];
  const visibleAttributes = record.attributes.filter((attribute) => !["classification_reason", "source_path"].includes(attribute.key));
  const drawings = record.relatedDrawings ?? [];
  const currentRecord = record;

  async function unlinkDrawing(linkedDrawingId: string) {
    const remaining = drawings.filter((item) => item.relationship === "linked" && item.drawingId !== linkedDrawingId).map((item) => item.drawingId);
    await applyDrawingMetadataOverrides(currentRecord.drawingId, "3d", {}, "関連図面を解除", { relatedDrawingIds: remaining });
    await refresh();
  }

  return (
    <section className="knowledge-production-page entity-page">
      <section className="production-section production-basic-section">
        <div className="production-section-header"><div className="production-section-title-row"><h2>基本情報</h2><span className="production-version">ver.1</span><button className="production-icon-button" type="button" aria-label="お気に入り" title="お気に入り"><IconStar size={20} /></button></div><div className="production-section-actions"><button className="production-icon-button" type="button" onClick={() => setEditOpen(true)} aria-label="編集" title="編集"><IconPencil size={19} /></button><button className="production-icon-button" type="button" disabled aria-label="削除" title="削除"><IconTrash size={18} /></button></div></div>
        <div className="production-section-divider" />
        <div className="production-detail-grid">{basicFields.map(([label, value]) => <div key={label} className="production-detail-field"><span>{label}</span><p>{value}</p></div>)}</div>
        <div className="production-attribute-block"><div className="production-attribute-heading"><span>属性情報</span><button className="production-secondary-button production-compact-button" type="button" onClick={() => setProvenanceOpen(true)}>取得根拠を見る</button></div><div className="production-table-shell"><table className="production-table entity-attribute-table"><tbody>
          {visibleAttributes.length ? visibleAttributes.map((attribute) => <tr key={`${attribute.key}-${attribute.value}`}><th>{attribute.label}</th><td>{attribute.value}</td></tr>) : <tr><td>属性情報がありません。</td></tr>}
          <tr><th>タグ</th><td>{record.tags.length ? <div className="production-tag-list">{record.tags.map((tag) => <span key={tag.value}>{tag.value}</span>)}</div> : "-"}</td></tr>
        </tbody></table></div></div>
        <div className="production-detail-field"><span>備考</span><p>{businessValue(record, "remarks")}</p></div>
      </section>

      <ReconciliationPanel record={record} />

      <section className="production-section production-related-section">
        <h2>関連情報</h2><div className="production-section-divider" />
        <div className="production-tabs" role="tablist">{tabs.map((tab) => <button key={tab.id} className={tab.id === activeTab.id ? "active" : ""} type="button" role="tab" onClick={() => setActiveTabId(tab.id)}>{tab.label}</button>)}</div>
        <div className="production-related-body"><div className="production-related-heading-row"><p>{activeTab.label}一覧</p>{activeTab.id === "drawing" ? <button className="production-secondary-button production-link-button" type="button" onClick={() => setLinkOpen(true)}><IconLink size={17} />図面を紐づける</button> : null}</div>
          <div className="production-table-shell"><table className="production-table"><thead><tr><th>{activeTab.id === "drawing" ? "図面名" : `${activeTab.label}名`}</th><th>種別</th><th>関連</th><th /></tr></thead><tbody>
            {activeTab.id === "drawing" ? drawings.map((item) => <tr key={item.drawingId} className="production-clickable-row" onClick={() => onNavigate("drawing", undefined, item.drawingId)}><td>{item.filename}</td><td>図面</td><td>{item.relationship === "source" ? "ICAD抽出元" : "紐づけ"}</td><td>{item.relationship === "linked" ? <button className="production-icon-button" type="button" aria-label={`${item.filename}の紐づけを解除`} title="紐づけを解除" onClick={(event) => { event.stopPropagation(); void unlinkDrawing(item.drawingId); }}><IconUnlink size={18} /></button> : null}</td></tr>)
            : activeItems.length ? activeItems.map((item) => <tr key={item.entityId} className="production-clickable-row" onClick={() => onNavigate(item.targetKey, item.entityId, record.drawingId)}><td>{item.name}</td><td>{item.entityKind === "part" ? "部品" : item.entityKind === "assembly" ? "アセンブリ" : "サブアセンブリ"}</td><td>{item.relationship === "parent" ? "親" : "子"}</td><td /></tr>)
            : <tr><td colSpan={4}>関連情報がありません。</td></tr>}
          </tbody></table></div>
        </div>
      </section>

      <section className="production-section production-history-section"><h2>変更履歴</h2><div className="production-section-divider" /><div className="production-table-shell"><table className="production-table"><thead><tr><th>バージョン</th><th>変更日時</th><th>変更者</th><th>操作</th></tr></thead><tbody>
        {record.history.length ? record.history.slice(0, 10).map((history, index) => <tr key={`${history.executedAt}-${index}`}><td>{record.history.length - index}</td><td>{formatDateTime(history.executedAt)}</td><td>{historyActorLabel(history.executedBy)}</td><td title={historyReasonLabel(history.reason)}>{historyActionLabel(history.action, history.mode)}</td></tr>) : <tr><td>1</td><td>{formatDateTime(record.updatedAt)}</td><td>ICAD抽出</td><td>抽出結果反映</td></tr>}
      </tbody></table></div></section>

      {editOpen ? <EntityEditDialog record={record} onClose={() => setEditOpen(false)} onSaved={refresh} /> : null}
      {provenanceOpen ? <ProvenanceDialog record={record} onClose={() => setProvenanceOpen(false)} /> : null}
      {linkOpen ? <DrawingLinkDialog record={record} onClose={() => setLinkOpen(false)} onSaved={refresh} /> : null}
    </section>
  );
}
