import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Viewer3DToolbar } from "./Viewer3DToolbar";

describe("Viewer3DToolbar", () => {
  it("triggers top toolbar actions", () => {
    const onReset = vi.fn();
    const onZoomIn = vi.fn();
    const onZoomOut = vi.fn();
    const onToggleClipping = vi.fn();
    const onToggleEdgeHighlight = vi.fn();

    render(
      <Viewer3DToolbar
        clippingEnabled={false}
        edgeHighlightEnabled={false}
        onReset={onReset}
        onZoomIn={onZoomIn}
        onZoomOut={onZoomOut}
        onToggleClipping={onToggleClipping}
        onToggleEdgeHighlight={onToggleEdgeHighlight}
      />,
    );

    fireEvent.click(screen.getByLabelText("拡大"));
    fireEvent.click(screen.getByLabelText("縮小"));
    fireEvent.click(screen.getByLabelText("リセット"));
    fireEvent.click(screen.getByText("断面オン"));
    fireEvent.click(screen.getByText("輪郭強調 ON"));

    expect(onZoomIn).toHaveBeenCalledTimes(1);
    expect(onZoomOut).toHaveBeenCalledTimes(1);
    expect(onReset).toHaveBeenCalledTimes(1);
    expect(onToggleClipping).toHaveBeenCalledTimes(1);
    expect(onToggleEdgeHighlight).toHaveBeenCalledTimes(1);
  });
});
