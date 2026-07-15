import type { ViewerLoadPhase } from "./types/loading";

interface LoadingMessage {
  title: string;
  detail: string;
}

// 表示文言をここへ集約し、各ページは phase だけ決めればよいようにする。
export function getViewer2DLoadingMessage(phase: ViewerLoadPhase): LoadingMessage | null {
  switch (phase) {
    case "uploading":
      return {
        title: "2Dファイルを送信しています",
        detail: "アップロードまたはURL取得を進めています。",
      };
    case "processing":
      return {
        title: "2Dファイルを処理しています",
        detail: "表示に必要な情報を整理しています。",
      };
    case "rendering":
      return {
        title: "2Dを描画しています",
        detail: "最初のページを表示用に準備しています。",
      };
    default:
      return null;
  }
}

export function getViewer3DLoadingMessage(phase: ViewerLoadPhase): LoadingMessage | null {
  switch (phase) {
    case "uploading":
      return {
        title: "3Dファイルを送信しています",
        detail: "アップロードまたはURL取得を進めています。",
      };
    case "processing":
      return {
        title: "3Dモデルを変換しています",
        detail: "サーバー側で表示用メッシュを生成しています。",
      };
    case "rendering":
      return {
        title: "3Dモデルを描画しています",
        detail: "最初のフレームを準備しています。",
      };
    default:
      return null;
  }
}
