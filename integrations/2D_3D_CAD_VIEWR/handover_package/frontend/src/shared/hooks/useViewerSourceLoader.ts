import { useMemo, useState } from "react";

import type { ViewerLoadPhase } from "../types/loading";

interface UseViewerSourceLoaderOptions<T> {
  openFromUrl: (url: string) => Promise<T>;
  openFromFile: (file: File) => Promise<T>;
  resolveSuccessPhase: (response: T) => ViewerLoadPhase;
  onSuccess: (response: T) => void;
  urlErrorMessage: string;
  fileErrorMessage: string;
}

interface UseViewerSourceLoaderResult {
  url: string;
  selectedFile: File | null;
  formError: string | null;
  phase: ViewerLoadPhase;
  localFileStatus: string | null;
  isBusy: boolean;
  setUrl: (value: string) => void;
  setPhase: (value: ViewerLoadPhase) => void;
  handleOpenUrl: () => Promise<void>;
  handlePickStart: () => void;
  handleFileChange: (file: File | null) => void;
  handlePickComplete: (file: File | null) => void;
  handleOpenExternalFile: (file: File) => void;
}

/**
 * 2D / 3D の入力導線で共通になる URL / upload の開始処理だけをまとめる。
 * 描画完了や polling 後の phase 更新は各 viewer 固有なのでページ側へ残す。
 */
export function useViewerSourceLoader<T>({
  openFromUrl,
  openFromFile,
  resolveSuccessPhase,
  onSuccess,
  urlErrorMessage,
  fileErrorMessage,
}: UseViewerSourceLoaderOptions<T>): UseViewerSourceLoaderResult {
  const [url, setUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [phase, setPhase] = useState<ViewerLoadPhase>("idle");
  const [localFileStatus, setLocalFileStatus] = useState<string | null>(null);

  const isBusy = useMemo(
    () => phase === "uploading" || phase === "processing" || phase === "rendering",
    [phase],
  );

  const handleOpenUrl = async () => {
    setFormError(null);
    setLocalFileStatus(null);
    setPhase("uploading");

    try {
      const response = await openFromUrl(url);
      onSuccess(response);
      setPhase(resolveSuccessPhase(response));
    } catch (nextError) {
      setFormError(nextError instanceof Error ? nextError.message : urlErrorMessage);
      setPhase("failed");
    }
  };

  const handleOpenFile = async (file: File) => {
    setFormError(null);
    setLocalFileStatus("ファイルを送信しています。");
    setPhase("uploading");

    try {
      const response = await openFromFile(file);
      onSuccess(response);
      setPhase(resolveSuccessPhase(response));
    } catch (nextError) {
      setFormError(nextError instanceof Error ? nextError.message : fileErrorMessage);
      setPhase("failed");
    }
  };

  return {
    url,
    selectedFile,
    formError,
    phase,
    localFileStatus,
    isBusy,
    setUrl,
    setPhase,
    handleOpenUrl,
    handlePickStart: () => setLocalFileStatus("ファイル選択ダイアログを開いています。"),
    handleFileChange: setSelectedFile,
    handlePickComplete: (file) => {
      if (!file) {
        setLocalFileStatus(null);
        setPhase("idle");
        return;
      }

      setSelectedFile(file);
      setPhase("file_selected");
      setLocalFileStatus("ファイルを確認しました。これからアップロードします。");
      void handleOpenFile(file);
    },
    handleOpenExternalFile: (file) => {
      setSelectedFile(file);
      setPhase("file_selected");
      setLocalFileStatus("ファイルを確認しました。これからアップロードします。");
      void handleOpenFile(file);
    },
  };
}
