export type DetailPageKey = "product" | "part";

export function PlaceholderKnowledgePage({ title }: { title: string }) {
  return (
    <section className="panel viewer-page">
      <div className="panel-section workspace-message">
        <h2>{title}</h2>
        <p>現在の確認対象は図面、製品・装置・ユニット、部品です。</p>
      </div>
    </section>
  );
}
