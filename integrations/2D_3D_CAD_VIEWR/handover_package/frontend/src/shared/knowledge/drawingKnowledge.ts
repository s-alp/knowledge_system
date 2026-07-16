import type { DrawingBootstrapResponse, DrawingField, DrawingKnowledgeDetail } from "../types/viewer";

export type { DrawingField, DrawingKnowledgeDetail } from "../types/viewer";

function resolveDisplayValue(value?: string | null): string {
  return value?.trim() ? value : "-";
}

function resolveTags(bootstrap: DrawingBootstrapResponse): string[] {
  return bootstrap.metadata.tags?.filter((tag) => tag.trim().length > 0) ?? [];
}

function resolveTagAttributeTargets(bootstrap: DrawingBootstrapResponse): DrawingKnowledgeDetail["tagAttributeTargets"] {
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
  const backendDetail = bootstrap.metadata.knowledgeDetail;

  if (backendDetail) {
    return {
      schemaVersion: backendDetail.schemaVersion ?? "viewer_knowledge_detail.v1",
      attributes: backendDetail.attributes ?? [],
      remarks: resolveDisplayValue(backendDetail.remarks),
      revisionHistory: backendDetail.revisionHistory ?? [],
      relatedTabs: backendDetail.relatedTabs ?? [],
      changeHistory: backendDetail.changeHistory ?? [],
      tagAttributeTargets: (backendDetail.tagAttributeTargets ?? tagAttributeTargets).map((target) => ({
        ...target,
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
      })),
      tagAttributePolicy: resolveDisplayValue(backendDetail.tagAttributePolicy),
      tagAttributeReviewRequired: Boolean(backendDetail.tagAttributeReviewRequired),
    };
  }

  return {
    schemaVersion: "viewer_knowledge_detail.empty.v1",
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
