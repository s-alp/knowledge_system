// このファイルは、clientの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "./client";

describe("resolveApiBaseUrl", () => {
  it("keeps relative API base URLs relative so the Vite proxy can route them", () => {
    expect(resolveApiBaseUrl("/api/v1", true)).toBe("/api/v1");
  });

  it("uses the relative API base by default in development", () => {
    expect(resolveApiBaseUrl(undefined, true)).toBe("/api/v1");
  });

  it("keeps absolute API base URLs when explicitly configured", () => {
    expect(resolveApiBaseUrl("http://127.0.0.1:8001/api/v1", true)).toBe("http://127.0.0.1:8001/api/v1");
  });
});
