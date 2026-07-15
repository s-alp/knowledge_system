import { useCallback, useEffect, useReducer, useState } from "react";

import type { TwoDDocumentAdapter } from "../adapters/types";
import { Viewer2DToolbar } from "../controls/Viewer2DToolbar";
import { initialTwoDViewportState, twoDViewportReducer } from "../state/viewer2dState";
import { TwoDViewerCanvas } from "./TwoDViewerCanvas";

interface Viewer2DPreviewPaneProps {
  adapter: TwoDDocumentAdapter | null;
  pageIndex: number;
  currentPage: number;
  pageCount: number;
  onPreviousPage: () => void;
  onNextPage: () => void;
  onPageCountResolved: (pageCount: number) => void;
  onRendered?: () => void;
}

export function Viewer2DPreviewPane({
  adapter,
  pageIndex,
  currentPage,
  pageCount,
  onPreviousPage,
  onNextPage,
  onPageCountResolved,
  onRendered,
}: Viewer2DPreviewPaneProps) {
  const [viewport, dispatchViewport] = useReducer(twoDViewportReducer, initialTwoDViewportState);
  const [stageSize, setStageSize] = useState({ width: 0, height: 480 });
  const handleStageSizeChange = useCallback((width: number, height: number) => {
    setStageSize((currentStageSize) =>
      currentStageSize.width === width && currentStageSize.height === height ? currentStageSize : { width, height },
    );
  }, []);

  useEffect(() => {
    dispatchViewport({ type: "reset" });
  }, [adapter, pageIndex]);

  const canZoomIn = viewport.scale < 8;
  const canZoomOut = viewport.scale > 0.2;
  const handleCenteredZoom = (delta: number) => {
    if (stageSize.width <= 0) {
      dispatchViewport({ type: "zoom", delta });
      return;
    }

    dispatchViewport({
      type: "zoomAt",
      delta,
      anchorX: stageSize.width / 2,
      anchorY: stageSize.height / 2,
      stageWidth: stageSize.width,
      stageHeight: stageSize.height,
    });
  };

  return (
    <>
      <Viewer2DToolbar
        currentPage={currentPage}
        pageCount={pageCount}
        onPreviousPage={() => {
          dispatchViewport({ type: "reset" });
          onPreviousPage();
        }}
        onNextPage={() => {
          dispatchViewport({ type: "reset" });
          onNextPage();
        }}
        onZoomIn={() => handleCenteredZoom(0.1)}
        onZoomOut={() => handleCenteredZoom(-0.1)}
        onResetView={() => dispatchViewport({ type: "reset" })}
        onRotateLeft={() => dispatchViewport({ type: "rotate", direction: "left" })}
        onRotateRight={() => dispatchViewport({ type: "rotate", direction: "right" })}
        canZoomIn={canZoomIn}
        canZoomOut={canZoomOut}
      />
      <TwoDViewerCanvas
        adapter={adapter}
        pageIndex={pageIndex}
        viewport={viewport}
        onViewportAction={dispatchViewport}
        onPageCountResolved={onPageCountResolved}
        onStageSizeChange={handleStageSizeChange}
        onRendered={onRendered}
      />
    </>
  );
}
