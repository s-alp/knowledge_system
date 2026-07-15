import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useViewerSourceLoader } from "./useViewerSourceLoader";

function HookHarness(props: {
  openFromUrl: (url: string) => Promise<{ nextPhase: "processing" | "rendering" }>;
  openFromFile: (file: File) => Promise<{ nextPhase: "processing" | "rendering" }>;
  onSuccess?: () => void;
}) {
  const controller = useViewerSourceLoader({
    openFromUrl: props.openFromUrl,
    openFromFile: props.openFromFile,
    resolveSuccessPhase: (response) => response.nextPhase,
    onSuccess: () => props.onSuccess?.(),
    urlErrorMessage: "url failed",
    fileErrorMessage: "file failed",
  });

  return (
    <div>
      <input
        aria-label="url"
        value={controller.url}
        onChange={(event) => controller.setUrl(event.target.value)}
      />
      <button type="button" onClick={() => void controller.handleOpenUrl()}>
        open-url
      </button>
      <button type="button" onClick={controller.handlePickStart}>
        pick-start
      </button>
      <button
        type="button"
        onClick={() => {
          controller.handleFileChange(new File(["mesh"], "mesh.stl", { type: "model/stl" }));
          controller.handlePickComplete(new File(["mesh"], "mesh.stl", { type: "model/stl" }));
        }}
      >
        pick-file
      </button>
      <button type="button" onClick={() => controller.handlePickComplete(null)}>
        cancel-pick
      </button>
      <span>{controller.phase}</span>
      <span>{controller.localFileStatus ?? "no-status"}</span>
      <span>{controller.formError ?? "no-error"}</span>
    </div>
  );
}

describe("useViewerSourceLoader", () => {
  afterEach(() => {
    cleanup();
  });

  it("opens URL and advances to the success phase", async () => {
    const onSuccess = vi.fn();
    const openFromUrl = vi.fn().mockResolvedValue({ nextPhase: "processing" as const });

    render(
      <HookHarness
        openFromUrl={openFromUrl}
        openFromFile={vi.fn()}
        onSuccess={onSuccess}
      />,
    );

    fireEvent.change(screen.getByLabelText("url"), { target: { value: "https://example.com/file.pdf" } });
    fireEvent.click(screen.getByText("open-url"));

    await waitFor(() => expect(screen.getByText("processing")).toBeInTheDocument());
    expect(openFromUrl).toHaveBeenCalledWith("https://example.com/file.pdf");
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });

  it("uploads the selected file immediately after the picker resolves", async () => {
    const openFromFile = vi.fn().mockResolvedValue({ nextPhase: "rendering" as const });

    render(<HookHarness openFromUrl={vi.fn()} openFromFile={openFromFile} />);

    fireEvent.click(screen.getByText("pick-start"));
    expect(screen.getByText("ファイル選択ダイアログを開いています。")).toBeInTheDocument();

    fireEvent.click(screen.getByText("pick-file"));

    await waitFor(() => expect(screen.getByText("rendering")).toBeInTheDocument());
    expect(openFromFile).toHaveBeenCalledTimes(1);
  });

  it("returns to idle when the picker is cancelled", () => {
    render(<HookHarness openFromUrl={vi.fn()} openFromFile={vi.fn()} />);

    fireEvent.click(screen.getByText("cancel-pick"));

    expect(screen.getByText("idle")).toBeInTheDocument();
    expect(screen.getByText("no-status")).toBeInTheDocument();
  });
});
