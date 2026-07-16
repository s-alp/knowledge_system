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

export interface DrawingKnowledgeDetail {
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

export function buildDrawingKnowledgeDetail(bootstrap: DrawingBootstrapResponse): DrawingKnowledgeDetail {
  const tags = resolveTags(bootstrap);
  const tagAttributeTargets = resolveTagAttributeTargets(bootstrap);

  return {
    attributes:
      tags.length > 0
        ? [
            { label: "タグ", value: tags.join(" / ") },
            { label: "図面タイプ", value: resolveDisplayValue(bootstrap.metadata.drawingType) },
          ]
        : [],
    remarks: bootstrap.metadata.designPurpose ?? "-",
    revisionHistory: [],
    relatedTabs: [
      { id: "project", label: "プロジェクト", items: [] },
      { id: "product", label: "製品・装置・ユニット", items: [] },
      { id: "parts", label: "部品", items: [] },
      { id: "conversation", label: "会話ログ", items: [] },
    ],
    changeHistory: [],
    tagAttributeTargets,
    tagAttributePolicy: resolveDisplayValue(bootstrap.metadata.tagAttributes?.displayPolicy),
    tagAttributeReviewRequired: Boolean(bootstrap.metadata.tagAttributes?.reviewRequired),
  };
}
