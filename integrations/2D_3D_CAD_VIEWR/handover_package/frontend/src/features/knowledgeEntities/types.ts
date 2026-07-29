// このファイルは、同じ機能フォルダー内で共有するTypeScriptのデータ型を定義する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
export type KnowledgePageKey =
  | "project"
  | "product"
  | "part"
  | "drawing"
  | "document"
  | "search"
  | "chat"
  | "similar"
  | "customer"
  | "notice"
  | "master"
  | "system";
