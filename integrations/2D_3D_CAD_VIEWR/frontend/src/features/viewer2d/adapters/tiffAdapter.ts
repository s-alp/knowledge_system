import type { RenderedPage, TwoDDocumentAdapter, TwoDRenderOptions } from "./types";

interface TiffPage {
  width: number;
  height: number;
  image: HTMLImageElement;
}

export async function createTiffAdapter(pageImageUrls: string[]): Promise<TwoDDocumentAdapter> {
  // backend が各ページを PNG 化してくれるので、frontend は画像として順番に読むだけでよい。
  const pages = await Promise.all(
    pageImageUrls.map(async (pageImageUrl) => {
      const image = await loadImage(pageImageUrl);
      return {
        width: image.naturalWidth,
        height: image.naturalHeight,
        image,
      } satisfies TiffPage;
    }),
  );
  return new TiffAdapter(pages);
}

class TiffAdapter implements TwoDDocumentAdapter {
  pageCount: number;

  constructor(private readonly pages: TiffPage[]) {
    this.pageCount = pages.length;
  }

  async renderPage(pageIndex: number, _options?: TwoDRenderOptions): Promise<RenderedPage> {
    const page = this.pages[pageIndex];
    return { width: page.width, height: page.height, renderScale: 1, source: page.image };
  }
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Failed to load TIFF page image"));
    image.src = url;
  });
}
