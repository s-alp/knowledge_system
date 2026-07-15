import type { DrawingKnowledgeMock } from "../../shared/mock/drawingKnowledge";

type SettingRow = {
  label: string;
  value: string;
};

type TargetMappingRow = {
  target: string;
  displayPage: string;
  storedAs: string;
  reviewRoute: string;
};

type OperationRow = {
  area: string;
  screen: string;
  role: string;
  writePolicy: string;
};

const runtimeSettingRows: SettingRow[] = [
  { label: "設定配置", value: "システム設定 > タグ自動取得設定" },
  { label: "AI補助", value: "Gemini API を低温度で使用" },
  { label: "温度", value: "0.0" },
  { label: "出力形式", value: "JSON固定。許可済みfield名と候補indexのみ採用" },
  { label: "採用方針", value: "ICAD 2D/3D またはパーツ付加情報に存在する値だけを採用" },
  { label: "本番書き込み", value: "行わない。創屋連携payloadの確認まで" },
];

const operationRows: OperationRow[] = [
  {
    area: "設定",
    screen: "システム設定 > タグ自動取得設定",
    role: "LLM、温度、タグルール、採用方針を管理する。",
    writePolicy: "本番保存は創屋実装側。こちらは設定値とpayload仕様を渡す。",
  },
  {
    area: "確認・再抽出・手直し",
    screen: "図面管理 > タグ候補レビュー",
    role: "2D/3D/パーツ付加情報の抽出結果、競合、対象別payloadを確認する。",
    writePolicy: "ローカルDBの手動補正と再抽出ジョブだけを扱う。",
  },
  {
    area: "表示",
    screen: "図面詳細 / 製品・装置・ユニット詳細 / 部品詳細",
    role: "確定候補をタグ・属性情報として表示し、紐づき候補も確認する。",
    writePolicy: "本番ナレッジシステムの登録・変更・削除は行わない。",
  },
  {
    area: "連携",
    screen: "創屋連携payload",
    role: "創屋が本番側に埋め込める形で対象、属性、タグ、根拠を出力する。",
    writePolicy: "読み取り確認とfixture/API出力まで。",
  },
];

const targetMappingRows: TargetMappingRow[] = [
  {
    target: "図面",
    displayPage: "図面詳細 / 図面管理",
    storedAs: "tags / 属性情報",
    reviewRoute: "図面管理 > タグ候補レビュー",
  },
  {
    target: "製品・装置・ユニット",
    displayPage: "製品・装置・ユニット詳細",
    storedAs: "属性情報 / 関連情報",
    reviewRoute: "図面管理 > 対象別payload確認",
  },
  {
    target: "部品",
    displayPage: "部品詳細",
    storedAs: "属性情報 / 関連情報",
    reviewRoute: "図面管理 > 対象別payload確認",
  },
  {
    target: "プロジェクト",
    displayPage: "プロジェクト詳細",
    storedAs: "現時点は保留",
    reviewRoute: "創屋の保存口確認後に再判定",
  },
];

const extractionRuleRows: SettingRow[] = [
  { label: "2D", value: "図枠、中央図面、寸法、注記、訂正内容、材質、表面処理、尺度、PRFX、ユニット番号" },
  { label: "3D", value: "図面名、図面サイズ候補、重量、材質、パーツツリー、パーツ付加情報、PRFX、ユニット番号" },
  { label: "照合", value: "2D/3D の同名属性は統合し、競合と診断差分を分けてレビューへ出す" },
  { label: "図枠外", value: "印刷枠内を自動採用優先。枠外・枠不明は証跡として残してレビュー対象" },
];

// この画面は設定の受け皿です。ICAD抽出とタグ生成の本体はバックエンド側で行います。
export function TagAutomationSettingsPage({ detail }: { detail: DrawingKnowledgeMock | null }) {
  const targetCount = detail?.tagAttributeTargets.length ?? 0;
  const tagCount = detail?.tagAttributeTargets.reduce((sum, target) => sum + target.tags.length, 0) ?? 0;
  const attributeCount =
    detail?.tagAttributeTargets.reduce((sum, target) => sum + target.attributes.length, 0) ?? 0;

  return (
    <section className="knowledge-production-page entity-page">
      <section className="production-section production-basic-section">
        <div className="production-section-header">
          <div>
            <h2>タグ自動取得設定</h2>
            <p className="production-section-note">
              ICAD抽出からタグ候補を作るための運用設定です。登録・変更・削除は創屋側の本番実装範囲です。
            </p>
          </div>
        </div>
        <div className="production-section-divider" />
        <div className="production-detail-grid">
          {runtimeSettingRows.map((row) => (
            <div key={row.label} className="production-detail-field">
              <span>{row.label}</span>
              <p>{row.value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="production-section">
        <h2>運用配置</h2>
        <div className="production-section-divider" />
        <div className="production-table-shell">
          <table className="production-table">
            <thead>
              <tr>
                <th>領域</th>
                <th>画面</th>
                <th>役割</th>
                <th>書き込み方針</th>
              </tr>
            </thead>
            <tbody>
              {operationRows.map((row) => (
                <tr key={row.area}>
                  <th>{row.area}</th>
                  <td>{row.screen}</td>
                  <td>{row.role}</td>
                  <td>{row.writePolicy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="production-section">
        <h2>対象別マッピング</h2>
        <div className="production-section-divider" />
        <div className="production-table-shell">
          <table className="production-table">
            <thead>
              <tr>
                <th>対象</th>
                <th>表示先</th>
                <th>反映候補</th>
                <th>確認導線</th>
              </tr>
            </thead>
            <tbody>
              {targetMappingRows.map((row) => (
                <tr key={row.target}>
                  <th>{row.target}</th>
                  <td>{row.displayPage}</td>
                  <td>{row.storedAs}</td>
                  <td>{row.reviewRoute}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="production-section">
        <h2>取得・採用ルール</h2>
        <div className="production-section-divider" />
        <table className="production-table">
          <tbody>
            {extractionRuleRows.map((row) => (
              <tr key={row.label}>
                <th>{row.label}</th>
                <td>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="production-section">
        <h2>現在表示中データの候補数</h2>
        <div className="production-section-divider" />
        <div className="production-detail-grid">
          <div className="production-detail-field">
            <span>対象数</span>
            <p>{targetCount}</p>
          </div>
          <div className="production-detail-field">
            <span>タグ候補</span>
            <p>{tagCount}</p>
          </div>
          <div className="production-detail-field">
            <span>属性候補</span>
            <p>{attributeCount}</p>
          </div>
          <div className="production-detail-field">
            <span>レビュー</span>
            <p>{detail?.tagAttributeReviewRequired ? "必要" : "候補なし、または不要"}</p>
          </div>
        </div>
      </section>
    </section>
  );
}
