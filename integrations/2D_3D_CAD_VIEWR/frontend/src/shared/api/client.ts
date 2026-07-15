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
}

export interface DrawingMetadataRegistrationResponse {
  drawingId: string;
  filename: string;
  sourcePath: string;
  sourceFormat: string;
  snapshotsByMode: Partial<Record<DrawingMetadataExtractionMode, DrawingMetadataSnapshotResponse>>;
  viewerBootstrap: DrawingBootstrapResponse;
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

export function applyDrawingMetadataOverrides(
  drawingId: string,
  extractionMode: DrawingMetadataExtractionMode,
  canonicalAttributes: Record<string, unknown>,
  reason: string,
): Promise<{
  drawingId: string;
  extractionMode: DrawingMetadataExtractionMode;
  manualOverrides: Record<string, unknown>;
  canonicalAttributes: Record<string, unknown>;
  derivedTags: unknown[];
}> {
  return requestJson(`/drawing-metadata/registrations/${drawingId}/overrides`, {
    method: "PATCH",
    body: JSON.stringify({ extractionMode, canonicalAttributes, reason }),
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
