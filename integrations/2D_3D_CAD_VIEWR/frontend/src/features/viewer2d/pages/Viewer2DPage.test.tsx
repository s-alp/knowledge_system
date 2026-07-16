import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DrawingKnowledgeDetail } from "../../../shared/knowledge/drawingKnowledge";
import type { DrawingBootstrapResponse } from "../../../shared/types/viewer";
import { Viewer2DPage } from "./Viewer2DPage";

let drawingOverviewRenderCount = 0;

vi.mock("../../../shared/api/client", () => ({
  openDrawingViewer2D: vi.fn(),
  openViewer2D: vi.fn(),
  uploadViewer2D: vi.fn(),
}));

vi.mock("../../../shared/components/DrawingOverviewPanel", () => ({
  DrawingOverviewPanel: ({ footerContent }: { footerContent: React.ReactNode }) => {
    drawingOverviewRenderCount += 1;
    return <div data-testid="drawing-overview-panel">{footerContent}</div>;
  },
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
  getViewer2DLoadingMessage: () => null,
}));

vi.mock("../../../shared/knowledge/drawingKnowledge", async () => {
  const actual = await vi.importActual<typeof import("../../../shared/knowledge/drawingKnowledge")>(
    "../../../shared/knowledge/drawingKnowledge",
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

vi.mock("../hooks/useViewer2DDocument", () => ({
  useViewer2DDocument: () => ({
    adapter: null,
    loading: false,
    error: null,
  }),
}));

vi.mock("../components/TwoDViewerCanvas", () => ({
  TwoDViewerCanvas: ({
    viewport,
  }: {
    viewport: {
      scale: number;
    };
  }) => <div data-testid="canvas-scale">{viewport.scale.toFixed(1)}</div>,
}));

const bootstrap: DrawingBootstrapResponse = {
  drawingId: "drawing-1",
  title: "Sample Drawing",
  version: "1",
  defaultMode: "2d",
  availability: {
    has2d: true,
    has3d: true,
  },
  metadata: {},
};

const knowledgeDetail: DrawingKnowledgeDetail = {
  attributes: [],
  remarks: "-",
  revisionHistory: [],
  relatedTabs: [],
  changeHistory: [],
  tagAttributeTargets: [],
  tagAttributePolicy: "-",
  tagAttributeReviewRequired: false,
};

describe("Viewer2DPage", () => {
  beforeEach(() => {
    drawingOverviewRenderCount = 0;
  });

  it("does not rerender the overview panel when preview zoom changes", () => {
    render(
      <Viewer2DPage
        drawingId="drawing-1"
        bootstrap={bootstrap}
        knowledgeDetail={knowledgeDetail}
        debugInputsEnabled={false}
        autoOpenDrawingSource={false}
      />,
    );

    expect(drawingOverviewRenderCount).toBe(1);
    expect(screen.getByTestId("canvas-scale")).toHaveTextContent("1.0");

    fireEvent.click(screen.getByLabelText("拡大"));

    expect(screen.getByTestId("canvas-scale")).toHaveTextContent("1.1");
    expect(drawingOverviewRenderCount).toBe(1);
  });
});
