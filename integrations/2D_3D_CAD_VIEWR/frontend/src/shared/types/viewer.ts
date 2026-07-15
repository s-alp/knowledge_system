// frontend が backend API とやり取りする時の契約を集める型定義。
export type Viewer3DStatus = "queued" | "processing" | "ready" | "failed";

export interface Open2DResponse {
  // sourceUrl は元ファイル取得用、pageImageUrls は TIFF の各ページ画像取得用。
  sessionId: string;
  filename: string;
  extension: "pdf" | "jpeg" | "tiff" | "svg";
  mimeType: string;
  sourceUrl: string;
  pageCount: number;
  pageImageUrls: string[];
  diagnostics?: {
    source?: string | null;
    previewKind?: string | null;
    note?: string | null;
  };
}

export interface DrawingBootstrapResponse {
  drawingId: string;
  title: string;
  version?: string | null;
  defaultMode: "2d" | "3d";
  availability: {
    has2d: boolean;
    has3d: boolean;
  };
  metadata: {
    drawingNumber?: string | null;
    drawingName?: string | null;
    drawingType?: string | null;
    paperSize?: string | null;
    status?: string | null;
    owner?: string | null;
    designPurpose?: string | null;
    tags?: string[];
    tagAttributes?: DrawingTagAttributes;
    extractionDiagnostics?: DrawingExtractionDiagnostics;
  };
}

export interface DrawingTagAttribute {
  name?: string | null;
  value?: string | null;
  sourcePath?: string | null;
  entityHint?: string | null;
  bindingStatus?: string | null;
}

export interface DrawingTagAttributeTarget {
  targetKey?: string | null;
  label?: string | null;
  existingReception?: string | null;
  tagApiStatus?: string | null;
  writePolicy?: string | null;
  tags?: string[];
  attributes?: DrawingTagAttribute[];
  reviewRequired?: boolean;
  notes?: string[];
}

export interface DrawingTagAttributes {
  schemaVersion?: string | null;
  sourceSchemaVersion?: string | null;
  displayPolicy?: string | null;
  targets?: DrawingTagAttributeTarget[];
  targetCount?: number;
  reviewRequired?: boolean;
}

export interface DrawingExtractionDiagnostics {
  schemaVersion?: string | null;
  status?: string | null;
  missingModes?: string[];
  policy?: string | null;
}

export interface Open3DResponse {
  // modelUrl は ready になるまで空文字のまま返り、polling 完了後に埋まる。
  jobId: string;
  filename: string;
  sourceExtension: "stl" | "step";
  modelFormat: "stl" | "";
  status: Viewer3DStatus;
  modelUrl: string;
  error: string;
  diagnostics?: {
    source?: string | null;
    previewKind?: string | null;
    note?: string | null;
  };
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
  };
}
