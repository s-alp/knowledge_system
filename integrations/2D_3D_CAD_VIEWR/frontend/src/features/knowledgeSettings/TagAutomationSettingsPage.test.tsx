import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getTagAutomationSettings,
  type TagAutomationSettingsResponse,
} from "../../shared/api/client";
import { TagAutomationSettingsPage } from "./TagAutomationSettingsPage";


vi.mock("../../shared/api/client", () => ({
  getTagAutomationSettings: vi.fn(),
}));

const settings: TagAutomationSettingsResponse = {
  title: "タグ・属性自動取得設定",
  summary: "抽出と採用判断に使用する現在の設定です。",
  runtimeRows: [
    { label: "AI APIキー", value: "設定済み" },
    { label: "温度", value: "0.1" },
  ],
  operationRows: [
    {
      area: "図面管理",
      screen: "ICAD抽出レビュー",
      role: "抽出開始・再抽出・候補確認",
      writePolicy: "ローカルDBのみ",
    },
  ],
  targetRows: [
    {
      target: "部品",
      displayPage: "部品詳細",
      storedAs: "確定属性・タグ",
      reviewRoute: "ICAD抽出レビュー",
    },
  ],
  ruleRows: [
    { label: "生成AIの利用", value: "決定論的抽出で不足するときだけ利用" },
  ],
};


describe("TagAutomationSettingsPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows the runtime settings returned by the backend without exposing a secret", async () => {
    vi.mocked(getTagAutomationSettings).mockResolvedValue(settings);

    render(<TagAutomationSettingsPage />);

    expect(await screen.findByText("タグ・属性自動取得設定")).toBeInTheDocument();
    expect(screen.getByText("設定済み")).toBeInTheDocument();
    expect(screen.getByText("0.1")).toBeInTheDocument();
    expect(screen.getByText("ローカルDBのみ")).toBeInTheDocument();
    expect(screen.queryByText(/AIza/i)).not.toBeInTheDocument();
  });
});
