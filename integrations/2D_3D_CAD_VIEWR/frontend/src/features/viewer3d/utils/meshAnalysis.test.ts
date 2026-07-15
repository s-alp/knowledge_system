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
