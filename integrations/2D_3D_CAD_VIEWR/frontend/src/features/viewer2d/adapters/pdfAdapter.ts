import { GlobalWorkerOptions, getDocument, type PDFDocumentProxy } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

import type { RenderedPage, TwoDDocumentAdapter, TwoDRenderOptions } from "./types";

GlobalWorkerOptions.workerSrc = workerUrl;

const DEFAULT_MAX_DEVICE_PIXEL_RATIO = 2;
const MAX_RENDER_PIXELS = 36_000_000;

interface ActiveRenderTask {
  cacheKey: string;
  cancel: (extraDelay?: number) => void;
}

export async function createPdfAdapter(data: ArrayBuffer): Promise<TwoDDocumentAdapter> {
  // PDF.js の document を viewer 共通 adapter へ包み、canvas 描画の入口をそろえる。
  const document = await getDocument({ data }).promise;
  return new PdfAdapter(document);
}

class PdfAdapter implements TwoDDocumentAdapter {
  pageCount: number;
  supportsDynamicResolution = true;
  private readonly renderedPageCache = new Map<string, Promise<RenderedPage>>();
  private readonly activeRenderTasks = new Map<number, ActiveRenderTask>();

  constructor(private readonly document: PDFDocumentProxy) {
    this.pageCount = document.numPages;
  }

  async renderPage(pageIndex: number, options?: TwoDRenderOptions): Promise<RenderedPage> {
    const cacheKey = this.createCacheKey(pageIndex, options);
    const cachedPage = this.renderedPageCache.get(cacheKey);
    if (cachedPage) {
      return cachedPage;
    }

    this.cancelSupersededTask(pageIndex, cacheKey);
    const renderedPagePromise = this.renderPdfPage(pageIndex, cacheKey, options);
    this.renderedPageCache.set(cacheKey, renderedPagePromise);
    try {
      return await renderedPagePromise;
    } catch (error) {
      this.renderedPageCache.delete(cacheKey);
      throw error;
    }
  }

  private createCacheKey(pageIndex: number, options?: TwoDRenderOptions): string {
    const targetWidthKey = options?.targetWidthPx ? String(Math.ceil(options.targetWidthPx)) : "auto";
    const pixelRatioKey = options?.maxDevicePixelRatio ? Number(options.maxDevicePixelRatio.toFixed(2)) : DEFAULT_MAX_DEVICE_PIXEL_RATIO;
    return `${pageIndex}:${targetWidthKey}:${pixelRatioKey}`;
  }

  private cancelSupersededTask(pageIndex: number, nextCacheKey: string) {
    const activeTask = this.activeRenderTasks.get(pageIndex);
    if (!activeTask || activeTask.cacheKey === nextCacheKey) {
      return;
    }
    activeTask.cancel();
  }

  private async renderPdfPage(
    pageIndex: number,
    cacheKey: string,
    options?: TwoDRenderOptions,
  ): Promise<RenderedPage> {
    // pageIndex は viewer 内部では 0 始まり、PDF.js API は 1 始まりなのでここで吸収する。
    const page = await this.document.getPage(pageIndex + 1);
    const unscaledViewport = page.getViewport({ scale: 1 });
    const targetWidthPx = options?.targetWidthPx ?? Math.ceil(unscaledViewport.width);
    const viewportScale = targetWidthPx / unscaledViewport.width;
    const viewport = page.getViewport({ scale: viewportScale });
    const requestedOutputScale = Math.max(window.devicePixelRatio || 1, options?.maxDevicePixelRatio ?? DEFAULT_MAX_DEVICE_PIXEL_RATIO);
    const outputScale = Math.max(
      1,
      Math.min(requestedOutputScale, Math.sqrt(MAX_RENDER_PIXELS / Math.max(viewport.width * viewport.height, 1))),
    );
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Canvas context is unavailable");
    }

    canvas.width = Math.max(1, Math.floor(viewport.width * outputScale));
    canvas.height = Math.max(1, Math.floor(viewport.height * outputScale));
    const renderTask = page.render({
      canvasContext: context,
      viewport,
      transform: outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : undefined,
      background: "rgb(255, 255, 255)",
    });
    this.activeRenderTasks.set(pageIndex, { cacheKey, cancel: (extraDelay?: number) => renderTask.cancel(extraDelay) });

    try {
      await renderTask.promise;
      return {
        width: Math.ceil(viewport.width),
        height: Math.ceil(viewport.height),
        renderScale: viewportScale,
        source: canvas,
      };
    } finally {
      const activeTask = this.activeRenderTasks.get(pageIndex);
      if (activeTask?.cacheKey === cacheKey) {
        this.activeRenderTasks.delete(pageIndex);
      }
    }
  }

  dispose() {
    for (const activeTask of this.activeRenderTasks.values()) {
      activeTask.cancel();
    }
    this.activeRenderTasks.clear();
    this.renderedPageCache.clear();
    void this.document.destroy();
  }
}
