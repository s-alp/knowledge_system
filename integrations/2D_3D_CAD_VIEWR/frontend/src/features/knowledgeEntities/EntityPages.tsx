// このファイルは、製品・装置・ユニットと部品の一覧・詳細画面を共通入口から切り替える。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
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
