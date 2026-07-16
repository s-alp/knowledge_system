import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import {
  getDrawingMetadataHandoffSummary,
  getDrawingMetadataRegistrations,
  getTagAutomationSettings,
  type HandoffSummaryResponse,
  type TagAutomationSettingsResponse,
} from "../../shared/api/client";
import { TagAutomationSettingsPage } from "./TagAutomationSettingsPage";

vi.mock("../../shared/api/client", () => ({
  getDrawingMetadataHandoffSummary: vi.fn(),
  getDrawingMetadataRegistrations: vi.fn(),
  getTagAutomationSettings: vi.fn(),
}));

const settings: TagAutomationSettingsResponse = {
  title: "タグ・属性自動取得設定",
  summary: "ICAD抽出結果からタグ・属性候補を作ります。",
  managementLinks: [
    {
      key: "icad-extraction-management",
      label: "ICAD抽出管理",
      description: "登録済みICDと抽出状態を確認します。",
      action: "open_icad_extraction_review",
    },
    {
      key: "integration-data-review",
      label: "API仕様・連携仕様",
      description: "API仕様と連携仕様で確認します。",
      action: "show_handoff_note",
    },
  ],
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

const handoffSummary: HandoffSummaryResponse = {
  workerStatus: {
    schemaVersion: "drawing_metadata_worker_heartbeat.v1",
    status: "running",
    label: "稼働中",
    message: "抽出workerは起動済みで、次のジョブを待機しています。",
    workerName: "codex-local-worker",
    mode: "all",
    state: "idle",
    jobId: "",
    updatedAt: "2026-07-16T00:00:00Z",
    ageSeconds: 2,
    staleAfterSeconds: 30,
  },
  jobStatusCounts: {
    queued: 1,
    processing: 0,
    succeeded: 10,
    failed: 1,
  },
  recentFailedJobs: [
    {
      jobId: "job-failed-1",
      drawingId: "drawing-1",
      filename: "sample.icd",
      extractionMode: "3d",
      status: "failed",
      workerName: "codex-local-worker",
      errorMessage: "sxnet.SxException: 指定したファイルは図面ファイルではありません。",
      reextractCondition: "ICAD/SXNETが図面ファイルとして開けていません。ファイル種別、パス、アクセス権、ICAD対応版を確認して再抽出します。",
      updatedAt: "2026-07-16T00:00:00Z",
    },
  ],
  scope: {
    mode: "manifest",
    manifestPath: "C:\\manifest\\shared.json",
    manifestSourceCount: 39,
    totalRegistrationCount: 68,
    scopedRegistrationCount: 39,
    excludedRegistrationCount: 29,
  },
  apiRows: [
    {
      area: "システム設定",
      method: "GET",
      path: "/api/v1/drawing-metadata/handoff-summary",
      purpose: "抽出管理、API仕様、対象別payload集計をシステム設定内に表示する。",
    },
    {
      area: "ICAD抽出登録",
      method: "GET",
      path: "/api/v1/drawing-metadata/registrations",
      purpose: "登録済みICD単位の抽出状態を確認する。",
    },
  ],
  summaryCards: [
    { label: "登録図面", value: 39 },
    { label: "2D/3D両snapshotあり", value: 39 },
  ],
  targetTotals: [
    { targetKey: "drawing", targetLabel: "図面", drawingCount: 39, attributeCount: 200, tagCount: 120 },
  ],
  rows: [
    {
      drawingId: "drawing-1",
      filename: "sample.icd",
      sourcePath: "J:\\SAMPLE\\sample.icd",
      has2d: true,
      has3d: true,
      has2dLabel: "あり",
      has3dLabel: "あり",
      snapshotStateLabel: "2D/3D抽出済み",
      defaultMode: "2d",
      canonicalAttributeCount: 10,
      tagCount: 3,
      reviewConflictCount: 0,
      diagnosticConflictCount: 1,
      payloadTargets: [],
      detailUrl: "/internal/drawing-metadata/drawing-1/",
      tagReviewUrl: "/internal/drawing-metadata/drawing-1/tags/",
      bootstrapApiUrl: "/api/v1/drawings/drawing-1/bootstrap",
      ragPayloadApiUrl: "/api/v1/drawing-metadata/registrations/drawing-1/rag-payload",
    },
  ],
};

describe("TagAutomationSettingsPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows extraction management and handoff data inside system settings", async () => {
    vi.mocked(getTagAutomationSettings).mockResolvedValue(settings);
    vi.mocked(getDrawingMetadataRegistrations).mockResolvedValue([
      {
        drawingId: "drawing-1",
        hostDrawingId: "",
        filename: "sample.icd",
        sourcePath: "J:\\SAMPLE\\sample.icd",
        sourceFormat: "icad",
        snapshotModes: ["2d", "3d"],
        latestJobStatusByMode: { "2d": "succeeded", "3d": "queued" },
        latestJobIdByMode: { "2d": "job-2d", "3d": "job-3d" },
        latestJobErrorByMode: { "2d": "", "3d": "sxnet.SxException: 指定したファイルは図面ファイルではありません。" },
        latestJobUpdatedAtByMode: { "2d": "2026-07-16T00:00:00Z", "3d": "2026-07-16T00:00:00Z" },
        createdAt: "2026-07-16T00:00:00Z",
        updatedAt: "2026-07-16T00:00:00Z",
      },
    ]);
    vi.mocked(getDrawingMetadataHandoffSummary).mockResolvedValue(handoffSummary);

    render(<TagAutomationSettingsPage />);

    expect(await screen.findByText("タグ・属性自動取得設定")).toBeInTheDocument();
    expect(getDrawingMetadataRegistrations).not.toHaveBeenCalled();
    expect(getDrawingMetadataHandoffSummary).not.toHaveBeenCalled();
    expect(screen.getByText("設定済み")).toBeInTheDocument();
    expect(screen.getByText("0.1")).toBeInTheDocument();
    expect(screen.getByText("ローカルDBのみ")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /ICAD抽出管理/ }));
    expect(screen.getByRole("heading", { name: "ICAD抽出管理" })).toBeInTheDocument();
    expect(getDrawingMetadataRegistrations).toHaveBeenCalledWith({ includeAll: true });
    expect((await screen.findAllByText("sample.icd")).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("2D / 3D")).toBeInTheDocument();
    expect(screen.getByText("待機中")).toBeInTheDocument();
    expect(screen.getByText("稼働中")).toBeInTheDocument();
    expect(screen.getByText("heartbeat更新")).toBeInTheDocument();
    expect(screen.getByText("heartbeat経過")).toBeInTheDocument();
    expect(screen.getAllByText("codex-local-worker").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("1 / 0 / 10 / 1")).toBeInTheDocument();
    expect(screen.getByText("最終ジョブ更新")).toBeInTheDocument();
    expect(screen.getByText("失敗日時")).toBeInTheDocument();
    expect(screen.getByText(/図面ファイルとして開けていません/)).toBeInTheDocument();
    expect(screen.getByText("対象範囲: 固定manifest 39件 / 全登録 68件")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /API仕様・連携仕様/ }));
    expect(screen.getByRole("heading", { name: "API仕様・連携仕様" })).toBeInTheDocument();
    expect(screen.getByText("登録図面")).toBeInTheDocument();
    expect(screen.getByText("集計対象外")).toBeInTheDocument();
    expect(screen.getByText("C:\\manifest\\shared.json")).toBeInTheDocument();
    expect(screen.getByText("/api/v1/drawing-metadata/handoff-summary")).toBeInTheDocument();
    expect(screen.getByText("抽出管理、API仕様、対象別payload集計をシステム設定内に表示する。")).toBeInTheDocument();
    expect(screen.getByText("/api/v1/drawings/drawing-1/bootstrap")).toBeInTheDocument();
    expect(screen.queryByText(/通常画面へ出さず/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /ICAD抽出管理/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/AIza/i)).not.toBeInTheDocument();
  });
});
