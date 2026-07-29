// このファイルは、viewer3dStateの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
import { describe, expect, it } from "vitest";

import { clippingReducer, initialClippingState } from "./viewer3dState";

describe("clippingReducer", () => {
  it("toggles clipping", () => {
    const next = clippingReducer(initialClippingState, { type: "toggle" });
    expect(next.enabled).toBe(true);
  });

  it("sets bounds and resets slider to midpoint", () => {
    const next = clippingReducer(initialClippingState, {
      type: "setBounds",
      min: -5,
      max: 7,
    });
    expect(next.value).toBe(1);
  });
});
