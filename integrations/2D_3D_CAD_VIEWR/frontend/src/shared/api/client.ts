import type { ApiErrorPayload, DrawingBootstrapResponse, Open2DResponse, Open3DResponse } from "../types/viewer";

export type DrawingMetadataExtractionMode = "2d" | "3d";

export interface DrawingMetadataJobResponse {
  jobId: string;
  drawingId: string;
  extractionMode: DrawingMetadataExtractionMode;
  status: string;
  extractionProfile: string;
  extractionOptions: Record<string, unknown>;
  errorMessage: string;
}

export interface DrawingMetadataSnapshotResponse {
  extractionMode: DrawingMetadataExtractionMode;
  canonicalAttributes: Record<string, unknown>;
  derivedTags: unknown[];
  manualOverrides: Record<string, unknown>;
  latestJob: DrawingMetadataJobResponse | null;
  reviewStatus: "pending" | "confirmed" | "needs_correction";
  reviewedAt: string | null;
  reviewedBy: string;
}

export interface DrawingMetadataRegistrationResponse {
  drawingId: string;
  filename: string;
  sourcePath: string;
  sourceFormat: string;
  snapshotsByMode: Partial<Record<DrawingMetadataExtractionMode, DrawingMetadataSnapshotResponse>>;
  viewerBootstrap: DrawingBootstrapResponse;
}

export interface DrawingMetadataRegistrationListItem {
  drawingId: string;
  hostDrawingId: string;
  filename: string;
  sourcePath: string;
  sourceFormat: string;
  snapshotModes: DrawingMetadataExtractionMode[];
  latestJobStatusByMode: Partial<Record<DrawingMetadataExtractionMode, string | null>>;
  createdAt: string;
  updatedAt: string;
}

export interface HandoffSummaryResponse {
  scope?: {
    mode: string;
    manifestPath: string;
    manifestSourceCount: number;
    totalRegistrationCount: number;
    scopedRegistrationCount: number;
    excludedRegistrationCount: number;
  };
  apiRows: Array<{
    area: string;
    method: string;
    path: string;
    purpose: string;
  }>;
  summaryCards: Array<{ label: string; value: number }>;
  targetTotals: Array<{
    targetKey: string;
    targetLabel: string;
    drawingCount: number;
    attributeCount: number;
    tagCount: number;
  }>;
  rows: Array<{
    drawingId: string;
    filename: string;
    sourcePath: string;
    has2d: boolean;
    has3d: boolean;
    has2dLabel: string;
    has3dLabel: string;
    snapshotStateLabel: string;
    defaultMode: string;
    canonicalAttributeCount: number;
    tagCount: number;
    reviewConflictCount: number;
    diagnosticConflictCount: number;
    payloadTargets: Array<{
      targetKey: string;
      targetLabel: string;
      attributeCount: number;
      tagCount: number;
      tagApiStatus: string;
      candidateEndpoint: string;
      payloadKeys: string;
    }>;
    detailUrl: string;
    tagReviewUrl: string;
    bootstrapApiUrl: string;
    ragPayloadApiUrl: string;
  }>;
}

export type KnowledgeEntityTargetKey = "product" | "part";
export type KnowledgeEntityKind = "assembly" | "subassembly" | "part";

export interface KnowledgeEntityAttribute {
  key: string;
  label: string;
  value: string;
  source: string;
  confidence: "high" | "medium" | "low" | string;
  evidence: string;
  reason: string;
}

export interface KnowledgeEntityTag {
  value: string;
  source: string;
  confidence: "high" | "medium" | "low" | string;
  evidence: string;
  reason: string;
  manualFlag?: boolean;
  ruleVersion?: string;
}

export interface KnowledgeEntityProvenance {
  kind: "attribute" | "tag";
  name: string;
  key?: string;
  label?: string;
  value: string;
  source: string;
  confidence: "high" | "medium" | "low" | string;
  evidence: string;
  reason: string;
}

export interface KnowledgeEntityRelatedItem {
  relationship: "parent" | "child";
  entityId: string;
  targetKey: KnowledgeEntityTargetKey;
  entityKind: KnowledgeEntityKind;
  name: string;
  partNumber: string | null;
}

export interface KnowledgeEntityRecord {
  entityId: string;
  targetKey: KnowledgeEntityTargetKey;
  entityKind: KnowledgeEntityKind;
  classificationEvidence: string;
  classificationConfidence: string;
  name: string;
  partNumber: string | null;
  comment: string | null;
  treePath: string[];
  depth: number;
  parentEntityId: string | null;
  childEntityIds: string[];
  childAssemblyCount: number;
  childPartCount: number;
  descendantPartCount: number;
  drawingId: string;
  drawingFilename: string;
  sourcePath: string;
  attributes: KnowledgeEntityAttribute[];
  tags: KnowledgeEntityTag[];
  businessFields: Record<string, string>;
  businessFieldSources: Record<string, { source: string; evidence: string }>;
  conflicts: Array<Record<string, unknown>>;
  reviewStatus: "pending" | "confirmed" | "needs_correction";
  reviewRequired: boolean;
  evidence: Array<Record<string, unknown>>;
  history: Array<{
    action: string;
    mode: string;
    reason: string;
    executedBy: string;
    executedAt: string;
  }>;
  updatedAt: string;
  relatedEntities?: KnowledgeEntityRelatedItem[];
  relatedDrawing?: { drawingId: string; filename: string };
  relatedDrawings?: Array<{
    drawingId: string;
    filename: string;
    sourcePath: string;
    relationship: "source" | "linked";
  }>;
  provenance?: KnowledgeEntityProvenance[];
  extractionReview: {
    status: "pending" | "confirmed" | "needs_correction";
    required: boolean;
    label: string;
    description: string;
  };
}

export interface DrawingOption {
  drawingId: string;
  filename: string;
  sourcePath: string;
}

export interface KnowledgeEntityCatalogResponse {
  schemaVersion: string;
  definitions: Record<KnowledgeEntityTargetKey, string>;
  targetKey: KnowledgeEntityTargetKey | null;
  count: number;
  totalCount: number;
  returnedCount: number;
  offset: number;
  limit: number | null;
  items: KnowledgeEntityRecord[];
  skippedDrawings: Array<{ drawingId: string; filename: string; reason: string }>;
}

export interface TagAutomationSettingsResponse {
  title: string;
  summary: string;
  managementLinks: Array<{
    key: string;
    label: string;
    description: string;
    action: "open_icad_extraction_review" | "show_handoff_note" | string;
  }>;
  runtimeRows: Array<{ label: string; value: string }>;
  operationRows: Array<{ area: string; screen: string; role: string; writePolicy: string }>;
  targetRows: Array<{ target: string; displayPage: string; storedAs: string; reviewRoute: string }>;
  ruleRows: Array<{ label: string; value: string }>;
}

export function resolveApiBaseUrl(
  configuredBaseUrl = import.meta.env.VITE_API_BASE_URL,
  isDev = import.meta.env.DEV,
): string {
  if (configuredBaseUrl && configuredBaseUrl.trim().length > 0) {
    return configuredBaseUrl;
  }

  if (isDev) {
    return "/api/v1";
  }

  return "/api/v1";
}

const API_BASE_URL = resolveApiBaseUrl();

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  // API 呼び出しの失敗形を 1 か所にそろえ、画面側は message だけを扱う。
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const payload = (await response.json()) as ApiErrorPayload;
    throw new Error(payload.error.message);
  }

  return (await response.json()) as T;
}

export function openViewer2D(url: string): Promise<Open2DResponse> {
  return requestJson<Open2DResponse>("/viewer2d/open", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function getDrawingBootstrap(drawingId: string): Promise<DrawingBootstrapResponse> {
  return requestJson<DrawingBootstrapResponse>(`/drawings/${drawingId}/bootstrap`);
}

export function getDrawingMetadataRegistration(drawingId: string): Promise<DrawingMetadataRegistrationResponse> {
  return requestJson<DrawingMetadataRegistrationResponse>(`/drawing-metadata/registrations/${drawingId}`);
}

export function getDrawingMetadataRegistrations(): Promise<DrawingMetadataRegistrationListItem[]> {
  return requestJson<DrawingMetadataRegistrationListItem[]>("/drawing-metadata/registrations");
}

export function getKnowledgeEntities(
  targetKey: KnowledgeEntityTargetKey,
  query = "",
  offset = 0,
  limit = 50,
): Promise<KnowledgeEntityCatalogResponse> {
  const search = new URLSearchParams({ target: targetKey, offset: String(offset), limit: String(limit) });
  if (query.trim()) {
    search.set("q", query.trim());
  }
  return requestJson<KnowledgeEntityCatalogResponse>(`/knowledge-entities?${search.toString()}`);
}

export function getKnowledgeEntity(entityId: string, drawingId?: string): Promise<KnowledgeEntityRecord> {
  const search = drawingId ? `?${new URLSearchParams({ drawingId }).toString()}` : "";
  return requestJson<KnowledgeEntityRecord>(`/knowledge-entities/${entityId}${search}`);
}

export function getDrawingOptions(query = "", limit = 100): Promise<{ items: DrawingOption[]; totalCount: number }> {
  const search = new URLSearchParams({ limit: String(limit) });
  if (query.trim()) {
    search.set("q", query.trim());
  }
  return requestJson(`/drawing-options?${search.toString()}`);
}

export function getTagAutomationSettings(): Promise<TagAutomationSettingsResponse> {
  return requestJson<TagAutomationSettingsResponse>("/drawing-metadata/settings/tag-automation");
}

export function getDrawingMetadataHandoffSummary(): Promise<HandoffSummaryResponse> {
  return requestJson<HandoffSummaryResponse>("/drawing-metadata/handoff-summary");
}

export function uploadIcadDrawingMetadata(file: File): Promise<DrawingMetadataRegistrationResponse> {
  return uploadFile<DrawingMetadataRegistrationResponse>("/drawing-metadata/registrations/upload", file);
}

export function enqueueDrawingMetadataExtraction(
  drawingId: string,
  extractionMode: DrawingMetadataExtractionMode,
  extractionProfile = "default",
  extractionOptions: Record<string, unknown> = {},
): Promise<DrawingMetadataJobResponse> {
  return requestJson<DrawingMetadataJobResponse>(`/drawing-metadata/registrations/${drawingId}/extract`, {
    method: "POST",
    body: JSON.stringify({ extractionMode, extractionProfile, extractionOptions }),
  });
}

export function getDrawingMetadataJob(jobId: string): Promise<DrawingMetadataJobResponse> {
  return requestJson<DrawingMetadataJobResponse>(`/drawing-metadata/jobs/${jobId}`);
}

export function applyDrawingMetadataReview(
  drawingId: string,
  extractionMode: DrawingMetadataExtractionMode,
  decision: "confirmed" | "needs_correction",
  reason: string,
): Promise<{
  drawingId: string;
  extractionMode: DrawingMetadataExtractionMode;
  reviewStatus: string;
  reviewedAt: string;
  reviewedBy: string;
}> {
  return requestJson(`/drawing-metadata/registrations/${drawingId}/review`, {
    method: "PATCH",
    body: JSON.stringify({ extractionMode, decision, reason }),
  });
}

export function applyDrawingMetadataOverrides(
  drawingId: string,
  extractionMode: DrawingMetadataExtractionMode,
  canonicalAttributes: Record<string, unknown>,
  reason: string,
  options: {
    businessFields?: Record<string, string>;
    relatedDrawingIds?: string[];
    knowledgeEntityTarget?: KnowledgeEntityTargetKey;
    knowledgeEntityKind?: KnowledgeEntityKind;
    derivedTags?: { added: string[]; removed: string[] };
  } = {},
): Promise<{
  drawingId: string;
  extractionMode: DrawingMetadataExtractionMode;
  manualOverrides: Record<string, unknown>;
  canonicalAttributes: Record<string, unknown>;
  derivedTags: unknown[];
}> {
  return requestJson(`/drawing-metadata/registrations/${drawingId}/overrides`, {
    method: "PATCH",
    body: JSON.stringify({ extractionMode, canonicalAttributes, reason, ...options }),
  });
}

export function openDrawingViewer2D(drawingId: string): Promise<Open2DResponse> {
  return requestJson<Open2DResponse>(`/drawings/${drawingId}/viewer2d/open`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function openViewer3D(url: string): Promise<Open3DResponse> {
  return requestJson<Open3DResponse>("/viewer3d/open", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function openDrawingViewer3D(drawingId: string): Promise<Open3DResponse> {
  return requestJson<Open3DResponse>(`/drawings/${drawingId}/viewer3d/open`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getViewer3DJob(jobId: string): Promise<Open3DResponse> {
  return requestJson<Open3DResponse>(`/viewer3d/jobs/${jobId}`);
}

async function uploadFile<T>(path: string, file: File): Promise<T> {
  // multipart/form-data は browser に boundary を付けさせるため、Content-Type を手で固定しない。
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payload = (await response.json()) as ApiErrorPayload;
    throw new Error(payload.error.message);
  }

  return (await response.json()) as T;
}

export function uploadViewer2D(file: File): Promise<Open2DResponse> {
  return uploadFile<Open2DResponse>("/viewer2d/upload", file);
}

export function uploadViewer3D(file: File): Promise<Open3DResponse> {
  return uploadFile<Open3DResponse>("/viewer3d/upload", file);
}
