import { useRef, useState } from "react";

import { resolveDrawingIdFromCandidate } from "../drawingRoute";

type LocalLaunchMode = "2d" | "3d";

interface DrawingEntryPanelProps {
  debugInputsEnabled: boolean;
  initialValue?: string;
  onLocalFileLaunch: (mode: LocalLaunchMode, file: File) => void;
}

const twoDFileExtensions = new Set(["pdf", "jpg", "jpeg", "tif", "tiff"]);
const threeDFileExtensions = new Set(["stl", "step", "stp"]);

function resolveLocalLaunchMode(file: File): LocalLaunchMode | null {
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (twoDFileExtensions.has(extension)) {
    return "2d";
  }
  if (threeDFileExtensions.has(extension)) {
    return "3d";
  }
  return null;
}

export function DrawingEntryPanel({
  debugInputsEnabled,
  initialValue = "",
  onLocalFileLaunch,
}: DrawingEntryPanelProps) {
  const localFileInputRef = useRef<HTMLInputElement | null>(null);
  const [value, setValue] = useState(initialValue);
  const [error, setError] = useState<string | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [localStatus, setLocalStatus] = useState<string | null>(null);

  const handleOpen = () => {
    const drawingId = resolveDrawingIdFromCandidate(value);
    if (!drawingId) {
      setError("drawingId(UUID) か `/drawing/<drawingId>` を含む URL を入力してください。");
      return;
    }

    window.location.assign(`/drawing/${drawingId}`);
  };

  return (
    <section className="panel viewer-page">
      <div className="panel-section launcher-panel">
        <div className="panel-header panel-header-stack">
          <div>
            <h2>図面を開く</h2>
            <p className="section-description">
              drawingId(UUID) または `/drawing/&lt;drawingId&gt;` を含む URL を入力してください。
            </p>
          </div>
        </div>

        <div className="form-grid launcher-form">
          <label className="input-stack">
            <span className="field-label">drawingId / URL</span>
            <input
              type="text"
              value={value}
              onChange={(event) => {
                setValue(event.target.value);
                if (error) {
                  setError(null);
                }
              }}
              placeholder="35463219-5fe5-49a0-ae7f-ed25c5661be9"
            />
          </label>
          <button className="primary-button" type="button" onClick={handleOpen}>
            drawingId で開く
          </button>
        </div>

        <div className="launcher-hint-list">
          <span>例: `35463219-5fe5-49a0-ae7f-ed25c5661be9`</span>
          <span>例: `http://localhost:5173/drawing/35463219-5fe5-49a0-ae7f-ed25c5661be9`</span>
        </div>

        {debugInputsEnabled ? (
          <div className="launcher-local-section">
            <div className="panel-header panel-header-stack">
              <div>
                <h2>ローカルファイルを開く</h2>
                <p className="section-description">
                  開発環境では、ここからローカルファイルを選ぶと 2D/3D を自動判定して詳細画面を開きます。
                </p>
                <p className="section-description">
                  対応形式: 2D は `.pdf, .jpg, .jpeg, .tif, .tiff`、3D は `.stl, .step, .stp`
                </p>
              </div>
            </div>

            <label className="input-stack">
              <span className="field-label">ローカルファイル</span>
              <div className="launcher-file-row">
                <input
                  type="text"
                  value={selectedFileName ?? ""}
                  readOnly
                  placeholder="ファイル未選択"
                />
                <input
                  ref={localFileInputRef}
                  className="sr-only-input"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.tif,.tiff,.stl,.step,.stp"
                  onClick={(event) => {
                    const target = event.currentTarget;
                    target.value = "";
                    setLocalStatus("ファイル選択ダイアログを開いています。");
                  }}
                  onChange={(event) => {
                    const file = event.target.files?.[0] ?? null;
                    setSelectedFileName(file?.name ?? null);

                    if (!file) {
                      setLocalStatus(null);
                      return;
                    }

                    const mode = resolveLocalLaunchMode(file);
                    if (!mode) {
                      setError("対応外のファイル形式です。2D は PDF/JPEG/TIFF、3D は STL/STEP/STP を選択してください。");
                      setLocalStatus("対応外のファイル形式です。");
                      return;
                    }

                    setError(null);
                    setLocalStatus(`${mode === "2d" ? "2D" : "3D"} と判定しました。詳細画面を開きます。`);
                    onLocalFileLaunch(mode, file);
                  }}
                />
                <button
                  className="primary-button launcher-file-button"
                  type="button"
                  onClick={() => {
                    localFileInputRef.current?.click();
                  }}
                >
                  ファイルを選択
                </button>
              </div>
            </label>

            {localStatus ? <p className="section-description">{localStatus}</p> : null}
          </div>
        ) : null}

        {error ? <p className="error-text">{error}</p> : null}
      </div>
    </section>
  );
}
