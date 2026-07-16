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

    expect(screen.getByText("図面を開く")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "ICADからタグ・属性を取得" })).toBeInTheDocument();
    expect(screen.getByText("ICAD原本パス")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ICADファイルを選択" })).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "タグ・属性取得へ進む" })).toBeDisabled();
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
    fireEvent.click(screen.getByRole("button", { name: "タグ・属性取得へ進む" }));

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

    fireEvent.change(screen.getByLabelText("ICAD原本パス"), {
      target: { value: "J:\\PROJECT\\sample.icd" },
    });
    fireEvent.click(screen.getByRole("button", { name: "タグ・属性取得へ進む" }));

    expect(handleIcadMetadataLaunch).toHaveBeenCalledWith({ file: null, sourcePath: "J:\\PROJECT\\sample.icd" });
  });
});
