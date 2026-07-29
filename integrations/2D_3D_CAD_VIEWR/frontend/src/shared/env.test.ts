// このファイルは、envの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
import { describe, expect, it } from "vitest";

import { isLocalFileEnabled, isViewerDebugInputsEnabled } from "./env";

describe("isLocalFileEnabled", () => {
  it("returns true for true-like strings", () => {
    expect(isLocalFileEnabled("true", false)).toBe(true);
  });

  it("returns false when flag is missing or false in production mode", () => {
    expect(isLocalFileEnabled(undefined, false)).toBe(false);
    expect(isLocalFileEnabled("false", false)).toBe(false);
  });

  it("returns true in development mode even when the flag is false", () => {
    expect(isLocalFileEnabled(undefined, true)).toBe(true);
    expect(isLocalFileEnabled("false", true)).toBe(true);
  });
});

describe("isViewerDebugInputsEnabled", () => {
  it("returns false outside development mode", () => {
    expect(isViewerDebugInputsEnabled(false)).toBe(false);
  });

  it("returns true in development mode", () => {
    expect(isViewerDebugInputsEnabled(true)).toBe(true);
  });
});
