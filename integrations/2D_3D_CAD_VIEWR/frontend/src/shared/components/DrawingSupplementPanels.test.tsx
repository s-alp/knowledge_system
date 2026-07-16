import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DrawingSupplementPanels } from "./DrawingSupplementPanels";
import type { DrawingKnowledgeDetail } from "../knowledge/drawingKnowledge";

const detail: DrawingKnowledgeDetail = {
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
        {
          name: "パーツ付加情報トークン",
          value: "User_type,User_syori1,User_syori2,User_netu,User_hrc,User_maker,User_bikou,User_souchi,User_unit,User_kenzu,User_sekkei,User_seizu,User_SNO,User_Partsname,User_Material,User_Surfacefinishing",
          sourcePath: "canonicalAttributes.part_ex_info_tokens",
          entityHint: "-",
          bindingStatus: "needs_part_record_and_attribute_master_binding",
        },
        {
          name: "属性2",
          value: "value2",
          sourcePath: "canonicalAttributes.extra2",
          entityHint: "-",
          bindingStatus: "needs_attribute_master_binding",
        },
        {
          name: "属性3",
          value: "value3",
          sourcePath: "canonicalAttributes.extra3",
          entityHint: "-",
          bindingStatus: "needs_attribute_master_binding",
        },
        {
          name: "属性4",
          value: "value4",
          sourcePath: "canonicalAttributes.extra4",
          entityHint: "-",
          bindingStatus: "needs_attribute_master_binding",
        },
        {
          name: "属性5",
          value: "value5",
          sourcePath: "canonicalAttributes.extra5",
          entityHint: "-",
          bindingStatus: "needs_attribute_master_binding",
        },
        {
          name: "属性6",
          value: "value6",
          sourcePath: "canonicalAttributes.extra6",
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
    expect(within(panel as HTMLElement).getByText("パーツ付加情報トークン")).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText(/User_Surfacefinishing/)).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText("1 属性")).toBeInTheDocument();
  });
});
