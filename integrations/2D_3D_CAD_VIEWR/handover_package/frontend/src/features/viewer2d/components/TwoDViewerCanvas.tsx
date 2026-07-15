import { useEffect, useLayoutEffect, useRef, useState } from "react";

import type { RenderedPage, TwoDDocumentAdapter, TwoDRenderOptions } from "../adapters/types";
import type { TwoDViewportAction, TwoDViewportState } from "../state/viewer2dState";

interface TwoDViewerCanvasProps {
  adapter: TwoDDocumentAdapter | null;
  pageIndex: number;
  viewport: TwoDViewportState;
  onViewportAction: (action: TwoDViewportAction) => void;
  onPageCountResolved: (pageCount: number) => void;
  onStageSizeChange?: (width: number, height: number) => void;
  onRendered?: () => void;
}

interface LoadedPage {
  page: RenderedPage;
  pageIndex: number;
  renderKey: string;
}

interface StageSize {
  width: number;
  height: number;
}

const DEFAULT_STAGE_HEIGHT = 480;
const BASE_MAX_DEVICE_PIXEL_RATIO = 2;
const MAX_ENHANCED_OUTPUT_SCALE = 4;
const WIDTH_BUCKET_SIZE = 256;
const ENHANCED_RENDER_DEBOUNCE_MS = 180;
const ENHANCED_RENDER_THRESHOLD = 1.15;
const MAX_TARGET_RENDER_MULTIPLIER = 4;

function resolveStageSize(stage: HTMLElement | null): StageSize {
  const measuredWidth = stage?.clientWidth ?? 0;
  const measuredHeight = stage?.clientHeight ?? DEFAULT_STAGE_HEIGHT;

  return {
    width: measuredWidth,
    height: Math.max(measuredHeight, DEFAULT_STAGE_HEIGHT),
  };
}

function resolveWidthBucket(width: number): number | null {
  if (width <= 0) {
    return null;
  }
  return Math.ceil(width / WIDTH_BUCKET_SIZE) * WIDTH_BUCKET_SIZE;
}

function isRenderingCancelledError(error: unknown): boolean {
  return error instanceof Error && error.name === "RenderingCancelledException";
}

function isDirectDomSource(source: CanvasImageSource | null): source is HTMLCanvasElement | HTMLImageElement {
  return source instanceof HTMLCanvasElement || source instanceof HTMLImageElement;
}

export function TwoDViewerCanvas({
  adapter,
  pageIndex,
  viewport,
  onViewportAction,
  onPageCountResolved,
  onStageSizeChange,
  onRendered,
}: TwoDViewerCanvasProps) {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const surfaceHostRef = useRef<HTMLDivElement | null>(null);
  const [activePointerId, setActivePointerId] = useState<number | null>(null);
  const [isInteracting, setIsInteracting] = useState(false);
  const [displayedPage, setDisplayedPage] = useState<LoadedPage | null>(null);
  const [pendingRenderedPage, setPendingRenderedPage] = useState<LoadedPage | null>(null);
  const [stageSize, setStageSize] = useState<StageSize>({ width: 0, height: 480 });
  const lastPoint = useRef<{ x: number; y: number } | null>(null);
  const activePointerIdRef = useRef<number | null>(null);
  const displayedPageRef = useRef<LoadedPage | null>(null);
  const pendingRenderedPageRef = useRef<LoadedPage | null>(null);
  const interactionIdleTimerIdRef = useRef<number | null>(null);
  const isInteractingRef = useRef(false);
  const wheelInteractingRef = useRef(false);
  const pageRequestSequence = useRef(0);
  const lastResolvedPageCount = useRef<number | null>(null);
  const lastNotifiedRenderKey = useRef<string | null>(null);
  const baseWidthBucket = resolveWidthBucket(stageSize.width);
  const renderWidthBucket = adapter?.supportsDynamicResolution ? baseWidthBucket : 1;
  const enhancedTargetWidth = resolveWidthBucket(
    stageSize.width * Math.min(Math.max(viewport.scale, 1), MAX_TARGET_RENDER_MULTIPLIER),
  );
  const directDomSource: HTMLCanvasElement | HTMLImageElement | null =
    displayedPage && isDirectDomSource(displayedPage.page.source) ? displayedPage.page.source : null;
  const dragging = activePointerId !== null;
  const hasPendingRenderedPage = pendingRenderedPage !== null;

  const clearInteractionIdleTimer = () => {
    if (interactionIdleTimerIdRef.current === null) {
      return;
    }
    window.clearTimeout(interactionIdleTimerIdRef.current);
    interactionIdleTimerIdRef.current = null;
  };

  const flushPendingRenderedPage = () => {
    if (!pendingRenderedPageRef.current) {
      return;
    }
    const nextDisplayedPage = pendingRenderedPageRef.current;
    pendingRenderedPageRef.current = null;
    displayedPageRef.current = nextDisplayedPage;
    setPendingRenderedPage(null);
    setDisplayedPage(nextDisplayedPage);
  };

  const syncInteractionState = () => {
    const nextInteracting = activePointerIdRef.current !== null || wheelInteractingRef.current;
    isInteractingRef.current = nextInteracting;
    setIsInteracting(nextInteracting);
    if (!nextInteracting) {
      flushPendingRenderedPage();
    }
  };

  const commitRenderedPage = (nextPage: LoadedPage) => {
    const currentDisplayedPage = displayedPageRef.current;
    const canDefer =
      isInteractingRef.current &&
      currentDisplayedPage !== null &&
      currentDisplayedPage.pageIndex === nextPage.pageIndex;
    if (canDefer) {
      pendingRenderedPageRef.current = nextPage;
      setPendingRenderedPage(nextPage);
      return;
    }
    pendingRenderedPageRef.current = null;
    displayedPageRef.current = nextPage;
    setPendingRenderedPage(null);
    setDisplayedPage(nextPage);
  };

  const scheduleWheelInteractionIdle = () => {
    wheelInteractingRef.current = true;
    syncInteractionState();
    clearInteractionIdleTimer();
    interactionIdleTimerIdRef.current = window.setTimeout(() => {
      wheelInteractingRef.current = false;
      interactionIdleTimerIdRef.current = null;
      syncInteractionState();
    }, ENHANCED_RENDER_DEBOUNCE_MS);
  };

  useEffect(() => {
    // TIFF の複数ページ対応でも toolbar は pageCount だけ見ればよいようにする。
    const nextPageCount = adapter?.pageCount ?? 0;
    if (lastResolvedPageCount.current === nextPageCount) {
      return;
    }
    lastResolvedPageCount.current = nextPageCount;
    onPageCountResolved(nextPageCount);
  }, [adapter, onPageCountResolved]);

  useEffect(() => {
    onStageSizeChange?.(stageSize.width, stageSize.height);
  }, [onStageSizeChange, stageSize.height, stageSize.width]);

  useLayoutEffect(() => {
    const stage = stageRef.current;
    if (!stage) {
      return;
    }

    const updateStageSize = () => {
      const nextStageSize = resolveStageSize(stage);
      setStageSize((currentStageSize) =>
        currentStageSize.width === nextStageSize.width && currentStageSize.height === nextStageSize.height
          ? currentStageSize
          : nextStageSize,
      );
    };

    updateStageSize();
    if (typeof ResizeObserver === "undefined") {
      return;
    }

    const observer = new ResizeObserver(() => {
      updateStageSize();
    });
    observer.observe(stage);

    return () => {
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    pendingRenderedPageRef.current = null;
    displayedPageRef.current = null;
    setPendingRenderedPage(null);
    setDisplayedPage(null);
    activePointerIdRef.current = null;
    setActivePointerId(null);
    setIsInteracting(false);
    isInteractingRef.current = false;
    wheelInteractingRef.current = false;
    lastPoint.current = null;
    clearInteractionIdleTimer();
    lastNotifiedRenderKey.current = null;
  }, [adapter, pageIndex]);

  useEffect(
    () => () => {
      clearInteractionIdleTimer();
    },
    [],
  );

  useEffect(() => {
    if (!adapter) {
      pendingRenderedPageRef.current = null;
      displayedPageRef.current = null;
      setPendingRenderedPage(null);
      setDisplayedPage(null);
      lastNotifiedRenderKey.current = null;
      return;
    }
    if (!renderWidthBucket) {
      return;
    }

    const currentAdapter = adapter;
    const renderOptions: TwoDRenderOptions | undefined = adapter.supportsDynamicResolution
      ? {
          targetWidthPx: renderWidthBucket,
          maxDevicePixelRatio: BASE_MAX_DEVICE_PIXEL_RATIO,
        }
      : undefined;
    let cancelled = false;
    const requestKey = `base:${++pageRequestSequence.current}:${renderWidthBucket}`;

    async function loadPage() {
      try {
        // PDF / JPEG / TIFF の差分は adapter に閉じ込め、canvas 側は描画済み page を受け取るだけにする。
        const page = await currentAdapter.renderPage(pageIndex, renderOptions);
        if (cancelled) {
          return;
        }
        commitRenderedPage({ page, pageIndex, renderKey: requestKey });
      } catch (error) {
        if (cancelled || isRenderingCancelledError(error)) {
          return;
        }
        throw error;
      }
    }

    void loadPage();
    return () => {
      cancelled = true;
    };
  }, [adapter, pageIndex, renderWidthBucket]);

  useEffect(() => {
    if (!adapter || !baseWidthBucket || !enhancedTargetWidth) {
      return;
    }
    if (!adapter.supportsDynamicResolution) {
      return;
    }
    if (viewport.scale < ENHANCED_RENDER_THRESHOLD) {
      return;
    }

    const currentAdapter = adapter;
    const enhancedOutputScale = Math.min(Math.max(BASE_MAX_DEVICE_PIXEL_RATIO * viewport.scale, BASE_MAX_DEVICE_PIXEL_RATIO), MAX_ENHANCED_OUTPUT_SCALE);
    const renderOptions: TwoDRenderOptions = {
      targetWidthPx: enhancedTargetWidth,
      maxDevicePixelRatio: enhancedOutputScale,
    };
    let cancelled = false;
    const requestKey = `enhanced:${++pageRequestSequence.current}:${enhancedTargetWidth}:${enhancedOutputScale.toFixed(2)}`;
    const timerId = window.setTimeout(() => {
      const loadEnhancedPage = async () => {
        try {
          const page = await currentAdapter.renderPage(pageIndex, renderOptions);
          if (cancelled) {
            return;
          }
          commitRenderedPage({ page, pageIndex, renderKey: requestKey });
        } catch (error) {
          if (cancelled || isRenderingCancelledError(error)) {
            return;
          }
          throw error;
        }
      };

      void loadEnhancedPage();
    }, ENHANCED_RENDER_DEBOUNCE_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [adapter, baseWidthBucket, enhancedTargetWidth, pageIndex, viewport.scale]);

  useEffect(() => {
    if (!directDomSource || !displayedPage) {
      return;
    }
    if (lastNotifiedRenderKey.current === displayedPage.renderKey) {
      return;
    }
    lastNotifiedRenderKey.current = displayedPage.renderKey;
    onRendered?.();
  }, [directDomSource, displayedPage, onRendered]);

  useEffect(() => {
    const host = surfaceHostRef.current;
    if (!host) {
      return;
    }
    if (!directDomSource) {
      host.replaceChildren();
      return;
    }

    directDomSource.classList.add("viewer-dom-source");
    if (host.firstChild !== directDomSource) {
      host.replaceChildren(directDomSource);
    }

    return () => {
      if (host.firstChild === directDomSource) {
        host.replaceChildren();
      }
    };
  }, [directDomSource]);

  useEffect(() => {
    if (!directDomSource || !displayedPage) {
      return;
    }

    directDomSource.style.width = `${displayedPage.page.width}px`;
    directDomSource.style.height = `${displayedPage.page.height}px`;
    directDomSource.style.transform = `translate(${viewport.offsetX}px, ${viewport.offsetY}px) rotate(${viewport.rotation}deg) scale(${viewport.scale / (displayedPage.page.renderScale ?? 1)})`;
  }, [directDomSource, displayedPage, viewport]);

  const handleWheel = (event: React.WheelEvent<HTMLElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const stage = stageRef.current;
    const rect = stage?.getBoundingClientRect();
    const stageWidth = rect?.width ?? stageSize.width;
    const stageHeight = rect?.height ?? stageSize.height;
    const anchorX = rect ? event.clientX - rect.left : stageWidth / 2;
    const anchorY = rect ? event.clientY - rect.top : stageHeight / 2;
    scheduleWheelInteractionIdle();
    onViewportAction({
      type: "zoomAt",
      delta: event.deltaY > 0 ? -0.1 : 0.1,
      anchorX,
      anchorY,
      stageWidth,
      stageHeight,
    });
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLElement>) => {
    if (event.isPrimary === false || event.button !== 0) {
      return;
    }
    event.preventDefault();
    clearInteractionIdleTimer();
    wheelInteractingRef.current = false;
    activePointerIdRef.current = event.pointerId;
    setActivePointerId(event.pointerId);
    event.currentTarget.setPointerCapture(event.pointerId);
    lastPoint.current = { x: event.clientX, y: event.clientY };
    syncInteractionState();
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLElement>) => {
    if (activePointerIdRef.current !== event.pointerId || !lastPoint.current) {
      return;
    }
    event.preventDefault();
    const deltaX = event.clientX - lastPoint.current.x;
    const deltaY = event.clientY - lastPoint.current.y;
    lastPoint.current = { x: event.clientX, y: event.clientY };
    onViewportAction({ type: "pan", deltaX, deltaY });
  };

  const finishPointerInteraction = (event: React.PointerEvent<HTMLElement>) => {
    if (activePointerIdRef.current !== event.pointerId) {
      return;
    }
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    activePointerIdRef.current = null;
    setActivePointerId(null);
    lastPoint.current = null;
    syncInteractionState();
  };

  const stageClassName = [
    "viewer-stage",
    "viewer-stage-document",
    dragging ? "dragging" : "",
    isInteracting ? "interacting" : "",
    hasPendingRenderedPage ? "pending-render" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="viewer-display-shell">
      <div
        ref={stageRef}
        className={stageClassName}
        onWheelCapture={(event) => {
          event.preventDefault();
        }}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishPointerInteraction}
        onPointerCancel={finishPointerInteraction}
      >
        <div ref={surfaceHostRef} className="viewer-dom-surface" aria-hidden="true" />
      </div>
    </div>
  );
}
