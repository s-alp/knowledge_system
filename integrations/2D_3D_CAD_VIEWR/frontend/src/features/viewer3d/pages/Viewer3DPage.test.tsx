import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { DrawingKnowledgeMock } from "../../../shared/mock/drawingKnowledge";
import type { DrawingBootstrapResponse, Open3DResponse } from "../../../shared/types/viewer";
import { Viewer3DPage } from "./Viewer3DPage";

vi.mock("../../../shared/api/client", () => ({
  openDrawingViewer3D: vi.fn(),
  openViewer3D: vi.fn(),
  uploadViewer3D: vi.fn(),
}));

vi.mock("../../../shared/components/DrawingOverviewPanel", () => ({
  DrawingOverviewPanel: ({ footerContent }: { footerContent: React.ReactNode }) => (
    <div data-testid="drawing-overview-panel">{footerContent}</div>
  ),
}));

vi.mock("../../../shared/components/LoadingNotice", () => ({
  LoadingNotice: () => <div>loading</div>,
}));

vi.mock("../../../shared/components/MetadataBar", () => ({
  MetadataBar: () => <div>metadata</div>,
}));

vi.mock("../../../shared/components/ViewerSourcePanel", () => ({
  ViewerSourcePanel: () => <div>viewer-source</div>,
}));

vi.mock("../../../shared/loadingMessages", () => ({
  getViewer3DLoadingMessage: () => null,
}));

vi.mock("../../../shared/mock/drawingKnowledge", async () => {
  const actual = await vi.importActual<typeof import("../../../shared/mock/drawingKnowledge")>(
    "../../../shared/mock/drawingKnowledge",
  );
  return {
    ...actual,
    buildDrawingInfoFields: () => [],
  };
});

vi.mock("../../../shared/hooks/useViewerSourceLoader", () => ({
  useViewerSourceLoader: () => ({
    url: "",
    selectedFile: null,
    formError: null,
    phase: "ready",
    localFileStatus: null,
    setUrl: vi.fn(),
    setPhase: vi.fn(),
    isBusy: false,
    handleOpenUrl: vi.fn(),
    handleFileChange: vi.fn(),
    handlePickStart: vi.fn(),
    handlePickComplete: vi.fn(),
    handleOpenExternalFile: vi.fn(),
  }),
}));

vi.mock("../hooks/useViewer3DJob", () => ({
  useViewer3DJob: () => ({
    job: {
      jobId: "job-1",
      filename: "sample.step",
      sourceExtension: "step",
      modelFormat: "stl",
      status: "ready",
      modelUrl: "/sample.stl",
      error: "",
    } satisfies Open3DResponse,
    error: null,
  }),
}));

vi.mock("../components/ThreeDViewerScene", () => ({
  ThreeDViewerScene: () => <div data-testid="viewer-3d-scene">scene</div>,
}));

const bootstrap: DrawingBootstrapResponse = {
  drawingId: "drawing-1",
  title: "Sample Drawing",
  version: "1",
  defaultMode: "3d",
  availability: {
    has2d: true,
    has3d: true,
  },
  metadata: {},
};

const knowledgeMock: DrawingKnowledgeMock = {
  attributes: [],
  remarks: "-",
  revisionHistory: [],
  relatedTabs: [],
  changeHistory: [],
  tagAttributeTargets: [],
  tagAttributePolicy: "-",
  tagAttributeReviewRequired: false,
};

describe("Viewer3DPage", () => {
  it("renders section controls after the 3D scene", async () => {
    render(
      <Viewer3DPage
        drawingId="drawing-1"
        bootstrap={bootstrap}
        knowledgeMock={knowledgeMock}
        debugInputsEnabled={false}
        autoOpenDrawingSource={false}
      />,
    );

    const header = screen.getByRole("heading", { name: "sample.step" });
    const toolbarButton = screen.getByLabelText("拡大");
    const scene = await screen.findByTestId("viewer-3d-scene");
    const sectionPosition = screen.getByText(/断面位置:/);

    expect(header.compareDocumentPosition(toolbarButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(toolbarButton.compareDocumentPosition(scene) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(scene.compareDocumentPosition(sectionPosition) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
