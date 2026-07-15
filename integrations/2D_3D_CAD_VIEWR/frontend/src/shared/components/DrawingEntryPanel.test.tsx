import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DrawingEntryPanel } from "./DrawingEntryPanel";

describe("DrawingEntryPanel", () => {
  it("shows the ICAD tag and attribute extraction entry separately from drawing open actions", () => {
    const handleIcadMetadataLaunch = vi.fn();

    render(
      <DrawingEntryPanel
        debugInputsEnabled={false}
        onIcadMetadataLaunch={handleIcadMetadataLaunch}
        onLocalFileLaunch={vi.fn()}
      />,
    );

    expect(screen.getByText("図面を開く")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "ICADからタグ・属性を取得" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ICADファイルを選択" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "タグ・属性取得へ進む" }));

    expect(handleIcadMetadataLaunch).toHaveBeenCalledTimes(1);
    expect(handleIcadMetadataLaunch).toHaveBeenCalledWith(null);
  });
});
