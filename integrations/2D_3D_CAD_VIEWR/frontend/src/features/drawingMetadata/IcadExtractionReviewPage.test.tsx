import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  enqueueDrawingMetadataExtraction,
  uploadIcadDrawingMetadata,
  type DrawingMetadataRegistrationResponse,
} from "../../shared/api/client";
import { IcadExtractionReviewPage } from "./IcadExtractionReviewPage";

vi.mock("../../shared/api/client", () => ({
  uploadIcadDrawingMetadata: vi.fn(),
  getDrawingMetadataRegistration: vi.fn(async () => registration),
  enqueueDrawingMetadataExtraction: vi.fn(async (_drawingId: string, extractionMode: "2d" | "3d") => ({
    jobId: `job-${extractionMode}`,
    drawingId: "drawing-1",
    extractionMode,
    status: "queued",
    extractionProfile: "2d_all_views_layers_print_frame",
    extractionOptions: {},
    errorMessage: "",
  })),
  applyDrawingMetadataOverrides: vi.fn(async () => ({
    drawingId: "drawing-1",
    extractionMode: "2d",
    manualOverrides: {},
    canonicalAttributes: {},
    derivedTags: [],
  })),
}));

const registration: DrawingMetadataRegistrationResponse = {
  drawingId: "drawing-1",
  filename: "sample.icd",
  sourcePath: "C:\\tmp\\sample.icd",
  sourceFormat: "icad",
  snapshotsByMode: {},
  viewerBootstrap: {
    drawingId: "drawing-1",
    title: "sample.icd",
    version: null,
    defaultMode: "3d",
    availability: { has2d: false, has3d: false },
    metadata: {
      tags: [],
      extractionDiagnostics: {
        schemaVersion: "viewer_extraction_diagnostics.v1",
        status: "not_extracted",
        missingModes: ["2d", "3d"],
        policy: "",
      },
    },
  },
};

describe("IcadExtractionReviewPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("registers the selected ICAD file and shows review, re-extract, and manual correction controls", async () => {
    vi.mocked(uploadIcadDrawingMetadata).mockResolvedValue(registration);
    const file = new File(["icad"], "sample.icd", { type: "application/octet-stream" });

    render(<IcadExtractionReviewPage file={file} onBack={vi.fn()} />);

    await waitFor(() => expect(uploadIcadDrawingMetadata).toHaveBeenCalledWith(file));
    expect(await screen.findByText("登録しました。抽出開始または条件付き再抽出を実行できます。")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "抽出・再抽出" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "レビュー" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "手直し" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "2D/3Dを抽出" }));
    await waitFor(() => expect(enqueueDrawingMetadataExtraction).toHaveBeenCalled());
  });
});
