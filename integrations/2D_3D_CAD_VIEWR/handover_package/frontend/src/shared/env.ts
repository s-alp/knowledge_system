export function isLocalFileEnabled(
  flag = import.meta.env.VITE_LOCAL_FILE_ENABLED,
  isDev = import.meta.env.DEV,
): boolean {
  // 開発版では検証導線を最初から出し、本番ビルドでは env の明示値だけを採用する。
  return isDev || String(flag).toLowerCase() === "true";
}

export function isViewerDebugInputsEnabled(
  isDev = import.meta.env.DEV,
): boolean {
  return isDev;
}
