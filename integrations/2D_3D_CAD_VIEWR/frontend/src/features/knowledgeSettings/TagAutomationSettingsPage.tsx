import { useEffect, useState } from "react";
import { IconChevronRight, IconDatabase, IconTransfer } from "@tabler/icons-react";

import {
  getTagAutomationSettings,
  type TagAutomationSettingsResponse,
} from "../../shared/api/client";


export function TagAutomationSettingsPage() {
  const [settingsPayload, setSettingsPayload] = useState<TagAutomationSettingsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getTagAutomationSettings()
      .then((payload) => {
        if (active) {
          setSettingsPayload(payload);
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
            return (
              <a key={link.key} className="settings-management-link" href={link.url}>
                <span className="settings-management-icon" aria-hidden="true">
                  <LinkIcon size={21} stroke={1.8} />
                </span>
                <span className="settings-management-copy">
                  <strong>{link.label}</strong>
                  <span>{link.description}</span>
                </span>
                <IconChevronRight className="settings-management-chevron" size={20} aria-hidden="true" />
              </a>
            );
          })}
        </div>
      </section>

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
