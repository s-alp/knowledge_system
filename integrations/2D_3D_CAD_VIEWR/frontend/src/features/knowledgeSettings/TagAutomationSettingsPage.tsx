import { useEffect, useState } from "react";
import { IconChevronRight, IconDatabase, IconTransfer } from "@tabler/icons-react";

import {
  createTagDictionaryEntry,
  deleteTagDictionaryEntry,
  getDrawingMetadataHandoffSummary,
  getDrawingMetadataRegistrations,
  getTagAutomationSettings,
  getTagDictionaries,
  updateTagDictionaryEntry,
  type DrawingMetadataRegistrationListItem,
  type HandoffSummaryResponse,
  type TagAutomationSettingsResponse,
  type TagDictionaryEntryPayload,
  type TagDictionaryListResponse,
} from "../../shared/api/client";

type SettingsPanelKey = "overview" | "icad-extraction" | "handoff" | "tag-dictionaries";

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

function formatJobCount(summary: HandoffSummaryResponse | null, status: string) {
  return summary?.jobStatusCounts?.[status] ?? 0;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const pad = (number: number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function shortError(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  const firstLine = value.split(/\r?\n/).find(Boolean) ?? value;
  return firstLine.length > 96 ? `${firstLine.slice(0, 96)}...` : firstLine;
}

function failedJobErrorText(job: NonNullable<HandoffSummaryResponse["recentFailedJobs"]>[number]) {
  return job.errorMessageSummary || shortError(job.errorMessage);
}

function latestFailureText(item: DrawingMetadataRegistrationListItem) {
  const messages = (["2d", "3d"] as const)
    .map((mode) => {
      const error = item.latestJobErrorByMode?.[mode];
      return error ? `${mode.toUpperCase()}: ${shortError(error)}` : "";
    })
    .filter(Boolean);
  return messages.length ? messages.join(" / ") : "-";
}

function latestJobUpdatedText(item: DrawingMetadataRegistrationListItem) {
  const values = (["2d", "3d"] as const)
    .map((mode) => item.latestJobUpdatedAtByMode?.[mode])
    .filter((value): value is string => Boolean(value))
    .sort();
  return formatDateTime(values[values.length - 1]);
}

function formatCheck(value: boolean | null | undefined) {
  if (value == null) {
    return "-";
  }
  return value ? "はい" : "いいえ";
}

function formatSourcePreflight(job: NonNullable<HandoffSummaryResponse["recentFailedJobs"]>[number]) {
  const preflight = job.sourcePreflight;
  if (!preflight) {
    return "-";
  }
  const pathLength = preflight.sourcePathLength != null ? `${preflight.sourcePathLength}文字` : "-";
  return `原本:${formatCheck(preflight.sourceExistsFromCurrentMachine)} / 長パス退避:${formatCheck(preflight.requiresSxnetStagedInput)} / パス長:${pathLength}`;
}

function panelForAction(action: string): SettingsPanelKey {
  if (action === "open_icad_extraction_review") {
    return "icad-extraction";
  }
  if (action === "show_handoff_note") {
    return "handoff";
  }
  if (action === "open_tag_dictionaries") {
    return "tag-dictionaries";
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
    "icad-extraction": false,
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
    // タグ辞書パネルは自前で読み込むため、共通のパネル読み込み対象から外す。
    if (activePanel === "overview" || activePanel === "tag-dictionaries" || loadedPanels[activePanel]) {
      return;
    }

    let active = true;
    setPanelLoading(true);
    setError(null);
    const request =
      activePanel === "icad-extraction"
        ? Promise.all([
            cachedRegistrations ? Promise.resolve(cachedRegistrations) : getDrawingMetadataRegistrations(),
            getDrawingMetadataHandoffSummary(),
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

  useEffect(() => {
    if (activePanel !== "icad-extraction") {
      return;
    }
    let active = true;
    const refresh = () => {
      getDrawingMetadataHandoffSummary()
        .then((summary) => {
          cachedHandoffSummary = summary;
          if (active) {
            setHandoffSummary(summary);
          }
        })
        .catch((reason: unknown) => {
          if (active) {
            setError(reason instanceof Error ? reason.message : "worker状態を更新できませんでした。");
          }
        });
    };
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [activePanel]);

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
                登録済みICD単位で、2D/3D snapshot、起票後の待機・抽出中・完了・失敗、worker状態、抽出対象ファイルを確認します。
              </p>
              <p className="production-section-note">{scopeLabel(handoffSummary)}</p>
            </div>
          </div>
          <div className="production-section-divider" />
          {panelLoading ? <p className="production-section-note">抽出管理情報を読み込んでいます。</p> : null}
          {handoffSummary ? (
            <div className="production-detail-grid">
              <div className="production-detail-field">
                <span>worker状態</span>
                <p>{handoffSummary.workerStatus?.label ?? "未確認"}</p>
              </div>
              <div className="production-detail-field">
                <span>worker</span>
                <p>{handoffSummary.workerStatus?.workerName || "-"}</p>
              </div>
              <div className="production-detail-field">
                <span>worker詳細</span>
                <p>{handoffSummary.workerStatus?.message ?? "worker状態を取得できません。"}</p>
              </div>
              <div className="production-detail-field">
                <span>heartbeat更新</span>
                <p>{formatDateTime(handoffSummary.workerStatus?.updatedAt)}</p>
              </div>
              <div className="production-detail-field">
                <span>heartbeat経過</span>
                <p>{handoffSummary.workerStatus?.ageSeconds != null ? `${handoffSummary.workerStatus.ageSeconds}秒` : "-"}</p>
              </div>
              <div className="production-detail-field">
                <span>待機中/抽出中/完了/失敗</span>
                <p>{formatJobCount(handoffSummary, "queued")} / {formatJobCount(handoffSummary, "processing")} / {formatJobCount(handoffSummary, "succeeded")} / {formatJobCount(handoffSummary, "failed")}</p>
              </div>
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
                  <th>最終ジョブ更新</th>
                  <th>失敗理由</th>
                  <th>抽出で使うICADファイル</th>
                </tr>
              </thead>
              <tbody>
                {panelLoading && !registrations.length ? (
                  <tr>
                    <td colSpan={7}>抽出管理情報を読み込んでいます。</td>
                  </tr>
                ) : registrations.length ? registrations.map((item) => (
                  <tr key={item.drawingId}>
                    <th>{item.filename}</th>
                    <td>{formatSnapshotModes(item)}</td>
                    <td>{formatJobStatus(item.latestJobStatusByMode["2d"])}</td>
                    <td>{formatJobStatus(item.latestJobStatusByMode["3d"])}</td>
                    <td>{latestJobUpdatedText(item)}</td>
                    <td title={latestFailureText(item)}>{latestFailureText(item)}</td>
                    <td>{item.sourcePath}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={7}>登録済みICADはありません。</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {handoffSummary?.recentFailedJobs?.length ? (
            <div className="production-table-shell">
              <table className="production-table">
                <thead>
                  <tr>
                    <th>直近失敗ICAD</th>
                    <th>mode</th>
                    <th>分類</th>
                    <th>事前診断</th>
                    <th>worker</th>
                    <th>失敗日時</th>
                    <th>失敗理由</th>
                    <th>再抽出条件</th>
                  </tr>
                </thead>
                <tbody>
                  {handoffSummary.recentFailedJobs.map((job) => (
                    <tr key={job.jobId}>
                      <th>{job.filename}</th>
                      <td>{job.extractionMode.toUpperCase()}</td>
                      <td>{job.errorClass || "-"}</td>
                      <td>{formatSourcePreflight(job)}</td>
                      <td>{job.workerName || "-"}</td>
                      <td>{formatDateTime(job.updatedAt)}</td>
                      <td>{failedJobErrorText(job)}</td>
                      <td>{job.reextractCondition}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}

      {activePanel === "tag-dictionaries" ? <TagDictionaryPanel /> : null}

      {activePanel === "handoff" ? (
        <section className="production-section">
          <div className="production-section-header">
            <div>
              <h2>API仕様・連携仕様</h2>
              <p className="production-section-note">
                創屋へ渡す読み取りAPI、viewer/RAG連携、対象別payload候補の集計です。
              </p>
              <p className="production-section-note">{scopeLabel(handoffSummary)}</p>
            </div>
          </div>
          <div className="production-section-divider" />
          {panelLoading ? <p className="production-section-note">API仕様・連携情報を読み込んでいます。</p> : null}
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
                    <td colSpan={4}>API仕様・連携情報を読み込んでいます。</td>
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

function TagDictionaryPanel() {
  const [payload, setPayload] = useState<TagDictionaryListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [kindFilter, setKindFilter] = useState<string>("all");
  const [formKind, setFormKind] = useState<string>("customer");
  const [formCanonical, setFormCanonical] = useState("");
  const [formAliases, setFormAliases] = useState("");
  const [saving, setSaving] = useState(false);

  const reload = () => {
    setLoading(true);
    getTagDictionaries()
      .then((response) => {
        setPayload(response);
        setError(null);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "タグ辞書を取得できませんでした。");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = () => {
    if (!formCanonical.trim()) {
      setError("正規名を入力してください。");
      return;
    }
    setSaving(true);
    setError(null);
    createTagDictionaryEntry({
      kind: formKind,
      canonicalValue: formCanonical.trim(),
      aliases: formAliases
        .split(/[、,]/)
        .map((alias) => alias.trim())
        .filter(Boolean),
    })
      .then((entry) => {
        setNotice(`「${entry.kindLabel}:${entry.canonicalValue}」を登録しました。既存図面への反映には再正規化が必要です。`);
        setFormCanonical("");
        setFormAliases("");
        reload();
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "登録に失敗しました。");
      })
      .finally(() => setSaving(false));
  };

  const toggleEnabled = (entry: TagDictionaryEntryPayload) => {
    updateTagDictionaryEntry(entry.id, { enabled: !entry.enabled })
      .then(() => reload())
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "更新に失敗しました。"));
  };

  const removeEntry = (entry: TagDictionaryEntryPayload) => {
    if (!window.confirm(`「${entry.kindLabel}:${entry.canonicalValue}」を削除しますか？`)) {
      return;
    }
    deleteTagDictionaryEntry(entry.id)
      .then(() => reload())
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "削除に失敗しました。"));
  };

  const entries = (payload?.entries ?? []).filter((entry) => kindFilter === "all" || entry.kind === kindFilter);

  return (
    <section className="production-section">
      <div className="production-section-header">
        <div>
          <h2>タグ辞書管理</h2>
          <p className="production-section-note">
            客先・案件・装置カテゴリ・メーカー・規格・熱処理の語彙を登録します。ここに登録した語が抽出時の照合とタグ生成に使われます。
          </p>
          <p className="production-section-note">{payload?.seedFallbackNote ?? ""}</p>
        </div>
      </div>
      <div className="production-section-divider" />
      {error ? <p className="production-section-note error-panel">{error}</p> : null}
      {notice ? <p className="production-section-note">{notice}</p> : null}

      <div className="production-detail-grid">
        <div className="production-detail-field">
          <span>種別</span>
          <select value={formKind} onChange={(event) => setFormKind(event.target.value)}>
            {(payload?.kinds ?? []).map((kind) => (
              <option key={kind.kind} value={kind.kind}>
                {kind.label}
              </option>
            ))}
          </select>
        </div>
        <div className="production-detail-field">
          <span>正規名(タグに使う名前)</span>
          <input
            type="text"
            value={formCanonical}
            placeholder="例: 不二越"
            onChange={(event) => setFormCanonical(event.target.value)}
          />
        </div>
        <div className="production-detail-field">
          <span>別名・略名(読点/カンマ区切り)</span>
          <input
            type="text"
            value={formAliases}
            placeholder="例: 不二越5、NACHI"
            onChange={(event) => setFormAliases(event.target.value)}
          />
        </div>
        <div className="production-detail-field">
          <span>&nbsp;</span>
          <button type="button" onClick={submit} disabled={saving}>
            {saving ? "登録中..." : "辞書へ登録"}
          </button>
        </div>
      </div>

      <div className="production-section-divider" />
      <div className="production-detail-field">
        <span>表示する種別</span>
        <select value={kindFilter} onChange={(event) => setKindFilter(event.target.value)}>
          <option value="all">すべて</option>
          {(payload?.kinds ?? []).map((kind) => (
            <option key={kind.kind} value={kind.kind}>
              {kind.label}
            </option>
          ))}
        </select>
      </div>
      {loading ? <p className="production-section-note">タグ辞書を読み込んでいます。</p> : null}
      <div className="production-table-shell">
        <table className="production-table">
          <thead>
            <tr>
              <th>種別</th>
              <th>正規名</th>
              <th>別名・略名</th>
              <th>有効</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {entries.length ? (
              entries.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.kindLabel}</td>
                  <td>{entry.canonicalValue}</td>
                  <td>{entry.aliases.length ? entry.aliases.join("、") : "-"}</td>
                  <td>{entry.enabled ? "有効" : "無効"}</td>
                  <td>
                    <button type="button" onClick={() => toggleEnabled(entry)}>
                      {entry.enabled ? "無効にする" : "有効にする"}
                    </button>{" "}
                    <button type="button" onClick={() => removeEntry(entry)}>
                      削除
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5}>{loading ? "-" : "登録済みの辞書エントリはありません(seed辞書で動作中)。"}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
