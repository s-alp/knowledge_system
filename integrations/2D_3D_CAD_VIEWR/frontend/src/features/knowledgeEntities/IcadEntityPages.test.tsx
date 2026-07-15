import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getKnowledgeEntities,
  getKnowledgeEntity,
  type KnowledgeEntityCatalogResponse,
  type KnowledgeEntityRecord,
} from "../../shared/api/client";
import { IcadEntityDetailPage, IcadEntityListPage } from "./IcadEntityPages";


vi.mock("../../shared/api/client", () => ({
  getKnowledgeEntities: vi.fn(),
  getKnowledgeEntity: vi.fn(),
}));

const partRecord: KnowledgeEntityRecord = {
  entityId: "11111111-1111-4111-8111-111111111111",
  targetKey: "part",
  entityKind: "part",
  classificationEvidence: "sxnet_node_fields",
  classificationConfidence: "high",
  name: "BRACKET-A",
  partNumber: "CAA5012-02434006P1R1",
  comment: "供給台ブラケット",
  treePath: ["MACHINE", "FEEDER", "BRACKET-A"],
  depth: 2,
  parentEntityId: "22222222-2222-4222-8222-222222222222",
  childEntityIds: [],
  childAssemblyCount: 0,
  childPartCount: 0,
  descendantPartCount: 0,
  drawingId: "33333333-3333-4333-8333-333333333333",
  drawingFilename: "CAA5012-02434006P1R1.icd",
  sourcePath: "J:\\ライズ\\CAA5012-02434006P1R1.icd",
  attributes: [
    {
      key: "materials",
      label: "材質",
      value: "SS400",
      source: "3d_part_material",
      confidence: "high",
      evidence: "snapshotsByMode.3d.rawExtract.parts[2].materials",
    },
  ],
  tags: [
    {
      value: "材質:SS400",
      source: "3d_part_material",
      confidence: "high",
      evidence: "snapshotsByMode.3d.rawExtract.parts[2].materials",
    },
  ],
  conflicts: [],
  reviewStatus: "confirmed",
  reviewRequired: false,
  evidence: [],
  history: [],
  updatedAt: "2026-07-15T12:00:00+09:00",
  relatedEntities: [
    {
      relationship: "parent",
      entityId: "22222222-2222-4222-8222-222222222222",
      targetKey: "product",
      entityKind: "subassembly",
      name: "FEEDER",
      partNumber: null,
    },
  ],
  relatedDrawing: {
    drawingId: "33333333-3333-4333-8333-333333333333",
    filename: "CAA5012-02434006P1R1.icd",
  },
};

const catalog: KnowledgeEntityCatalogResponse = {
  schemaVersion: "icad_knowledge_entities.v1",
  definitions: {
    product: "ICAD 3D構成で子ノードを持つアセンブリ／サブアセンブリ",
    part: "ICAD 3D構成で子ノードを持たない末端パーツ",
  },
  targetKey: "part",
  count: 1,
  totalCount: 1,
  returnedCount: 1,
  offset: 0,
  limit: 50,
  items: [partRecord],
  skippedDrawings: [],
};


describe("ICAD knowledge entity pages", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows every leaf part returned by the ICAD entity API", async () => {
    vi.mocked(getKnowledgeEntities).mockResolvedValue(catalog);
    const onOpenDetail = vi.fn();

    render(<IcadEntityListPage targetKey="part" onOpenDetail={onOpenDetail} />);

    expect(await screen.findByText("CAA5012-02434006P1R1")).toBeInTheDocument();
    expect(screen.getByText("BRACKET-A")).toBeInTheDocument();
    expect(screen.getByText("SS400")).toBeInTheDocument();
    fireEvent.click(screen.getByText("BRACKET-A"));
    expect(onOpenDetail).toHaveBeenCalledWith(partRecord.entityId, partRecord.drawingId);
  });

  it("shows node-specific attributes, tags, evidence confidence, and relationships", async () => {
    vi.mocked(getKnowledgeEntity).mockResolvedValue(partRecord);
    const onNavigate = vi.fn();

    render(<IcadEntityDetailPage entityId={partRecord.entityId} drawingId={partRecord.drawingId} onNavigate={onNavigate} />);

    expect(await screen.findByText("材質:SS400")).toBeInTheDocument();
    expect(screen.getByText("高")).toBeInTheDocument();
    expect(screen.getByText("3D材質")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "親製品・装置・ユニット" })).toBeInTheDocument();
    fireEvent.click(screen.getByText("FEEDER"));
    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith(
        "product",
        "22222222-2222-4222-8222-222222222222",
        partRecord.drawingId,
      );
    });
  });
});
