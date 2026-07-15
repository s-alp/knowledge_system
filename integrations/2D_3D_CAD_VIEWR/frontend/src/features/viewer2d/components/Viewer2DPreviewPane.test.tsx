import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Viewer2DPreviewPane } from "./Viewer2DPreviewPane";

vi.mock("./TwoDViewerCanvas", () => ({
  TwoDViewerCanvas: ({
    pageIndex,
    viewport,
    onStageSizeChange,
    onViewportAction,
  }: {
    pageIndex: number;
    viewport: {
      scale: number;
      rotation: number;
      offsetX: number;
      offsetY: number;
    };
    onStageSizeChange?: (width: number, height: number) => void;
    onViewportAction: (action: { type: "pan"; deltaX: number; deltaY: number }) => void;
  }) => {
    useEffect(() => {
      onStageSizeChange?.(960, 640);
    }, [onStageSizeChange]);

    return (
      <>
        <div data-testid="viewport-probe">
          {`${pageIndex}:${viewport.scale}:${viewport.rotation}:${viewport.offsetX}:${viewport.offsetY}`}
        </div>
        <button type="button" onClick={() => onViewportAction({ type: "pan", deltaX: 100, deltaY: 50 })}>
          pan
        </button>
      </>
    );
  },
}));

afterEach(() => {
  cleanup();
});

describe("Viewer2DPreviewPane", () => {
  it("keeps zoom, rotate, and reset inside the preview pane", () => {
    render(
      <Viewer2DPreviewPane
        adapter={null}
        pageIndex={0}
        currentPage={1}
        pageCount={3}
        onPreviousPage={vi.fn()}
        onNextPage={vi.fn()}
        onPageCountResolved={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByLabelText("拡大"));
    fireEvent.click(screen.getByLabelText("右回転"));
    expect(screen.getByTestId("viewport-probe")).toHaveTextContent("0:1.1:90:0:0");

    fireEvent.click(screen.getByLabelText("リセット"));
    expect(screen.getByTestId("viewport-probe")).toHaveTextContent("0:1:0:0:0");
  });

  it("uses the stage center as the toolbar zoom anchor", () => {
    render(
      <Viewer2DPreviewPane
        adapter={null}
        pageIndex={0}
        currentPage={1}
        pageCount={3}
        onPreviousPage={vi.fn()}
        onNextPage={vi.fn()}
        onPageCountResolved={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText("pan"));
    expect(screen.getByTestId("viewport-probe")).toHaveTextContent("0:1:0:100:50");

    fireEvent.click(screen.getByLabelText("拡大"));
    expect(screen.getByTestId("viewport-probe")).toHaveTextContent("0:1.1:0:110:55");
  });

  it("resets the viewport when the page changes", async () => {
    const { rerender } = render(
      <Viewer2DPreviewPane
        adapter={null}
        pageIndex={0}
        currentPage={1}
        pageCount={3}
        onPreviousPage={vi.fn()}
        onNextPage={vi.fn()}
        onPageCountResolved={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByLabelText("拡大"));
    expect(screen.getByTestId("viewport-probe")).toHaveTextContent("0:1.1:0:0:0");

    rerender(
      <Viewer2DPreviewPane
        adapter={null}
        pageIndex={1}
        currentPage={2}
        pageCount={3}
        onPreviousPage={vi.fn()}
        onNextPage={vi.fn()}
        onPageCountResolved={vi.fn()}
      />,
    );

    await waitFor(() => expect(screen.getByTestId("viewport-probe")).toHaveTextContent("1:1:0:0:0"));
  });
});
