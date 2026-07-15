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

const runtimeSettingRows: SettingRow[] = [
  { label: "設定配置", value: "システム設定 > タグ自動取得設定" },
  { label: "AI補助", value: "Gemini API を低温度で使用" },
  { label: "温度", value: "0.0" },
  { label: "出力形式", value: "JSON固定。許可済みfield名と候補indexのみ採用" },
  { label: "採用方針", value: "ICAD 2D/3D またはパーツ付加情報に存在する値だけを採用" },
  { label: "本番書き込み", value: "行わない。創屋連携payloadの確認まで" },
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
              ICAD抽出からタグ候補を作るための共通設定です。登録・変更・削除は創屋側の本番実装範囲です。
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
