interface LoadingNoticeProps {
  title: string;
  detail: string;
  phase?: string;
}

// 見た目は共通化しつつ、文言だけを phase ごとに差し替えられる読み込み表示。
export function LoadingNotice({ title, detail, phase }: LoadingNoticeProps) {
  return (
    <div className="loading-notice" role="status" aria-live="polite" data-phase={phase}>
      <div className="loading-copy">
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
      <div className="loading-bar" aria-hidden="true">
        <div className="loading-bar-fill" />
      </div>
    </div>
  );
}
