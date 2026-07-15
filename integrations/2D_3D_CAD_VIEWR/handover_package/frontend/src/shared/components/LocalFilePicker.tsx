import { useRef } from "react";

interface LocalFilePickerProps {
  acceptedTypes: string;
  helperText: string;
  selectedFileName?: string;
  onFileChange: (file: File | null) => void;
  onPickStart?: () => void;
  onPickComplete?: (file: File | null) => void;
  onOpen: () => void;
  browseDisabled?: boolean;
  openDisabled?: boolean;
  buttonLabel: string;
  statusText?: string;
}

export function LocalFilePicker({
  acceptedTypes,
  helperText,
  selectedFileName,
  onFileChange,
  onPickStart,
  onPickComplete,
  onOpen,
  browseDisabled,
  openDisabled,
  buttonLabel,
  statusText,
}: LocalFilePickerProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const pendingSelectionRef = useRef(false);
  const selectionResolvedRef = useRef(false);

  const handleBrowseClick = () => {
    const input = inputRef.current;
    if (!input) {
      return;
    }

    onPickStart?.();
    input.value = "";
    pendingSelectionRef.current = true;
    selectionResolvedRef.current = false;

    const handleWindowFocus = () => {
      window.setTimeout(() => {
        // ネイティブのファイルダイアログは cancel を直接拾えないため、
        // focus 復帰時に未選択なら picker 完了として扱う。
        const file = inputRef.current?.files?.[0] ?? null;
        if (pendingSelectionRef.current && !selectionResolvedRef.current && !file) {
          pendingSelectionRef.current = false;
          selectionResolvedRef.current = true;
          onPickComplete?.(null);
        }
      }, 250);
    };

    window.addEventListener("focus", handleWindowFocus, { once: true });
    input.click();
  };

  return (
    <div className="panel local-file-panel">
      <div className="panel-header panel-header-stack">
        <div>
          <p className="section-eyebrow">Local Check</p>
          <h3>ローカルファイル選択</h3>
          <p className="section-description">{helperText}</p>
        </div>
      </div>
      <div className="form-grid">
        <label className="input-stack">
          <span className="field-label">検証用ファイル</span>
          <input
            ref={inputRef}
            type="file"
            accept={acceptedTypes}
            className="sr-only-input"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              pendingSelectionRef.current = false;
              selectionResolvedRef.current = true;
              onFileChange(file);
              onPickComplete?.(file);
            }}
          />
          <button className="ghost-button" type="button" onClick={handleBrowseClick} disabled={browseDisabled}>
            ファイルを選択
          </button>
          <input value={selectedFileName ?? ""} readOnly placeholder="ファイル未選択" />
        </label>
        <button className="secondary-button" type="button" onClick={onOpen} disabled={openDisabled}>
          {buttonLabel}
        </button>
      </div>
      <div className="status">
        {statusText ? <span>{statusText}</span> : null}
        {selectedFileName ? <span>選択中: {selectedFileName}</span> : <span>ファイル未選択</span>}
      </div>
    </div>
  );
}
