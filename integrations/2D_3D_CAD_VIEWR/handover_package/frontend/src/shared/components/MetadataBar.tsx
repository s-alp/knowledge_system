interface MetadataBarProps {
  filename?: string;
  currentPage?: number;
  pageCount?: number;
  formatLabel?: string;
}

/**
 * ファイル名、ページ数、形式のような軽いメタ情報だけを横並びで出す部品。
 * viewer 本体の状態に依存しないので、2D / 3D の両方から使う。
 */
export function MetadataBar({
  filename,
  currentPage,
  pageCount,
  formatLabel,
}: MetadataBarProps) {
  return (
    <div className="meta-grid">
      {filename ? (
        <span className="meta-pill">
          <span className="meta-pill-label">ファイル</span>
          <strong className="meta-pill-value">{filename}</strong>
        </span>
      ) : null}
      {typeof currentPage === "number" && typeof pageCount === "number" ? (
        <span className="meta-pill">
          <span className="meta-pill-label">ページ</span>
          <strong className="meta-pill-value">
            {currentPage}/{pageCount}
          </strong>
        </span>
      ) : null}
      {formatLabel ? (
        <span className="meta-pill">
          <span className="meta-pill-label">形式</span>
          <strong className="meta-pill-value">{formatLabel}</strong>
        </span>
      ) : null}
    </div>
  );
}
