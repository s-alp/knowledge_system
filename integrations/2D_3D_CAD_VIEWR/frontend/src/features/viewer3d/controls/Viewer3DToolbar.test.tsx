// このファイルは、Viewer3DToolbarの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
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
