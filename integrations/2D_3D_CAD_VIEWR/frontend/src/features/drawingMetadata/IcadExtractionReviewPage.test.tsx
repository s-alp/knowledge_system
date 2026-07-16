import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  applyDrawingMetadataReview,
  enqueueDrawingMetadataExtraction,
  getDrawingMetadataJob,
  registerIcadDrawingMetadataPath,
  uploadIcadDrawingMetadata,
  type DrawingMetadataRegistrationResponse,
} from "../../shared/api/client";
import { IcadExtractionReviewPage } from "./IcadExtractionReviewPage";

vi.mock("../../shared/api/client", () => ({
  uploadIcadDrawingMetadata: vi.fn(),
  registerIcadDrawingMetadataPath: vi.fn(),
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
  getDrawingMetadataJob: vi.fn(async (jobId: string) => ({
    jobId,
    drawingId: "drawing-1",
    extractionMode: jobId.endsWith("3d") ? "3d" : "2d",
    status: "succeeded",
    extractionProfile: "default",
    extractionOptions: {},
    errorMessage: "",
  })),
  applyDrawingMetadataReview: vi.fn(async (_drawingId: string, extractionMode: "2d" | "3d", decision: string) => ({
    drawingId: "drawing-1",
    extractionMode,
    reviewStatus: decision,
    reviewedAt: "2026-07-15T12:00:00+09:00",
    reviewedBy: "api",
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
  latestJobsByMode: {},
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
    cleanup();
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

  it("restores the latest queued job after registration reload and prevents duplicate extraction", async () => {
    vi.mocked(getDrawingMetadataJob).mockResolvedValue({
      jobId: "job-existing-3d",
      drawingId: "drawing-1",
      extractionMode: "3d",
      status: "queued",
      extractionProfile: "3d_model_part_attributes",
      extractionOptions: {},
      errorMessage: "",
    });
    vi.mocked(uploadIcadDrawingMetadata).mockResolvedValue({
      ...registration,
      latestJobsByMode: {
        "3d": {
          jobId: "job-existing-3d",
          drawingId: "drawing-1",
          extractionMode: "3d",
          status: "queued",
          extractionProfile: "3d_model_part_attributes",
          extractionOptions: {},
          errorMessage: "",
        },
      },
    });
    const file = new File(["icad"], "sample.icd", { type: "application/octet-stream" });

    render(<IcadExtractionReviewPage file={file} onBack={vi.fn()} />);

    expect(await screen.findByText("job-existing-3d")).toBeInTheDocument();
    expect(screen.getByText("待機中")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "2D/3Dを抽出" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "3D条件で再抽出" }));
    expect(enqueueDrawingMetadataExtraction).not.toHaveBeenCalled();
  });

  it("shows a concise failure reason and keeps the raw stack trace inside details", async () => {
    const rawError = [
      "error[0].type=System.Reflection.TargetInvocationException",
      "error[1].type=sxnet.SxException",
      "error[1].message=指定したファイルは図面ファイルではありません。",
      "error.stack_trace_begin",
      "System.Reflection.TargetInvocationException: 呼び出しのターゲットが例外をスローしました。",
      "場所 IcadExtraction.SxNet.SxNetOpenContext.OpenReadOnly",
      "error.stack_trace_end",
    ].join("\n");
    vi.mocked(uploadIcadDrawingMetadata).mockResolvedValue({
      ...registration,
      latestJobsByMode: {
        "2d": {
          jobId: "job-failed-2d",
          drawingId: "drawing-1",
          extractionMode: "2d",
          status: "failed",
          extractionProfile: "2d_all_views_layers_print_frame",
          extractionOptions: {},
          errorMessage: rawError,
          createdAt: "2026-07-16T09:07:00Z",
          startedAt: "2026-07-16T09:07:10Z",
          finishedAt: "2026-07-16T09:07:40Z",
          updatedAt: "2026-07-16T09:07:40Z",
          diagnostics: {
            failure: {
              errorClass: "sxnet_rejected_as_not_drawing_file",
              sourcePreflight: {
                sourcePathLength: 312,
                sourcePathWithinSxnetLegacyLimit: false,
                requiresSxnetStagedInput: true,
                filenameLength: 10,
                filenameWithinWindowsLimit: true,
                extensionIsIcd: true,
                sourceExistsFromCurrentMachine: true,
              },
              reextractCondition: "長い原本パスは短い一時パスへ退避済み/退避対象です。",
            },
          },
        },
      },
    });
    const file = new File(["icad"], "sample.icd", { type: "application/octet-stream" });

    render(<IcadExtractionReviewPage file={file} onBack={vi.fn()} />);

    expect(await screen.findByText("job-failed-2d")).toBeInTheDocument();
    expect(screen.getByText("ICDファイルですが、ICAD/SXNETが図面モデルとして開けません。原本パス、外部参照、ICAD対応版を確認してください。")).toBeInTheDocument();
    expect(screen.getByText("原本:可 / 長パス退避:可 / パス長:312 / 上限超過 / ファイル名長:10")).toBeInTheDocument();
    expect(screen.getByText(/SxNetOpenContext.OpenReadOnly/)).toBeInTheDocument();
  });

  it("registers an original ICAD path without uploading a browser copy", async () => {
    vi.mocked(registerIcadDrawingMetadataPath).mockResolvedValue(registration);

    render(<IcadExtractionReviewPage file={null} sourcePath={"J:\\PROJECT\\sample.icd"} onBack={vi.fn()} />);

    await waitFor(() => expect(registerIcadDrawingMetadataPath).toHaveBeenCalledWith("J:\\PROJECT\\sample.icd"));
    expect(uploadIcadDrawingMetadata).not.toHaveBeenCalled();
    expect(await screen.findByText("登録しました。抽出開始または条件付き再抽出を実行できます。")).toBeInTheDocument();
  });

  it("confirms an extracted candidate from the dedicated review screen", async () => {
    vi.mocked(uploadIcadDrawingMetadata).mockResolvedValue({
      ...registration,
      snapshotsByMode: {
        "3d": {
          extractionMode: "3d",
          canonicalAttributes: { material: "SUS304" },
          derivedTags: [{ tag: "材質:SUS304" }],
          manualOverrides: {},
          latestJob: null,
          reviewStatus: "pending",
          reviewedAt: null,
          reviewedBy: "",
        },
      },
    });
    const file = new File(["icad"], "sample.icd", { type: "application/octet-stream" });

    render(<IcadExtractionReviewPage file={file} onBack={vi.fn()} />);

    const confirmButtons = await screen.findAllByRole("button", { name: "候補を確定" });
    const enabledConfirmButton = confirmButtons.find((button) => !(button as HTMLButtonElement).disabled);
    expect(enabledConfirmButton).toBeDefined();
    fireEvent.click(enabledConfirmButton!);
    await waitFor(() => {
      expect(applyDrawingMetadataReview).toHaveBeenCalledWith(
        "drawing-1",
        "3d",
        "confirmed",
        "図面管理で候補内容を確認",
      );
    });
  });
});
