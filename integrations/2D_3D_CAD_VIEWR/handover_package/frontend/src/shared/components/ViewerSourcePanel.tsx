import { isLocalFileEnabled } from "../env";
import { LocalFilePicker } from "./LocalFilePicker";

interface ViewerSourcePanelProps {
  title: string;
  description: string;
  sectionLabel?: string;
  url: string;
  urlPlaceholder: string;
  urlButtonLabel: string;
  acceptedTypes: string;
  localHelperText: string;
  selectedFileName?: string;
  localFileStatus?: string;
  openBusy: boolean;
  onUrlChange: (value: string) => void;
  onOpenUrl: () => void;
  onFileChange: (file: File | null) => void;
  onPickStart: () => void;
  onPickComplete: (file: File | null) => void;
}

/**
 * 2D / 3D で共通になる入力 UI を寄せ、各ページは表示本体に集中させる。
 */
export function ViewerSourcePanel({
  title,
  description,
  sectionLabel,
  url,
  urlPlaceholder,
  urlButtonLabel,
  acceptedTypes,
  localHelperText,
  selectedFileName,
  localFileStatus,
  openBusy,
  onUrlChange,
  onOpenUrl,
  onFileChange,
  onPickStart,
  onPickComplete,
}: ViewerSourcePanelProps) {
  return (
    <>
      <div className="panel-header panel-header-stack">
        <div>
          {sectionLabel ? <p className="section-eyebrow">{sectionLabel}</p> : null}
          <h2>{title}</h2>
          <p className="section-description">{description}</p>
        </div>
      </div>

      <div className="form-grid">
        <label className="input-stack">
          <span className="field-label">File URL</span>
          <input
            value={url}
            onChange={(event) => onUrlChange(event.target.value)}
            placeholder={urlPlaceholder}
          />
        </label>
        <button className="primary-button" onClick={onOpenUrl} disabled={!url || openBusy} type="button">
          {openBusy ? "Loading..." : urlButtonLabel}
        </button>
      </div>

      {isLocalFileEnabled() ? (
        <LocalFilePicker
          acceptedTypes={acceptedTypes}
          helperText={localHelperText}
          selectedFileName={selectedFileName}
          onFileChange={onFileChange}
          onPickStart={onPickStart}
          onPickComplete={onPickComplete}
          // この画面では選択後に自動送信するため、明示的な open ボタン操作は使わない。
          onOpen={() => {}}
          browseDisabled={openBusy}
          openDisabled
          buttonLabel="自動送信"
          statusText={localFileStatus}
        />
      ) : null}
    </>
  );
}
