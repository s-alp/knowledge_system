// このファイルは、Viewer3DSectionControlsの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Viewer3DSectionControls } from "./Viewer3DSectionControls";

describe("Viewer3DSectionControls", () => {
  it("renders clipping values and triggers section callbacks", () => {
    const onAxisChange = vi.fn();
    const onValueChange = vi.fn();

    render(
      <Viewer3DSectionControls
        clippingAxis="z"
        clippingValue={0}
        clippingMin={-1}
        clippingMax={1}
        onAxisChange={onAxisChange}
        onValueChange={onValueChange}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("Z"), { target: { value: "x" } });
    fireEvent.change(screen.getByRole("slider"), { target: { value: "0.5" } });

    expect(screen.getByText("断面位置: 0.000 (-1.00 から 1.00)")).toBeInTheDocument();
    expect(onAxisChange).toHaveBeenCalledWith("x");
    expect(onValueChange).toHaveBeenCalledWith(0.5);
  });
});
