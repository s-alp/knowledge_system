import type { DrawingBootstrapResponse } from "../types/viewer";

export interface DrawingField {
  label: string;
  value: string;
}

export interface DrawingRevisionItem {
  version: string;
  updatedAt: string;
  updatedBy: string;
  summary: string;
  status: string;
}

export interface DrawingRelatedItem {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  chips: string[];
}

export interface DrawingRelatedTab {
  id: string;
  label: string;
  items: DrawingRelatedItem[];
}

export interface DrawingChangeItem {
  version: string;
  changedAt: string;
  changedBy: string;
  summary: string;
}

export interface DrawingTagAttributeItem {
  name: string;
  value: string;
  sourcePath: string;
  entityHint: string;
  bindingStatus: string;
}

export interface DrawingTagAttributeTarget {
  targetKey: string;
  label: string;
  tagApiStatus: string;
  writePolicy: string;
  reviewRequired: boolean;
  tags: string[];
  attributes: DrawingTagAttributeItem[];
  notes: string[];
}

export interface DrawingKnowledgeMock {
  attributes: DrawingField[];
  remarks: string;
  revisionHistory: DrawingRevisionItem[];
  relatedTabs: DrawingRelatedTab[];
  changeHistory: DrawingChangeItem[];
  tagAttributeTargets: DrawingTagAttributeTarget[];
  tagAttributePolicy: string;
  tagAttributeReviewRequired: boolean;
}

function resolveDisplayValue(value?: string | null): string {
  return value?.trim() ? value : "-";
}

function normalizeVersion(version?: string | null): number {
  const parsed = Number.parseInt(version ?? "1", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

function buildVersionLabel(baseVersion: number, offset: number): string {
  return `ver.${Math.max(baseVersion - offset, 1)}`;
}

function resolveTags(bootstrap: DrawingBootstrapResponse): string[] {
  return bootstrap.metadata.tags?.filter((tag) => tag.trim().length > 0) ?? [];
}

function resolveTagAttributeTargets(bootstrap: DrawingBootstrapResponse): DrawingTagAttributeTarget[] {
  return (
    bootstrap.metadata.tagAttributes?.targets
      ?.map((target) => ({
        targetKey: resolveDisplayValue(target.targetKey),
        label: resolveDisplayValue(target.label ?? target.targetKey),
        tagApiStatus: resolveDisplayValue(target.tagApiStatus),
        writePolicy: resolveDisplayValue(target.writePolicy),
        reviewRequired: Boolean(target.reviewRequired),
        tags: target.tags?.filter((tag) => tag.trim().length > 0) ?? [],
        attributes:
          target.attributes
            ?.map((attribute) => ({
              name: resolveDisplayValue(attribute.name),
              value: resolveDisplayValue(attribute.value),
              sourcePath: resolveDisplayValue(attribute.sourcePath),
              entityHint: resolveDisplayValue(attribute.entityHint),
              bindingStatus: resolveDisplayValue(attribute.bindingStatus),
            }))
            .filter((attribute) => attribute.name !== "-" || attribute.value !== "-") ?? [],
        notes: target.notes?.filter((note) => note.trim().length > 0) ?? [],
      }))
      .filter((target) => target.tags.length > 0 || target.attributes.length > 0) ?? []
  );
}

export function buildDrawingInfoFields(bootstrap: DrawingBootstrapResponse): DrawingField[] {
  return [
    { label: "図面番号", value: resolveDisplayValue(bootstrap.metadata.drawingNumber) },
    { label: "図面名", value: resolveDisplayValue(bootstrap.metadata.drawingName ?? bootstrap.title) },
    { label: "図面タイプ", value: resolveDisplayValue(bootstrap.metadata.drawingType) },
    { label: "用紙サイズ", value: resolveDisplayValue(bootstrap.metadata.paperSize) },
    { label: "ステータス", value: resolveDisplayValue(bootstrap.metadata.status) },
    { label: "所有者", value: resolveDisplayValue(bootstrap.metadata.owner) },
    { label: "設計意図・目的", value: resolveDisplayValue(bootstrap.metadata.designPurpose) },
    { label: "タグ", value: resolveTags(bootstrap).join(", ") },
  ];
}

export function buildDrawingKnowledgeMock(bootstrap: DrawingBootstrapResponse): DrawingKnowledgeMock {
  const drawingName = bootstrap.metadata.drawingName ?? bootstrap.title;
  const drawingNumber = bootstrap.metadata.drawingNumber ?? bootstrap.drawingId;
  const owner = bootstrap.metadata.owner ?? "-";
  const tags = resolveTags(bootstrap);
  const tagAttributeTargets = resolveTagAttributeTargets(bootstrap);
  const baseVersion = normalizeVersion(bootstrap.version);
  const hasMeaningfulMetadata =
    Boolean(bootstrap.metadata.drawingNumber) ||
    Boolean(bootstrap.metadata.drawingName) ||
    Boolean(bootstrap.metadata.designPurpose) ||
    tags.length > 0;

  return {
    attributes:
      tags.length > 0
        ? [
            { label: "タグ", value: tags.join(" / ") },
            { label: "図面タイプ", value: resolveDisplayValue(bootstrap.metadata.drawingType) },
          ]
        : [],
    remarks: bootstrap.metadata.designPurpose ?? "-",
    revisionHistory: hasMeaningfulMetadata
      ? [
          {
            version: buildVersionLabel(baseVersion, 0),
            updatedAt: "2026/04/13 22:20:39",
            updatedBy: owner,
            summary: "図面プレビューと基本情報を最新化",
            status: "現行",
          },
          {
            version: buildVersionLabel(baseVersion, 1),
            updatedAt: "2026/04/10 09:12:18",
            updatedBy: "品質保証 佐倉",
            summary: "寸法注記と関連情報の見直し",
            status: "承認",
          },
          {
            version: buildVersionLabel(baseVersion, 2),
            updatedAt: "2026/04/08 14:05:03",
            updatedBy: "設計 二階堂",
            summary: "初版登録",
            status: "作成",
          },
        ]
      : [],
    relatedTabs: hasMeaningfulMetadata
      ? [
          {
            id: "project",
            label: "プロジェクト",
            items: [
              {
                id: "project-main",
                title: "PRJ-OP30 ライン改善",
                subtitle: drawingNumber,
                description: `${drawingName} を利用している親プロジェクトのモック情報です。工程改善向けの確認タスクを紐付けています。`,
                chips: ["進行中", "製造改善"],
              },
            ],
          },
          {
            id: "product",
            label: "製品",
            items: [
              {
                id: "product-main",
                title: "OP30 カセット",
                subtitle: "製品マスタ",
                description: `${drawingName} が属する製品系統を表すモック情報です。部品表や派生図面への接続を想定しています。`,
                chips: ["量産", "標準"],
              },
            ],
          },
          {
            id: "parts",
            label: "部品",
            items: [
              {
                id: "parts-main",
                title: drawingName,
                subtitle: drawingNumber,
                description: "図面と同一識別子で参照される部品情報のモックです。将来的に ERP / BOM の参照先へ差し替えできます。",
                chips: tags,
              },
            ],
          },
          {
            id: "conversation",
            label: "会話ログ",
            items: [
              {
                id: "conversation-main",
                title: "レビューコメント",
                subtitle: "2026/04/13",
                description: "修正箇所の確認依頼と、関連部門からの回答をモックとして表示しています。",
                chips: ["確認依頼", "回答待ち"],
              },
            ],
          },
        ]
      : [
          { id: "project", label: "プロジェクト", items: [] },
          { id: "product", label: "製品", items: [] },
          { id: "parts", label: "部品", items: [] },
          { id: "conversation", label: "会話ログ", items: [] },
        ],
    changeHistory: hasMeaningfulMetadata
      ? [
          {
            version: buildVersionLabel(baseVersion, 0),
            changedAt: "2026/04/13 22:20:39",
            changedBy: owner,
            summary: "図面名、プレビュー、関連セクションの表示内容を更新",
          },
          {
            version: buildVersionLabel(baseVersion, 1),
            changedAt: "2026/04/10 09:12:18",
            changedBy: "品質保証 佐倉",
            summary: "レビューコメントを反映し、注記の表現を調整",
          },
          {
            version: buildVersionLabel(baseVersion, 2),
            changedAt: "2026/04/08 14:05:03",
            changedBy: "設計 二階堂",
            summary: "初版図面を登録",
          },
        ]
      : [],
    tagAttributeTargets,
    tagAttributePolicy: resolveDisplayValue(bootstrap.metadata.tagAttributes?.displayPolicy),
    tagAttributeReviewRequired: Boolean(bootstrap.metadata.tagAttributes?.reviewRequired),
  };
}
