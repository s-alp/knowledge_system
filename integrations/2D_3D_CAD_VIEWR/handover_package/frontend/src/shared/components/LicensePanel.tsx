// このファイルは、ビューワーで使用する外部ライブラリのライセンス導線を表示する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
export function LicensePanel() {
  return (
    <details className="license-disclosure">
      <summary>ライセンス</summary>
      <div className="license-panel">
        <p>
          STEP 変換では CadQuery / OCP / OCCT を利用します。配布時は `docs/THIRD_PARTY_NOTICES.md`
          と `docs/licenses/` を同梱してください。
        </p>
        <ul>
          <li>PDF.js: Apache-2.0</li>
          <li>UTIF.js: MIT</li>
          <li>three.js / React Three Fiber / Drei: MIT</li>
          <li>CadQuery / OCP: Apache-2.0</li>
          <li>OCCT: LGPL-2.1 with additional exception</li>
        </ul>
      </div>
    </details>
  );
}
