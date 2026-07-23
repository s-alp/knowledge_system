import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DrawingEntryPanel } from "./DrawingEntryPanel";

describe("DrawingEntryPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows the ICAD tag and attribute extraction entry separately from drawing open actions", () => {
    const handleIcadMetadataLaunch = vi.fn();

    render(
      <DrawingEntryPanel
        debugInputsEnabled={false}
        onIcadMetadataLaunch={handleIcadMetadataLaunch}
        onLocalFileLaunch={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "図面を開く" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "ICADファイルからタグ・属性を取得" })).toBeInTheDocument();
    expect(screen.getByText("ICADファイルのパスを指定（推奨）")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ICADファイルを選択してアップロード" })).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "このICADを登録して抽出画面へ" })).toBeDisabled();
    expect(handleIcadMetadataLaunch).not.toHaveBeenCalled();
  });

  it("passes a selected ICAD file to the metadata extraction entry", () => {
    const handleIcadMetadataLaunch = vi.fn();
    const file = new File(["icad"], "sample.icd", { type: "application/octet-stream" });

    const { container } = render(
      <DrawingEntryPanel
        debugInputsEnabled={false}
        onIcadMetadataLaunch={handleIcadMetadataLaunch}
        onLocalFileLaunch={vi.fn()}
      />,
    );
    const icadFileInput = container.querySelector('input[type="file"][accept=".icd"]');

    fireEvent.change(icadFileInput as HTMLInputElement, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "このICADを登録して抽出画面へ" }));

    expect(handleIcadMetadataLaunch).toHaveBeenCalledWith({ file, sourcePath: "" });
  });

  it("passes an original ICAD path to the metadata extraction entry", () => {
    const handleIcadMetadataLaunch = vi.fn();

    render(
      <DrawingEntryPanel
        debugInputsEnabled={false}
        onIcadMetadataLaunch={handleIcadMetadataLaunch}
        onLocalFileLaunch={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText("ICADファイルのパスを指定（推奨）"), {
      target: { value: "J:\\PROJECT\\sample.icd" },
    });
    fireEvent.click(screen.getByRole("button", { name: "このICADを登録して抽出画面へ" }));

    expect(handleIcadMetadataLaunch).toHaveBeenCalledWith({ file: null, sourcePath: "J:\\PROJECT\\sample.icd" });
  });
});
