import { describe, expect, it } from "vitest";

import { buildDrawingInfoFields, buildDrawingKnowledgeDetail } from "./drawingKnowledge";
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

  it("uses backend knowledge detail for supplement sections", () => {
    const detail = buildDrawingKnowledgeDetail({
      ...bootstrap,
      metadata: {
        ...bootstrap.metadata,
        knowledgeDetail: {
          schemaVersion: "viewer_knowledge_detail.v1",
          attributes: [{ label: "材質", value: "SUS304" }],
          remarks: "図枠から取得",
          revisionHistory: [
            {
              version: "R1",
              updatedAt: "2026-07-16T10:00:00+09:00",
              updatedBy: "ICAD抽出",
              summary: "A 寸法変更",
              status: "印刷枠内 / 信頼度:medium",
            },
          ],
          relatedTabs: [
            {
              id: "drawing",
              label: "図面",
              items: [
                {
                  id: "drawing",
                  title: "図面",
                  subtitle: "既存受け口あり",
                  description: "図面へタグを連携",
                  chips: ["治具"],
                },
              ],
            },
          ],
          changeHistory: [
            {
              version: "2D",
              changedAt: "2026-07-16T10:00:00+09:00",
              changedBy: "ICAD抽出",
              summary: "2D snapshotを更新",
            },
          ],
          tagAttributeTargets: [
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
                  entityHint: "drawing",
                  bindingStatus: "needs_attribute_master_binding",
                },
              ],
              reviewRequired: true,
              notes: ["図面が第一優先"],
            },
          ],
          tagAttributePolicy: "図面管理で確認",
          tagAttributeReviewRequired: true,
        },
      },
    });

    expect(detail.attributes).toEqual([{ label: "材質", value: "SUS304" }]);
    expect(detail.remarks).toBe("図枠から取得");
    expect(detail.tagAttributeReviewRequired).toBe(true);
    expect(detail.tagAttributePolicy).toBe("図面管理で確認");
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
    expect(detail.revisionHistory[0].summary).toBe("A 寸法変更");
    expect(detail.relatedTabs[0].items[0].title).toBe("図面");
    expect(detail.changeHistory[0].summary).toBe("2D snapshotを更新");
  });

  it("keeps local sandbox metadata empty when no bootstrap fields exist", () => {
    const localDetail = buildDrawingKnowledgeDetail({
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
