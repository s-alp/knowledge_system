// frontend が backend API とやり取りする時の契約を集める型定義。
export type Viewer3DStatus = "queued" | "processing" | "ready" | "failed";

export interface Open2DResponse {
  // sourceUrl は元ファイル取得用、pageImageUrls は TIFF の各ページ画像取得用。
  sessionId: string;
  filename: string;
  extension: "pdf" | "jpeg" | "tiff";
  mimeType: string;
  sourceUrl: string;
  pageCount: number;
  pageImageUrls: string[];
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
  };
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
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
  };
}
