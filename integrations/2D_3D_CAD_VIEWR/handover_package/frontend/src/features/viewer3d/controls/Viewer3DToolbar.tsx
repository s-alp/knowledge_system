import { IconFocus2, IconZoomIn, IconZoomOut } from "@tabler/icons-react";

import { IconToolbarButton } from "../../../shared/components/IconToolbarButton";

interface Viewer3DToolbarProps {
  clippingEnabled: boolean;
  edgeHighlightEnabled: boolean;
  onReset: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onToggleClipping: () => void;
  onToggleEdgeHighlight: () => void;
}

export function Viewer3DToolbar({
  clippingEnabled,
  edgeHighlightEnabled,
  onReset,
  onZoomIn,
  onZoomOut,
  onToggleClipping,
  onToggleEdgeHighlight,
}: Viewer3DToolbarProps) {
  return (
    <div className="toolbar viewer-inline-toolbar knowledge-preview-toolbar">
      <IconToolbarButton ariaLabel="拡大" onClick={onZoomIn}>
        <IconZoomIn size={20} stroke={1.8} />
      </IconToolbarButton>
      <IconToolbarButton ariaLabel="縮小" onClick={onZoomOut}>
        <IconZoomOut size={20} stroke={1.8} />
      </IconToolbarButton>
      <IconToolbarButton ariaLabel="リセット" onClick={onReset}>
        <IconFocus2 size={20} stroke={1.8} />
      </IconToolbarButton>
      <div className="toolbar-divider" aria-hidden="true" />
      <button className="secondary-button compact-text-button" onClick={onToggleClipping} type="button">
        {clippingEnabled ? "断面オフ" : "断面オン"}
      </button>
      <button className="ghost-button compact-text-button" onClick={onToggleEdgeHighlight} type="button">
        {edgeHighlightEnabled ? "輪郭強調 OFF" : "輪郭強調 ON"}
      </button>
    </div>
  );
}
