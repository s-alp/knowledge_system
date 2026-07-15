// 2D / 3D の両 viewer で共通利用する、読み込み進行度の表現。
export type ViewerLoadPhase =
  | "idle"
  | "file_selected"
  | "uploading"
  | "processing"
  | "rendering"
  | "ready"
  | "failed";
