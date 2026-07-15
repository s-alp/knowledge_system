import { beforeEach, describe, expect, it, vi } from "vitest";

import { getDocument } from "pdfjs-dist";

import { createPdfAdapter } from "./pdfAdapter";

vi.mock("pdfjs-dist/build/pdf.worker.min.mjs?url", () => ({
  default: "pdf-worker-url",
}));

vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: {},
  getDocument: vi.fn(),
}));

function createRenderTask() {
  let resolvePromise!: () => void;
  let rejectPromise!: (reason?: unknown) => void;
  const promise = new Promise<void>((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });

  const cancel = vi.fn(() => {
    const error = new Error("Rendering cancelled");
    error.name = "RenderingCancelledException";
    rejectPromise(error);
  });

  return {
    promise,
    cancel,
    resolve: resolvePromise,
    reject: rejectPromise,
  };
}

describe("createPdfAdapter", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      {} as unknown as ReturnType<HTMLCanvasElement["getContext"]>,
    );
    Object.defineProperty(window, "devicePixelRatio", {
      configurable: true,
      value: 2,
    });
  });

  it("reuses the cached render for the same page and width bucket", async () => {
    const renderTask = createRenderTask();
    const renderCalls: Array<{ viewport: { width: number }; transform?: number[] }> = [];
    const page = {
      getViewport: vi.fn(({ scale }: { scale: number }) => ({
        width: 500 * scale,
        height: 700 * scale,
      })),
      render: vi.fn((context: { viewport: { width: number }; transform?: number[] }) => {
        renderCalls.push(context);
        return renderTask;
      }),
    };
    const documentProxy = {
      numPages: 1,
      getPage: vi.fn(async () => page),
      destroy: vi.fn(),
    };
    vi.mocked(getDocument).mockReturnValue({
      promise: Promise.resolve(documentProxy),
    } as never);

    const adapter = await createPdfAdapter(new ArrayBuffer(0));
    const firstRenderPromise = adapter.renderPage(0, { targetWidthPx: 1024, maxDevicePixelRatio: 1.25 });
    const secondRenderPromise = adapter.renderPage(0, { targetWidthPx: 1024, maxDevicePixelRatio: 1.25 });

    renderTask.resolve();
    const [firstPage, secondPage] = await Promise.all([firstRenderPromise, secondRenderPromise]);
    const firstRenderContext = renderCalls[0];

    expect(documentProxy.getPage).toHaveBeenCalledTimes(1);
    expect(page.render).toHaveBeenCalledTimes(1);
    expect(firstRenderContext).toBeDefined();
    expect(firstRenderContext?.viewport.width).toBe(1024);
    expect(firstRenderContext?.transform).toEqual([2, 0, 0, 2, 0, 0]);
    expect(firstPage.width).toBe(1024);
    expect(secondPage.width).toBe(1024);
  });

  it("starts a distinct render when the width bucket changes", async () => {
    const firstTask = createRenderTask();
    const secondTask = createRenderTask();
    const tasks = [firstTask, secondTask];
    const renderCalls: Array<{ viewport: { width: number } }> = [];
    const page = {
      getViewport: vi.fn(({ scale }: { scale: number }) => ({
        width: 500 * scale,
        height: 700 * scale,
      })),
      render: vi.fn((context: { viewport: { width: number } }) => {
        renderCalls.push(context);
        return tasks.shift() as ReturnType<typeof createRenderTask>;
      }),
    };
    const documentProxy = {
      numPages: 1,
      getPage: vi.fn(async () => page),
      destroy: vi.fn(),
    };
    vi.mocked(getDocument).mockReturnValue({
      promise: Promise.resolve(documentProxy),
    } as never);

    const adapter = await createPdfAdapter(new ArrayBuffer(0));
    const firstRenderPromise = adapter.renderPage(0, { targetWidthPx: 1024, maxDevicePixelRatio: 1.25 });
    firstTask.resolve();
    await firstRenderPromise;

    const secondRenderPromise = adapter.renderPage(0, { targetWidthPx: 1280, maxDevicePixelRatio: 1.25 });
    secondTask.resolve();
    await secondRenderPromise;
    const secondRenderContext = renderCalls[1];

    expect(page.render).toHaveBeenCalledTimes(2);
    expect(secondRenderContext).toBeDefined();
    expect(secondRenderContext?.viewport.width).toBe(1280);
  });

  it("cancels a superseded in-flight render for the same page", async () => {
    const firstTask = createRenderTask();
    const secondTask = createRenderTask();
    const tasks = [firstTask, secondTask];
    const page = {
      getViewport: vi.fn(({ scale }: { scale: number }) => ({
        width: 500 * scale,
        height: 700 * scale,
      })),
      render: vi.fn(() => tasks.shift()),
    };
    const documentProxy = {
      numPages: 1,
      getPage: vi.fn(async () => page),
      destroy: vi.fn(),
    };
    vi.mocked(getDocument).mockReturnValue({
      promise: Promise.resolve(documentProxy),
    } as never);

    const adapter = await createPdfAdapter(new ArrayBuffer(0));
    const firstRenderPromise = adapter.renderPage(0, { targetWidthPx: 1024, maxDevicePixelRatio: 1.25 });
    await Promise.resolve();
    const secondRenderPromise = adapter.renderPage(0, { targetWidthPx: 1024, maxDevicePixelRatio: 3.2 });

    expect(firstTask.cancel).toHaveBeenCalledTimes(1);
    secondTask.resolve();
    await secondRenderPromise;
    await expect(firstRenderPromise).rejects.toMatchObject({ name: "RenderingCancelledException" });
  });

  it("clears a failed cache entry so the same width bucket can retry", async () => {
    const firstTask = createRenderTask();
    const secondTask = createRenderTask();
    const tasks = [firstTask, secondTask];
    const page = {
      getViewport: vi.fn(({ scale }: { scale: number }) => ({
        width: 500 * scale,
        height: 700 * scale,
      })),
      render: vi.fn(() => tasks.shift()),
    };
    const documentProxy = {
      numPages: 1,
      getPage: vi.fn(async () => page),
      destroy: vi.fn(),
    };
    vi.mocked(getDocument).mockReturnValue({
      promise: Promise.resolve(documentProxy),
    } as never);

    const adapter = await createPdfAdapter(new ArrayBuffer(0));
    const firstRenderPromise = adapter.renderPage(0, { targetWidthPx: 1024, maxDevicePixelRatio: 1.25 });
    firstTask.reject(new Error("render failed"));
    await expect(firstRenderPromise).rejects.toThrow("render failed");

    const retryPromise = adapter.renderPage(0, { targetWidthPx: 1024, maxDevicePixelRatio: 1.25 });
    secondTask.resolve();
    await retryPromise;

    expect(page.render).toHaveBeenCalledTimes(2);
  });
});
