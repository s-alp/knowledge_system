import { act, cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReducer } from "react";

import type { RenderedPage, TwoDDocumentAdapter, TwoDRenderOptions } from "../adapters/types";
import { initialTwoDViewportState, twoDViewportReducer } from "../state/viewer2dState";
import { TwoDViewerCanvas } from "./TwoDViewerCanvas";

class ResizeObserverMock {
  static instances: ResizeObserverMock[] = [];
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();

  constructor(private readonly callback: ResizeObserverCallback) {
    ResizeObserverMock.instances.push(this);
  }

  trigger() {
    this.callback([] as ResizeObserverEntry[], this as unknown as ResizeObserver);
  }

  static triggerAll() {
    for (const instance of ResizeObserverMock.instances) {
      instance.trigger();
    }
  }
}

function createPage(width: number, height: number): RenderedPage {
  return {
    width,
    height,
    source: document.createElement("img"),
  };
}

function createCanvasPage(width: number, height: number): RenderedPage {
  return createLabeledCanvasPage("canvas", width, height);
}

function createLabeledCanvasPage(label: string, width: number, height: number): RenderedPage {
  const canvas = document.createElement("canvas");
  canvas.dataset.label = label;
  return {
    width,
    height,
    source: canvas,
  };
}

function createAdapter() {
  const pages = [createPage(320, 240), createPage(480, 360)];
  const renderPage = vi.fn(async (pageIndex: number, _options?: TwoDRenderOptions) => pages[pageIndex]);
  const adapter = {
    pageCount: pages.length,
    renderPage,
  } satisfies TwoDDocumentAdapter;

  return { adapter, renderPage };
}

function createDynamicAdapter() {
  const pages = [createCanvasPage(320, 240), createCanvasPage(480, 360)];
  const renderPage = vi.fn(async (pageIndex: number, _options?: TwoDRenderOptions) => pages[pageIndex]);
  const adapter = {
    pageCount: pages.length,
    supportsDynamicResolution: true,
    renderPage,
  } satisfies TwoDDocumentAdapter;

  return { adapter, renderPage };
}

function createDeferredDynamicAdapter() {
  const renderPage = vi.fn(
    (pageIndex: number, options?: TwoDRenderOptions) =>
      new Promise<RenderedPage>((resolve) => {
        renderResolvers.push({ pageIndex, options, resolve });
      }),
  );
  const renderResolvers: Array<{
    pageIndex: number;
    options?: TwoDRenderOptions;
    resolve: (page: RenderedPage) => void;
  }> = [];
  const adapter = {
    pageCount: 2,
    supportsDynamicResolution: true,
    renderPage,
  } satisfies TwoDDocumentAdapter;

  return { adapter, renderPage, renderResolvers };
}

function Harness({ adapter }: { adapter: TwoDDocumentAdapter | null }) {
  const [viewport, dispatchViewport] = useReducer(twoDViewportReducer, initialTwoDViewportState);

  return (
    <TwoDViewerCanvas
      adapter={adapter}
      pageIndex={0}
      viewport={viewport}
      onViewportAction={dispatchViewport}
      onPageCountResolved={vi.fn()}
      onRendered={vi.fn()}
    />
  );
}

describe("TwoDViewerCanvas", () => {
  let stageWidth = 960;
  let stageHeight = 640;
  let setPointerCaptureMock: ReturnType<typeof vi.fn>;
  let releasePointerCaptureMock: ReturnType<typeof vi.fn>;
  let hasPointerCaptureMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    const mockedContext = {
      clearRect: vi.fn(),
      drawImage: vi.fn(),
      restore: vi.fn(),
      rotate: vi.fn(),
      save: vi.fn(),
      scale: vi.fn(),
      translate: vi.fn(),
    } as unknown as ReturnType<HTMLCanvasElement["getContext"]>;

    ResizeObserverMock.instances = [];
    setPointerCaptureMock = vi.fn();
    releasePointerCaptureMock = vi.fn();
    hasPointerCaptureMock = vi.fn(() => true);
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    vi.stubGlobal("PointerEvent", MouseEvent);
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(mockedContext);
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(() => stageWidth);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockImplementation(() => stageHeight);
    Object.assign(HTMLElement.prototype, {
      setPointerCapture: setPointerCaptureMock,
      releasePointerCapture: releasePointerCaptureMock,
      hasPointerCapture: hasPointerCaptureMock,
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("keeps the rendered page while only panning", async () => {
    const { adapter, renderPage } = createAdapter();
    const onPageCountResolved = vi.fn();
    const onRendered = vi.fn();
    const onViewportAction = vi.fn();
    const { rerender } = render(
      <TwoDViewerCanvas
        adapter={adapter}
        pageIndex={0}
        viewport={initialTwoDViewportState}
        onViewportAction={onViewportAction}
        onPageCountResolved={onPageCountResolved}
        onRendered={onRendered}
      />,
    );

    await waitFor(() => expect(renderPage).toHaveBeenCalledTimes(1));
    expect(renderPage).toHaveBeenNthCalledWith(1, 0, undefined);
    await waitFor(() => expect(onRendered).toHaveBeenCalledTimes(1));
    expect(onPageCountResolved).toHaveBeenCalledTimes(1);
    expect(onPageCountResolved).toHaveBeenCalledWith(2);

    rerender(
      <TwoDViewerCanvas
        adapter={adapter}
        pageIndex={0}
        viewport={{ ...initialTwoDViewportState, offsetX: 48, offsetY: -24 }}
        onViewportAction={onViewportAction}
        onPageCountResolved={onPageCountResolved}
        onRendered={onRendered}
      />,
    );

    await waitFor(() => expect(onRendered).toHaveBeenCalledTimes(1));
    expect(renderPage).toHaveBeenCalledTimes(1);
    expect(onPageCountResolved).toHaveBeenCalledTimes(1);
  });

  it("loads a higher-resolution page after zoom settles", async () => {
    const { adapter, renderPage, renderResolvers } = createDeferredDynamicAdapter();
    const onRendered = vi.fn();
    const { container, rerender } = render(
      <TwoDViewerCanvas
        adapter={adapter}
        pageIndex={0}
        viewport={initialTwoDViewportState}
        onViewportAction={vi.fn()}
        onPageCountResolved={vi.fn()}
        onRendered={onRendered}
      />,
    );

    await waitFor(() => expect(renderPage).toHaveBeenCalledTimes(1));
    renderResolvers.shift()?.resolve(createLabeledCanvasPage("base", 1024, 768));
    await act(async () => {
      await Promise.resolve();
    });
    await waitFor(() => expect(onRendered).toHaveBeenCalledTimes(1));

    vi.useFakeTimers();

    const stage = container.querySelector(".viewer-stage-document");
    expect(stage).not.toBeNull();
    fireEvent.pointerDown(stage!, { pointerId: 7, button: 0, isPrimary: true, clientX: 200, clientY: 200 });

    rerender(
      <TwoDViewerCanvas
        adapter={adapter}
        pageIndex={0}
        viewport={{ ...initialTwoDViewportState, scale: 1.6 }}
        onViewportAction={vi.fn()}
        onPageCountResolved={vi.fn()}
        onRendered={onRendered}
      />,
    );

    expect(renderPage).toHaveBeenCalledTimes(1);
    await act(async () => {
      await Promise.resolve();
      vi.advanceTimersByTime(180);
      await Promise.resolve();
    });
    expect(renderPage).toHaveBeenCalledTimes(2);
    expect(renderPage).toHaveBeenNthCalledWith(2, 0, {
      maxDevicePixelRatio: 3.2,
      targetWidthPx: 1536,
    });
    renderResolvers.shift()?.resolve(createLabeledCanvasPage("enhanced", 1536, 1152));
    await act(async () => {
      await Promise.resolve();
    });

    expect(container.querySelector(".viewer-dom-source")?.getAttribute("data-label")).toBe("base");
    fireEvent.pointerUp(stage!, { pointerId: 7, isPrimary: true, clientX: 200, clientY: 200 });
    await act(async () => {
      await Promise.resolve();
    });
    expect(container.querySelector(".viewer-dom-source")?.getAttribute("data-label")).toBe("enhanced");
    expect(onRendered).toHaveBeenCalledTimes(2);
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("loads a new page only when pageIndex changes", async () => {
    const { adapter, renderPage } = createAdapter();
    const onRendered = vi.fn();
    const { rerender } = render(
      <TwoDViewerCanvas
        adapter={adapter}
        pageIndex={0}
        viewport={initialTwoDViewportState}
        onViewportAction={vi.fn()}
        onPageCountResolved={vi.fn()}
        onRendered={onRendered}
      />,
    );

    await waitFor(() => expect(renderPage).toHaveBeenNthCalledWith(1, 0, undefined));
    await waitFor(() => expect(onRendered).toHaveBeenCalledTimes(1));

    rerender(
      <TwoDViewerCanvas
        adapter={adapter}
        pageIndex={1}
        viewport={initialTwoDViewportState}
        onViewportAction={vi.fn()}
        onPageCountResolved={vi.fn()}
        onRendered={onRendered}
      />,
    );

    await waitFor(() => expect(renderPage).toHaveBeenNthCalledWith(2, 1, undefined));
    await waitFor(() => expect(onRendered).toHaveBeenCalledTimes(2));
  });

  it("rerenders only when the stage width crosses a 256px bucket", async () => {
    const { adapter, renderPage } = createDynamicAdapter();
    render(
      <TwoDViewerCanvas
        adapter={adapter}
        pageIndex={0}
        viewport={initialTwoDViewportState}
        onViewportAction={vi.fn()}
        onPageCountResolved={vi.fn()}
        onRendered={vi.fn()}
      />,
    );

    await waitFor(() =>
      expect(renderPage).toHaveBeenNthCalledWith(1, 0, {
        maxDevicePixelRatio: 2,
        targetWidthPx: 1024,
      }),
    );

    stageWidth = 1000;
    ResizeObserverMock.triggerAll();
    await waitFor(() => expect(renderPage).toHaveBeenCalledTimes(1));

    stageWidth = 1100;
    ResizeObserverMock.triggerAll();
    await waitFor(() =>
      expect(renderPage).toHaveBeenNthCalledWith(2, 0, {
        maxDevicePixelRatio: 2,
        targetWidthPx: 1280,
      }),
    );
  });

  it("keeps the current page until wheel interaction becomes idle, then applies the enhanced page", async () => {
    const { adapter, renderPage, renderResolvers } = createDeferredDynamicAdapter();
    const { container } = render(<Harness adapter={adapter} />);

    await waitFor(() => expect(renderPage).toHaveBeenCalledTimes(1));
    renderResolvers.shift()?.resolve(createLabeledCanvasPage("base", 1024, 768));
    await act(async () => {
      await Promise.resolve();
    });

    vi.useFakeTimers();

    const stage = container.querySelector(".viewer-stage-document");
    expect(stage).not.toBeNull();

    await act(async () => {
      fireEvent.wheel(stage!, { deltaY: -100, clientX: 300, clientY: 240 });
      fireEvent.wheel(stage!, { deltaY: -100, clientX: 300, clientY: 240 });
      await Promise.resolve();
    });

    expect(container.querySelector(".viewer-dom-source")?.getAttribute("data-label")).toBe("base");
    expect(renderPage).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(179);
      await Promise.resolve();
    });
    expect(renderPage).toHaveBeenCalledTimes(1);
    expect(container.querySelector(".viewer-dom-source")?.getAttribute("data-label")).toBe("base");

    await act(async () => {
      vi.advanceTimersByTime(1);
      await Promise.resolve();
    });
    expect(renderPage).toHaveBeenCalledTimes(2);
    renderResolvers.shift()?.resolve(createLabeledCanvasPage("enhanced", 1280, 960));
    await act(async () => {
      await Promise.resolve();
    });

    expect(container.querySelector(".viewer-dom-source")?.getAttribute("data-label")).toBe("enhanced");
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });
});
