import { useState } from "react";

import type { DrawingKnowledgeDetail } from "../knowledge/drawingKnowledge";

interface DrawingSupplementPanelsProps {
  detail: DrawingKnowledgeDetail;
}

const ATTRIBUTE_VALUE_PREVIEW_LENGTH = 160;

function confidenceLabel(value: string): string {
  if (value === "high") return "高";
  if (value === "medium") return "中";
  if (value === "low") return "低";
  return value || "-";
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
              <h2>タグ・属性候補</h2>
            </div>
            {detail.tagAttributeReviewRequired ? (
              <span className="tag-review-status">レビュー要</span>
            ) : null}
          </div>
          {detail.tagAttributeTargets.length > 0 ? (
            <div className="tag-target-grid">
              {detail.tagAttributeTargets.map((target) => (
                <article key={target.targetKey} className="tag-target-card">
                  <div className="tag-target-card-header">
                    <div>
                      <strong>{target.label}</strong>
                      <p>{target.tagApiStatus}</p>
                    </div>
                    <span>{target.attributes.length} 属性</span>
                  </div>
                  <div className="tag-chip-row">
                    {target.tags.length > 0 ? (
                      target.tags.map((tag) => (
                        <span key={tag} className="related-chip tag-chip">
                          {tag}
                        </span>
                      ))
                    ) : (
                      <span className="tag-target-empty">タグなし</span>
                    )}
                  </div>
                  {target.tagEvidence && target.tagEvidence.length > 0 ? (
                    <div className="tag-evidence-list">
                      <strong>タグ根拠</strong>
                      {target.tagEvidence.slice(0, 4).map((item) => (
                        <dl key={`${target.targetKey}-${item.tag}-${item.evidence}`}>
                          <div>
                            <dt>タグ</dt>
                            <dd>{item.tag}</dd>
                          </div>
                          <div>
                            <dt>取得元</dt>
                            <dd>{item.source}</dd>
                          </div>
                          <div>
                            <dt>信頼度</dt>
                            <dd>{confidenceLabel(item.confidence)}</dd>
                          </div>
                          <div>
                            <dt>採用理由</dt>
                            <dd>{item.reason}</dd>
                          </div>
                        </dl>
                      ))}
                      {target.tagEvidence.length > 4 ? (
                        <p>{target.tagEvidence.length - 4} 件のタグ根拠を省略</p>
                      ) : null}
                    </div>
                  ) : null}
                  {target.attributes.length > 0 ? (
                    <dl className="tag-attribute-list">
                      {target.attributes.slice(0, 6).map((attribute) => (
                        <div key={`${target.targetKey}-${attribute.name}-${attribute.value}`}>
                          <dt>{attribute.name}</dt>
                          <dd>
                            <AttributeValue value={attribute.value} />
                          </dd>
                        </div>
                      ))}
                      {target.attributes.length > 6 ? (
                        <div>
                          <dt>ほか</dt>
                          <dd>{target.attributes.length - 6} 属性</dd>
                        </div>
                      ) : null}
                    </dl>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state-panel compact supplemental-empty-state">
              <p>タグ・属性候補はありません。</p>
            </div>
          )}
          {detail.tagAttributePolicy !== "-" ? (
            <p className="tag-policy-note">{detail.tagAttributePolicy}</p>
          ) : null}
          <p className="tag-policy-note">
            抽出結果の確認、再抽出、手直しは図面管理のタグ候補レビューで行います。
          </p>
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

function AttributeValue({ value }: { value: string }) {
  if (value.length <= ATTRIBUTE_VALUE_PREVIEW_LENGTH) {
    return <>{value}</>;
  }

  const preview = `${value.slice(0, ATTRIBUTE_VALUE_PREVIEW_LENGTH)}...`;

  return (
    <details className="attribute-value-details">
      <summary>
        <span className="attribute-value-preview">{preview}</span>
      </summary>
      <p>{value}</p>
    </details>
  );
}
