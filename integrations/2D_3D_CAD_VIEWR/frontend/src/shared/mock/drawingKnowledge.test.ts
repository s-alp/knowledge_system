import { describe, expect, it } from "vitest";

import { buildDrawingInfoFields, buildDrawingKnowledgeMock } from "./drawingKnowledge";
import type { DrawingBootstrapResponse } from "../types/viewer";

const bootstrap: DrawingBootstrapResponse = {
  drawingId: "35463219-5fe5-49a0-ae7f-ed25c5661be9",
  title: "工程図",
  version: "2",
  defaultMode: "2d",
  availability: {
    has2d: true,
    has3d: false,
  },
  metadata: {
    drawingNumber: "PART-001",
    drawingName: "工程図",
    drawingType: "部品図",
    paperSize: "A3",
    status: "レビュー中",
    owner: "創屋 太郎",
    designPurpose: "加工確認",
    tags: ["治具"],
    tagAttributes: {
      schemaVersion: "viewer_tag_attributes.v1",
      displayPolicy: "本番登録は行わない",
      reviewRequired: true,
      targets: [
        {
          targetKey: "drawing",
          label: "図面",
          tagApiStatus: "candidate_existing",
          writePolicy: "preview_only_no_production_write",
          tags: ["治具", "材質:SUS304"],
          attributes: [
            {
              name: "材質",
              value: "SUS304",
              sourcePath: "canonicalAttributes.material_keywords",
              bindingStatus: "needs_attribute_master_binding",
            },
          ],
          reviewRequired: true,
          notes: ["図面が第一優先"],
        },
      ],
    },
  },
};

describe("drawingKnowledge", () => {
  it("maps bootstrap metadata into display fields", () => {
    expect(buildDrawingInfoFields(bootstrap)).toEqual([
      { label: "図面番号", value: "PART-001" },
      { label: "図面名", value: "工程図" },
      { label: "図面タイプ", value: "部品図" },
      { label: "用紙サイズ", value: "A3" },
      { label: "ステータス", value: "レビュー中" },
      { label: "所有者", value: "創屋 太郎" },
      { label: "設計意図・目的", value: "加工確認" },
      { label: "タグ", value: "治具" },
    ]);
  });

  it("builds deterministic mock detail sections", () => {
    const detail = buildDrawingKnowledgeMock(bootstrap);

    expect(detail.attributes).toHaveLength(2);
    expect(detail.remarks).toBe("加工確認");
    expect(detail.tagAttributeReviewRequired).toBe(true);
    expect(detail.tagAttributePolicy).toBe("本番登録は行わない");
    expect(detail.tagAttributeTargets[0]).toMatchObject({
      targetKey: "drawing",
      label: "図面",
      tags: ["治具", "材質:SUS304"],
    });
    expect(detail.tagAttributeTargets[0].attributes[0]).toMatchObject({
      name: "材質",
      value: "SUS304",
      bindingStatus: "needs_attribute_master_binding",
    });
    expect(detail.revisionHistory[0]).toMatchObject({
      version: "ver.2",
      updatedBy: "創屋 太郎",
    });
    expect(detail.relatedTabs.map((tab) => tab.label)).toEqual(["プロジェクト", "製品", "部品", "会話ログ"]);
    expect(detail.changeHistory).toHaveLength(3);
  });

  it("keeps local sandbox metadata empty when no bootstrap fields exist", () => {
    const localDetail = buildDrawingKnowledgeMock({
      ...bootstrap,
      title: "",
      version: null,
      metadata: {},
    });

    expect(localDetail.attributes).toEqual([]);
    expect(localDetail.remarks).toBe("-");
    expect(localDetail.revisionHistory).toEqual([]);
    expect(localDetail.relatedTabs.every((tab) => tab.items.length === 0)).toBe(true);
    expect(localDetail.changeHistory).toEqual([]);
    expect(localDetail.tagAttributeTargets).toEqual([]);
  });
});
