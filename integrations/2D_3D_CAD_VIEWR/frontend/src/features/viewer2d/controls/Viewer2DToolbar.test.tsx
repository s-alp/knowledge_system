import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Viewer2DToolbar } from "./Viewer2DToolbar";

describe("Viewer2DToolbar", () => {
  it("renders page info and triggers navigation", () => {
    const onPreviousPage = vi.fn();
    const onNextPage = vi.fn();
    const onZoomIn = vi.fn();
    const onZoomOut = vi.fn();
    const onResetView = vi.fn();
    const onRotateLeft = vi.fn();
    const onRotateRight = vi.fn();
    render(
      <Viewer2DToolbar
        currentPage={2}
        pageCount={5}
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
        onZoomIn={onZoomIn}
        onZoomOut={onZoomOut}
        onResetView={onResetView}
        onRotateLeft={onRotateLeft}
        onRotateRight={onRotateRight}
        canZoomIn
        canZoomOut
      />,
    );

    fireEvent.click(screen.getByLabelText("戻る"));
    fireEvent.click(screen.getByLabelText("進む"));
    fireEvent.click(screen.getByLabelText("拡大"));
    fireEvent.click(screen.getByLabelText("縮小"));
    fireEvent.click(screen.getByLabelText("リセット"));
    fireEvent.click(screen.getByLabelText("左回転"));
    fireEvent.click(screen.getByLabelText("右回転"));

    expect(screen.getByText("ページ 2/5")).toBeInTheDocument();
    expect(onPreviousPage).toHaveBeenCalledTimes(1);
    expect(onNextPage).toHaveBeenCalledTimes(1);
    expect(onZoomIn).toHaveBeenCalledTimes(1);
    expect(onZoomOut).toHaveBeenCalledTimes(1);
    expect(onResetView).toHaveBeenCalledTimes(1);
    expect(onRotateLeft).toHaveBeenCalledTimes(1);
    expect(onRotateRight).toHaveBeenCalledTimes(1);
  });
});
