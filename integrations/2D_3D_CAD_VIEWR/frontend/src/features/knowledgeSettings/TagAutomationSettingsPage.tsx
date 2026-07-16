import { useEffect, useState } from "react";
import { IconChevronRight, IconDatabase, IconTransfer } from "@tabler/icons-react";

import {
  getDrawingMetadataHandoffSummary,
  getDrawingMetadataRegistrations,
  getTagAutomationSettings,
  type DrawingMetadataRegistrationListItem,
  type HandoffSummaryResponse,
  type TagAutomationSettingsResponse,
} from "../../shared/api/client";

type SettingsPanelKey = "overview" | "icad-extraction" | "handoff";

let cachedSettingsPayload: TagAutomationSettingsResponse | null = null;
let cachedRegistrations: DrawingMetadataRegistrationListItem[] | null = null;
let cachedHandoffSummary: HandoffSummaryResponse | null = null;

function formatSnapshotModes(item: DrawingMetadataRegistrationListItem) {
  if (!item.snapshotModes.length) {
    return "未抽出";
  }
  return item.snapshotModes.map((mode) => mode.toUpperCase()).join(" / ");
}

function formatJobStatus(status: string | null | undefined) {
  if (!status) {
    return "-";
  }
  return {
    queued: "待機中",
    processing: "抽出中",
    succeeded: "完了",
    failed: "失敗",
  }[status] ?? status;
}

function panelForAction(action: string): SettingsPanelKey {
  if (action === "open_icad_extraction_review") {
    return "icad-extraction";
  }
  if (action === "show_handoff_note") {
    return "handoff";
  }
  return "overview";
}

function scopeLabel(summary: HandoffSummaryResponse | null) {
  const scope = summary?.scope;
  if (!scope) {
    return "対象範囲: 全登録";
  }
  if (scope.mode === "manifest") {
    return `対象範囲: 固定manifest ${scope.scopedRegistrationCount}件 / 全登録 ${scope.totalRegistrationCount}件`;
  }
  if (scope.mode === "all_manifest_missing") {
    return `対象範囲: 全登録（manifest未検出: ${scope.manifestPath}）`;
  }
  return `対象範囲: 全登録 ${scope.totalRegistrationCount}件`;
}

export function TagAutomationSettingsPage() {
  const [settingsPayload, setSettingsPayload] = useState<TagAutomationSettingsResponse | null>(() => cachedSettingsPayload);
  const [registrations, setRegistrations] = useState<DrawingMetadataRegistrationListItem[]>(() => cachedRegistrations ?? []);
  const [handoffSummary, setHandoffSummary] = useState<HandoffSummaryResponse | null>(() => cachedHandoffSummary);
  const [activePanel, setActivePanel] = useState<SettingsPanelKey>("overview");
  const [panelLoading, setPanelLoading] = useState(false);
  const [loadedPanels, setLoadedPanels] = useState<Partial<Record<SettingsPanelKey, boolean>>>(() => ({
    "icad-extraction": Boolean(cachedRegistrations && cachedHandoffSummary),
    handoff: Boolean(cachedHandoffSummary),
  }));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cachedSettingsPayload) {
      return;
    }
    let active = true;
    getTagAutomationSettings()
      .then((settings) => {
        cachedSettingsPayload = settings;
        if (active) {
          setSettingsPayload(settings);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "タグ自動取得設定を取得できませんでした。");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (activePanel === "overview" || loadedPanels[activePanel]) {
      return;
    }

    let active = true;
    setPanelLoading(true);
    setError(null);
    const request =
      activePanel === "icad-extraction"
        ? Promise.all([
            cachedRegistrations ? Promise.resolve(cachedRegistrations) : getDrawingMetadataRegistrations(),
            cachedHandoffSummary ? Promise.resolve(cachedHandoffSummary) : getDrawingMetadataHandoffSummary(),
          ])
            .then(([registrationItems, summary]) => {
              cachedRegistrations = registrationItems;
              cachedHandoffSummary = summary;
              setRegistrations(registrationItems);
              setHandoffSummary(summary);
            })
        : (cachedHandoffSummary ? Promise.resolve(cachedHandoffSummary) : getDrawingMetadataHandoffSummary()).then((summary) => {
            cachedHandoffSummary = summary;
            setHandoffSummary(summary);
          });

    request
      .then(() => {
        if (active) {
          setLoadedPanels((current) => ({
            ...current,
            [activePanel]: true,
            handoff: activePanel === "icad-extraction" || activePanel === "handoff" ? true : current.handoff,
          }));
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "管理情報を取得できませんでした。");
        }
      })
      .finally(() => {
        if (active) {
          setPanelLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [activePanel, loadedPanels]);

  if (error) {
    return <section className="production-section workspace-message error-panel">{error}</section>;
  }
  if (!settingsPayload) {
    return <section className="production-section workspace-message">設定を読み込んでいます。</section>;
  }

  return (
    <section className="knowledge-production-page entity-page">
      <section className="production-section">
        <h2>ICADタグ・属性管理</h2>
        <p className="production-section-note">抽出運用と創屋連携データの確認は、システム設定から行います。</p>
        <div className="production-section-divider" />
        <div className="settings-management-list">
          {settingsPayload.managementLinks.map((link) => {
            const LinkIcon = link.key === "integration-data-review" ? IconTransfer : IconDatabase;
            const nextPanel = panelForAction(link.action);
            return (
              <button
                key={link.key}
                className={activePanel === nextPanel ? "settings-management-link active" : "settings-management-link"}
                type="button"
                onClick={() => setActivePanel(nextPanel)}
              >
                <span className="settings-management-icon" aria-hidden="true">
                  <LinkIcon size={21} stroke={1.8} />
                </span>
                <span className="settings-management-copy">
                  <strong>{link.label}</strong>
                  <span>{link.description}</span>
                </span>
                <IconChevronRight className="settings-management-chevron" size={20} aria-hidden="true" />
              </button>
            );
          })}
        </div>
      </section>

      {activePanel === "icad-extraction" ? (
        <section className="production-section">
          <div className="production-section-header">
            <div>
              <h2>ICAD抽出管理</h2>
              <p className="production-section-note">
                登録済みICD単位で、2D/3D snapshot、最新ジョブ状態、保存先を確認します。
              </p>
              <p className="production-section-note">{scopeLabel(handoffSummary)}</p>
            </div>
          </div>
          <div className="production-section-divider" />
          {panelLoading ? <p className="production-section-note">抽出管理情報を読み込んでいます。</p> : null}
          {handoffSummary ? (
            <div className="production-detail-grid">
              {handoffSummary.summaryCards.map((card) => (
                <div key={card.label} className="production-detail-field">
                  <span>{card.label}</span>
                  <p>{card.value}</p>
                </div>
              ))}
            </div>
          ) : null}
          <div className="production-table-shell">
            <table className="production-table">
              <thead>
                <tr>
                  <th>ICADファイル</th>
                  <th>snapshot</th>
                  <th>2Dジョブ</th>
                  <th>3Dジョブ</th>
                  <th>保存先</th>
                </tr>
              </thead>
              <tbody>
                {panelLoading && !registrations.length ? (
                  <tr>
                    <td colSpan={5}>抽出管理情報を読み込んでいます。</td>
                  </tr>
                ) : registrations.length ? registrations.map((item) => (
                  <tr key={item.drawingId}>
                    <th>{item.filename}</th>
                    <td>{formatSnapshotModes(item)}</td>
                    <td>{formatJobStatus(item.latestJobStatusByMode["2d"])}</td>
                    <td>{formatJobStatus(item.latestJobStatusByMode["3d"])}</td>
                    <td>{item.sourcePath}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5}>登録済みICADはありません。</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {activePanel === "handoff" ? (
        <section className="production-section">
          <div className="production-section-header">
            <div>
              <h2>API仕様・引継ぎ資料</h2>
              <p className="production-section-note">
                創屋へ渡す読み取りAPI、viewer/RAG連携、対象別payload候補の集計です。
              </p>
              <p className="production-section-note">{scopeLabel(handoffSummary)}</p>
            </div>
          </div>
          <div className="production-section-divider" />
          {panelLoading ? <p className="production-section-note">API仕様・引継ぎ情報を読み込んでいます。</p> : null}
          {handoffSummary?.scope ? (
            <div className="production-detail-grid">
              <div className="production-detail-field">
                <span>manifest対象</span>
                <p>{handoffSummary.scope.scopedRegistrationCount}</p>
              </div>
              <div className="production-detail-field">
                <span>全登録</span>
                <p>{handoffSummary.scope.totalRegistrationCount}</p>
              </div>
              <div className="production-detail-field">
                <span>集計対象外</span>
                <p>{handoffSummary.scope.excludedRegistrationCount}</p>
              </div>
              <div className="production-detail-field">
                <span>manifest</span>
                <p>{handoffSummary.scope.manifestPath || "-"}</p>
              </div>
            </div>
          ) : null}
          <div className="production-detail-grid">
            {handoffSummary?.summaryCards.map((card) => (
              <div key={card.label} className="production-detail-field">
                <span>{card.label}</span>
                <p>{card.value}</p>
              </div>
            ))}
          </div>
          <div className="production-table-shell">
            <table className="production-table">
              <thead>
                <tr>
                  <th>領域</th>
                  <th>method</th>
                  <th>API</th>
                  <th>用途</th>
                </tr>
              </thead>
              <tbody>
                {handoffSummary?.apiRows.map((row) => (
                  <tr key={`${row.method}-${row.path}`}>
                    <th>{row.area}</th>
                    <td>{row.method}</td>
                    <td>{row.path}</td>
                    <td>{row.purpose}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="production-table-shell">
            <table className="production-table">
              <thead>
                <tr>
                  <th>対象</th>
                  <th>図面数</th>
                  <th>属性候補</th>
                  <th>タグ候補</th>
                </tr>
              </thead>
              <tbody>
                {handoffSummary?.targetTotals.map((target) => (
                  <tr key={target.targetKey}>
                    <th>{target.targetLabel}</th>
                    <td>{target.drawingCount}</td>
                    <td>{target.attributeCount}</td>
                    <td>{target.tagCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="production-table-shell">
            <table className="production-table">
              <thead>
                <tr>
                  <th>ICADファイル</th>
                  <th>抽出状態</th>
                  <th>属性/タグ</th>
                  <th>API</th>
                </tr>
              </thead>
              <tbody>
                {handoffSummary?.rows.slice(0, 50).map((row) => (
                  <tr key={row.drawingId}>
                    <th>{row.filename}</th>
                    <td>{row.snapshotStateLabel}</td>
                    <td>{row.canonicalAttributeCount} / {row.tagCount}</td>
                    <td>
                      <div>{row.bootstrapApiUrl}</div>
                      <div>{row.ragPayloadApiUrl}</div>
                    </td>
                  </tr>
                )) ?? (
                  <tr>
                    <td colSpan={4}>API仕様・引継ぎ情報を読み込んでいます。</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="production-section production-basic-section">
        <div className="production-section-header">
          <div>
            <h2>{settingsPayload.title}</h2>
            <p className="production-section-note">{settingsPayload.summary}</p>
          </div>
        </div>
        <div className="production-section-divider" />
        <div className="production-detail-grid">
          {settingsPayload.runtimeRows.map((row) => (
            <div key={row.label} className="production-detail-field">
              <span>{row.label}</span>
              <p>{row.value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="production-section">
        <h2>管理項目</h2>
        <div className="production-section-divider" />
        <div className="production-table-shell">
          <table className="production-table">
            <thead>
              <tr>
                <th>領域</th>
                <th>画面</th>
                <th>役割</th>
                <th>書き込み方針</th>
              </tr>
            </thead>
            <tbody>
              {settingsPayload.operationRows.map((row) => (
                <tr key={row.area}>
                  <th>{row.area}</th>
                  <td>{row.screen}</td>
                  <td>{row.role}</td>
                  <td>{row.writePolicy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="production-section">
        <h2>対象別マッピング</h2>
        <div className="production-section-divider" />
        <div className="production-table-shell">
          <table className="production-table">
            <thead>
              <tr>
                <th>対象</th>
                <th>表示先</th>
                <th>反映候補</th>
                <th>確認導線</th>
              </tr>
            </thead>
            <tbody>
              {settingsPayload.targetRows.map((row) => (
                <tr key={row.target}>
                  <th>{row.target}</th>
                  <td>{row.displayPage}</td>
                  <td>{row.storedAs}</td>
                  <td>{row.reviewRoute}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="production-section">
        <h2>取得・採用ルール</h2>
        <div className="production-section-divider" />
        <table className="production-table">
          <tbody>
            {settingsPayload.ruleRows.map((row) => (
              <tr key={row.label}>
                <th>{row.label}</th>
                <td>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );
}
