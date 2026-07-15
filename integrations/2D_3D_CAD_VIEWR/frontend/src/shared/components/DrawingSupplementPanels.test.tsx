import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DrawingSupplementPanels } from "./DrawingSupplementPanels";
import type { DrawingKnowledgeMock } from "../mock/drawingKnowledge";

const detail: DrawingKnowledgeMock = {
  attributes: [],
  remarks: "-",
  revisionHistory: [],
  relatedTabs: [{ id: "project", label: "プロジェクト", items: [] }],
  changeHistory: [],
  tagAttributePolicy: "2D/3Dビューワー内の補助パネル表示用",
  tagAttributeReviewRequired: true,
  tagAttributeTargets: [
    {
      targetKey: "drawing",
      label: "図面",
      tagApiStatus: "candidate_existing",
      writePolicy: "preview_only_no_production_write",
      reviewRequired: true,
      tags: ["材質:SUS304", "装置:供給台"],
      attributes: [
        {
          name: "材質",
          value: "SUS304",
          sourcePath: "canonicalAttributes.material_keywords",
          entityHint: "-",
          bindingStatus: "needs_attribute_master_binding",
        },
      ],
      notes: [],
    },
  ],
};

describe("DrawingSupplementPanels", () => {
  it("renders viewer tag and attribute targets from bootstrap metadata", () => {
    render(<DrawingSupplementPanels detail={detail} />);

    const panel = screen.getByRole("heading", { name: "タグ・属性候補" }).closest("section");
    expect(panel).not.toBeNull();
    expect(within(panel as HTMLElement).getByText("レビュー要")).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText("図面")).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText("candidate_existing")).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText("材質:SUS304")).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText("装置:供給台")).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText("材質")).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText("SUS304")).toBeInTheDocument();
  });
});
