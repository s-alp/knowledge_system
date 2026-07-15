import { useState } from "react";

import type { DrawingKnowledgeMock } from "../mock/drawingKnowledge";

interface DrawingSupplementPanelsProps {
  detail: DrawingKnowledgeMock;
}

export function DrawingSupplementPanels({ detail }: DrawingSupplementPanelsProps) {
  const [activeTabId, setActiveTabId] = useState(detail.relatedTabs[0]?.id ?? "");
  const activeTab =
    detail.relatedTabs.find((tab) => tab.id === activeTabId) ?? detail.relatedTabs[0] ?? null;

  return (
    <>
      <section className="panel supplemental-panel">
        <div className="panel-section supplemental-section">
          <div className="panel-header panel-header-inline">
            <div>
              <h2>改訂履歴</h2>
            </div>
          </div>
          {detail.revisionHistory.length > 0 ? (
            <div className="revision-list">
              {detail.revisionHistory.map((item) => (
                <article key={`${item.version}-${item.updatedAt}`} className="revision-card">
                  <div className="revision-card-main">
                    <div className="revision-card-heading">
                      <strong>{item.version}</strong>
                      <span className="revision-status">{item.status}</span>
                    </div>
                    <p>{item.summary}</p>
                  </div>
                  <dl className="revision-card-meta">
                    <div>
                      <dt>変更日時</dt>
                      <dd>{item.updatedAt}</dd>
                    </div>
                    <div>
                      <dt>変更者</dt>
                      <dd>{item.updatedBy}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state-panel compact supplemental-empty-state">
              <p>改訂履歴はありません。</p>
            </div>
          )}
        </div>
      </section>

      <section className="panel supplemental-panel">
        <div className="panel-section supplemental-section">
          <div className="panel-header panel-header-inline">
            <div>
              <h2>関連情報</h2>
            </div>
          </div>
          <div className="related-tabs" role="tablist" aria-label="related information">
            {detail.relatedTabs.map((tab) => (
              <button
                key={tab.id}
                className={tab.id === activeTab?.id ? "related-tab active" : "related-tab"}
                type="button"
                role="tab"
                aria-selected={tab.id === activeTab?.id}
                onClick={() => setActiveTabId(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {activeTab && activeTab.items.length > 0 ? (
            <div className="related-card-grid">
              {activeTab.items.map((item) => (
                <article key={item.id} className="related-card">
                  <div className="related-card-header">
                    <div>
                      <strong>{item.title}</strong>
                      <p>{item.subtitle}</p>
                    </div>
                    <div className="related-card-chips">
                      {item.chips.map((chip) => (
                        <span key={chip} className="related-chip">
                          {chip}
                        </span>
                      ))}
                    </div>
                  </div>
                  <p className="related-card-description">{item.description}</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state-panel compact supplemental-empty-state">
              <p>関連情報はありません。</p>
            </div>
          )}
        </div>
      </section>

      <section className="panel supplemental-panel">
        <div className="panel-section supplemental-section">
          <div className="panel-header panel-header-inline">
            <div>
              <h2>変更履歴</h2>
            </div>
          </div>
          <div className="history-table-shell">
            <table className="history-table">
              <thead>
                <tr>
                  <th>バージョン</th>
                  <th>変更日時</th>
                  <th>変更者</th>
                  <th>変更内容</th>
                </tr>
              </thead>
              <tbody>
                {detail.changeHistory.length > 0 ? (
                  detail.changeHistory.map((item) => (
                    <tr key={`${item.version}-${item.changedAt}`}>
                      <td>{item.version}</td>
                      <td>{item.changedAt}</td>
                      <td>{item.changedBy}</td>
                      <td>{item.summary}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4}>変更履歴がありません。</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </>
  );
}
