import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  applyDrawingMetadataOverrides,
  getDrawingOptions,
  getKnowledgeEntities,
  getKnowledgeEntity,
  type KnowledgeEntityCatalogResponse,
  type KnowledgeEntityRecord,
} from "../../shared/api/client";
import { IcadEntityDetailPage, IcadEntityListPage } from "./IcadEntityPages";


vi.mock("../../shared/api/client", () => ({
  applyDrawingMetadataOverrides: vi.fn(),
  getDrawingOptions: vi.fn(),
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
      reason: "材質として3D部品材質情報から抽出でき、部品検索に使えるため採用しています。",
    },
  ],
  tags: [
    {
      value: "材質:SS400",
      source: "3d_part_material",
      confidence: "high",
      evidence: "snapshotsByMode.3d.rawExtract.parts[2].materials",
      reason: "正式材質として分類でき、加工・調達検索に使えるため採用しています。",
    },
  ],
  businessFields: {
    name: "BRACKET-A",
    partNumber: "CAA5012-02434006P1R1",
    category: "ブラケット",
    entityKind: "part",
    phase: "",
    status: "完了",
    owner: "設計担当者",
    supplier: "",
    unitPrice: "",
    unit: "個",
    remarks: "供給台ブラケット",
  },
  businessFieldSources: {
    name: { source: "icad_extraction", evidence: "topPart" },
  },
  conflicts: [],
  diagnosticConflicts: [],
  reconciledAttributes: [
    {
      attribute: "material_keywords",
      value2d: ["SS400"],
      value3d: ["SS400"],
      chosenValue: ["SS400"],
      chosenMode: "merged",
      status: "merged",
      reason: "2Dと3Dの配列値を重複排除して統合しました。",
    },
    {
      attribute: "mass_value",
      value2d: null,
      value3d: 12.3456,
      chosenValue: 12.3456,
      chosenMode: "3d",
      status: "only_3d",
      reason: "3D抽出にのみ値があるため採用しました。",
    },
  ],
  reviewStatus: "confirmed",
  reviewRequired: false,
  extractionReview: {
    status: "confirmed",
    required: false,
    label: "確認済み",
    description: "ICAD自動抽出結果の確認状態です。",
  },
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
  relatedDrawings: [
    {
      drawingId: "33333333-3333-4333-8333-333333333333",
      filename: "CAA5012-02434006P1R1.icd",
      sourcePath: "J:\\ライズ\\CAA5012-02434006P1R1.icd",
      relationship: "source",
    },
  ],
  provenance: [
    {
      kind: "attribute",
      name: "材質",
      key: "materials",
      label: "材質",
      value: "SS400",
      source: "3d_part_material",
      confidence: "high",
      evidence: "rawExtract.parts[2].materials",
      reason: "材質として3D部品材質情報から抽出でき、部品検索に使えるため採用しています。",
    },
  ],
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

  it("shows Souya-style business fields, tags, provenance, and relationships", async () => {
    vi.mocked(getKnowledgeEntity).mockResolvedValue(partRecord);
    vi.mocked(getDrawingOptions).mockResolvedValue({ items: [], totalCount: 0 });
    vi.mocked(applyDrawingMetadataOverrides).mockResolvedValue({
      drawingId: partRecord.drawingId,
      extractionMode: "3d",
      manualOverrides: {},
      canonicalAttributes: {},
      derivedTags: [],
    });
    const onNavigate = vi.fn();

    render(<IcadEntityDetailPage entityId={partRecord.entityId} drawingId={partRecord.drawingId} onNavigate={onNavigate} />);

    expect(await screen.findByText("材質:SS400")).toBeInTheDocument();
    expect(screen.getByText("2D/3D照合")).toBeInTheDocument();
    expect(screen.getByText("material_keywords")).toBeInTheDocument();
    expect(screen.getByText("統合")).toBeInTheDocument();
    expect(screen.getByText("3D抽出にのみ値があるため採用しました。")).toBeInTheDocument();
    expect(screen.getAllByText("完了").length).toBeGreaterThan(0);
    expect(screen.getByRole("tab", { name: "製品・装置・ユニット" })).toBeInTheDocument();
    fireEvent.click(screen.getByText("FEEDER"));
    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith(
        "product",
        "22222222-2222-4222-8222-222222222222",
        partRecord.drawingId,
      );
    });
    fireEvent.click(screen.getByRole("button", { name: "取得根拠を見る" }));
    expect(screen.getByRole("dialog", { name: "取得元・採用根拠" })).toBeInTheDocument();
    expect(screen.getByText("3D材質API")).toBeInTheDocument();
    expect(screen.getByText("信頼度")).toBeInTheDocument();
    expect(screen.getByText("採用理由")).toBeInTheDocument();
    expect(screen.getByText("材質として3D部品材質情報から抽出でき、部品検索に使えるため採用しています。")).toBeInTheDocument();
    expect(screen.getByText("ICAD抽出根拠")).toBeInTheDocument();
    expect(screen.queryByText(/抽出結果:/)).not.toBeInTheDocument();
  });
});
