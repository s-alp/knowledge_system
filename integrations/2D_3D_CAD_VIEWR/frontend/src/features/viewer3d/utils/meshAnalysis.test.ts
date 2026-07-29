// このファイルは、meshAnalysisの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
import { BufferGeometry, Float32BufferAttribute } from "three";
import { describe, expect, it } from "vitest";

import { analyzeClosedMesh } from "./meshAnalysis";

function createGeometry(vertices: number[]) {
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new Float32BufferAttribute(vertices, 3));
  return geometry;
}

describe("analyzeClosedMesh", () => {
  it("detects a closed tetrahedron mesh", () => {
    const geometry = createGeometry([
      0, 0, 0, 1, 0, 0, 0, 1, 0,
      0, 0, 0, 0, 1, 0, 0, 0, 1,
      0, 0, 0, 0, 0, 1, 1, 0, 0,
      1, 0, 0, 0, 0, 1, 0, 1, 0,
    ]);

    expect(analyzeClosedMesh(geometry).isClosed).toBe(true);
  });

  it("detects an open mesh", () => {
    const geometry = createGeometry([
      0, 0, 0, 1, 0, 0, 0, 1, 0,
      0, 0, 0, 0, 1, 0, 0, 0, 1,
    ]);

    expect(analyzeClosedMesh(geometry).isClosed).toBe(false);
  });
});
