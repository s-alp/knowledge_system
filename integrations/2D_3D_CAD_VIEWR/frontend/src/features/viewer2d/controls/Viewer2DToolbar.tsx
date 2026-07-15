import {
  IconChevronLeft,
  IconChevronRight,
  IconFocus2,
  IconRotate2,
  IconRotateClockwise2,
  IconZoomIn,
  IconZoomOut,
} from "@tabler/icons-react";

import { IconToolbarButton } from "../../../shared/components/IconToolbarButton";

interface Viewer2DToolbarProps {
  currentPage: number;
  pageCount: number;
  onPreviousPage: () => void;
  onNextPage: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetView: () => void;
  onRotateLeft: () => void;
  onRotateRight: () => void;
  canZoomIn: boolean;
  canZoomOut: boolean;
}

export function Viewer2DToolbar({
  currentPage,
  pageCount,
  onPreviousPage,
  onNextPage,
  onZoomIn,
  onZoomOut,
  onResetView,
  onRotateLeft,
  onRotateRight,
  canZoomIn,
  canZoomOut,
}: Viewer2DToolbarProps) {
  return (
    <div className="toolbar viewer-inline-toolbar knowledge-preview-toolbar">
      <IconToolbarButton ariaLabel="戻る" onClick={onPreviousPage} disabled={currentPage <= 1}>
        <IconChevronLeft size={20} stroke={1.8} />
      </IconToolbarButton>
      <IconToolbarButton
        ariaLabel="進む"
        onClick={onNextPage}
        disabled={currentPage >= pageCount || pageCount === 0}
      >
        <IconChevronRight size={20} stroke={1.8} />
      </IconToolbarButton>
      <div className="toolbar-divider" aria-hidden="true" />
      <IconToolbarButton ariaLabel="拡大" onClick={onZoomIn} disabled={!canZoomIn}>
        <IconZoomIn size={20} stroke={1.8} />
      </IconToolbarButton>
      <IconToolbarButton ariaLabel="縮小" onClick={onZoomOut} disabled={!canZoomOut}>
        <IconZoomOut size={20} stroke={1.8} />
      </IconToolbarButton>
      <IconToolbarButton ariaLabel="リセット" onClick={onResetView}>
        <IconFocus2 size={20} stroke={1.8} />
      </IconToolbarButton>
      <IconToolbarButton ariaLabel="左回転" onClick={onRotateLeft}>
        <IconRotate2 size={20} stroke={1.8} />
      </IconToolbarButton>
      <IconToolbarButton ariaLabel="右回転" onClick={onRotateRight}>
        <IconRotateClockwise2 size={20} stroke={1.8} />
      </IconToolbarButton>
      <span className="meta-pill compact">ページ {pageCount === 0 ? 0 : currentPage}/{pageCount}</span>
      <span className="toolbar-chip-label" aria-hidden="true">
        枠線クリア
      </span>
    </div>
  );
}
