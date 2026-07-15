import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DrawingOverviewPanel } from "./DrawingOverviewPanel";

describe("DrawingOverviewPanel", () => {
  it("renders header icons as decorative elements", () => {
    const { container } = render(
      <DrawingOverviewPanel
        version="1.2"
        fields={[{ label: "図面番号", value: "DWG-001" }]}
        attributes={[{ label: "材質", value: "SUS304" }]}
        remarks="加工確認"
      />,
    );

    expect(screen.getByRole("heading", { name: "基本情報", level: 2 })).toBeInTheDocument();
    expect(screen.getByText("ver.1.2")).toBeInTheDocument();

    const headerActions = container.querySelector(".knowledge-header-actions");
    expect(headerActions).not.toBeNull();
    expect(headerActions).toHaveAttribute("aria-hidden", "true");
    expect(headerActions?.querySelectorAll("svg")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "編集" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "削除" })).not.toBeInTheDocument();
  });

  it("omits version text when version is not provided", () => {
    const { container } = render(
      <DrawingOverviewPanel
        fields={[{ label: "図面番号", value: "DWG-002" }]}
        attributes={[]}
        remarks="-"
      />,
    );

    expect(within(container).queryByText(/^ver\./)).not.toBeInTheDocument();
  });
});
