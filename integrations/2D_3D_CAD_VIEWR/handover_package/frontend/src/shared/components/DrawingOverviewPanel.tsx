import { IconPencil, IconStarFilled, IconTrash } from "@tabler/icons-react";
import type { ReactNode } from "react";

import type { DrawingField } from "../knowledge/drawingKnowledge";

interface DrawingOverviewPanelProps {
  version?: string | null;
  fields: DrawingField[];
  attributes: DrawingField[];
  remarks: string;
  metadataContent?: ReactNode;
  footerContent?: ReactNode;
}

export function DrawingOverviewPanel({
  version,
  fields,
  attributes,
  remarks,
  metadataContent,
  footerContent,
}: DrawingOverviewPanelProps) {
  return (
    <div className="panel-section viewer-info-card knowledge-info-card">
      <div className="panel-header panel-header-inline knowledge-info-header">
        <div className="knowledge-heading">
          <h2>基本情報</h2>
          {version ? <span className="knowledge-version">ver.{version}</span> : null}
          <span className="knowledge-favorite-icon" aria-hidden="true">
            <IconStarFilled size={20} stroke={1.6} />
          </span>
        </div>
        <div className="knowledge-header-actions" aria-hidden="true">
          <span className="knowledge-header-action-icon">
            <IconPencil size={18} stroke={1.8} />
          </span>
          <span className="knowledge-header-action-icon knowledge-header-action-icon-danger">
            <IconTrash size={18} stroke={1.8} />
          </span>
        </div>
      </div>

      <div className="detail-field-grid">
        {fields.map((item) => (
          <div key={item.label} className="detail-field">
            <span className="detail-field-label">{item.label}</span>
            <strong className="detail-field-value">{item.value}</strong>
          </div>
        ))}
      </div>

      <div className="detail-divider" />

      <div className="knowledge-subsection">
        <h3 className="knowledge-subsection-title">属性情報</h3>
        {attributes.length > 0 ? (
          <div className="attribute-grid">
            {attributes.map((attribute) => (
              <div key={attribute.label} className="attribute-item">
                <span className="attribute-label">{attribute.label}</span>
                <strong className="attribute-value">{attribute.value}</strong>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state-panel compact supplemental-empty-state">
            <p>属性情報がありません。</p>
          </div>
        )}
      </div>

      <div className="detail-divider" />

      <div className="knowledge-subsection">
        <h3 className="knowledge-subsection-title">備考</h3>
        <p className="knowledge-remarks">{remarks}</p>
      </div>

      {metadataContent ? (
        <>
          <div className="detail-divider" />
          {metadataContent}
        </>
      ) : null}

      {footerContent ? (
        <>
          <div className="detail-divider" />
          {footerContent}
        </>
      ) : null}
    </div>
  );
}
