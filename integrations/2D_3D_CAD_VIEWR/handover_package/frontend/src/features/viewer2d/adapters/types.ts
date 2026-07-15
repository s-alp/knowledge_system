// 2D viewer が各形式の adapter に期待する、最小限の共通契約。
export interface RenderedPage {
  width: number;
  height: number;
  renderScale?: number;
  source: CanvasImageSource;
}

export interface TwoDRenderOptions {
  targetWidthPx?: number;
  maxDevicePixelRatio?: number;
}

export interface TwoDDocumentAdapter {
  // PDF/TIFF/JPEG の違いがあっても、viewer 本体はこの API だけ知っていればよい。
  pageCount: number;
  supportsDynamicResolution?: boolean;
  renderPage(pageIndex: number, options?: TwoDRenderOptions): Promise<RenderedPage>;
  dispose?: () => void;
}
