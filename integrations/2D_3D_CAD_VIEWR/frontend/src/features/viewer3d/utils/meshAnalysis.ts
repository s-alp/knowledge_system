import { Box3, BufferGeometry, Vector3 } from "three";

const DEFAULT_TOLERANCE = 1e-5;

export interface ClosedMeshAnalysis {
  bounds: Box3;
  isClosed: boolean;
}

// STL の断面キャップ可否を判定するため、mesh が閉じているかを簡易検査する。
export function analyzeClosedMesh(
  geometry: BufferGeometry,
  tolerance = DEFAULT_TOLERANCE,
): ClosedMeshAnalysis {
  // indexed geometry のままだと辺の数え上げがしにくいため、三角形列へ正規化する。
  const workingGeometry = geometry.index ? geometry.toNonIndexed() ?? geometry : geometry;
  const positionAttribute = workingGeometry.getAttribute("position");
  const edgeCounts = new Map<string, number>();

  if (!positionAttribute || positionAttribute.count < 3) {
    geometry.computeBoundingBox();
    return {
      bounds: geometry.boundingBox?.clone() ?? new Box3(),
      isClosed: false,
    };
  }

  const verticesPerTriangle = 3;
  for (let index = 0; index < positionAttribute.count; index += verticesPerTriangle) {
    // 微小な座標ぶれで別頂点扱いにならないよう、許容誤差つきで丸める。
    const a = quantizeVertex(positionAttribute, index, tolerance);
    const b = quantizeVertex(positionAttribute, index + 1, tolerance);
    const c = quantizeVertex(positionAttribute, index + 2, tolerance);

    incrementEdge(edgeCounts, a, b);
    incrementEdge(edgeCounts, b, c);
    incrementEdge(edgeCounts, c, a);
  }

  geometry.computeBoundingBox();
  const bounds = geometry.boundingBox?.clone() ?? new Box3();
  const isClosed = edgeCounts.size > 0 && [...edgeCounts.values()].every((count) => count === 2);

  return { bounds, isClosed };
}

function quantizeVertex(attribute: BufferGeometry["attributes"]["position"], index: number, tolerance: number) {
  const x = Math.round(attribute.getX(index) / tolerance);
  const y = Math.round(attribute.getY(index) / tolerance);
  const z = Math.round(attribute.getZ(index) / tolerance);
  return `${x},${y},${z}`;
}

function incrementEdge(edgeCounts: Map<string, number>, start: string, end: string) {
  // 向きに関係なく同じ辺として数えるため、key 生成前に並びを正規化する。
  const edgeKey = [start, end].sort().join("|");
  edgeCounts.set(edgeKey, (edgeCounts.get(edgeKey) ?? 0) + 1);
}

export function createCapPlaneTransform(planeNormal: Vector3, planeConstant: number) {
  // Three.js の Plane 定義から、描画用 plane mesh の配置情報へ変換する。
  const position = planeNormal.clone().multiplyScalar(-planeConstant);
  const target = position.clone().sub(planeNormal);
  return { position, target };
}
