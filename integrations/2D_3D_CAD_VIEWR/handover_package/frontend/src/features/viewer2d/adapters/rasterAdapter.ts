import type { RenderedPage, TwoDDocumentAdapter, TwoDRenderOptions } from "./types";

export async function createRasterAdapter(blob: Blob): Promise<TwoDDocumentAdapter> {
  // JPEG など単一画像は object URL に変換して、他形式と同じ adapter API へ合わせる。
  const objectUrl = URL.createObjectURL(blob);
  const image = await loadImage(objectUrl);
  return new RasterAdapter(image, objectUrl);
}

class RasterAdapter implements TwoDDocumentAdapter {
  pageCount = 1;

  constructor(
    private readonly image: HTMLImageElement,
    private readonly objectUrl: string,
  ) {}

  async renderPage(_pageIndex: number, _options?: TwoDRenderOptions): Promise<RenderedPage> {
    return {
      width: this.image.naturalWidth,
      height: this.image.naturalHeight,
      renderScale: 1,
      source: this.image,
    };
  }

  dispose() {
    // object URL を解放しないと画像切り替えのたびに browser 側へ残り続ける。
    URL.revokeObjectURL(this.objectUrl);
  }
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Failed to load image"));
    image.src = url;
  });
}
