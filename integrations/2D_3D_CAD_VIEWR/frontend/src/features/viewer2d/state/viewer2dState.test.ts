// このファイルは、viewer2dStateの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
import { describe, expect, it } from "vitest";

import { initialTwoDViewportState, twoDViewportReducer } from "./viewer2dState";

function toStagePoint(
  scale: number,
  rotation: number,
  offsetX: number,
  offsetY: number,
  pageX: number,
  pageY: number,
) {
  const radians = (rotation * Math.PI) / 180;
  const scaledX = pageX * scale;
  const scaledY = pageY * scale;
  return {
    x: offsetX + (scaledX * Math.cos(radians) - scaledY * Math.sin(radians)),
    y: offsetY + (scaledX * Math.sin(radians) + scaledY * Math.cos(radians)),
  };
}

describe("twoDViewportReducer", () => {
  it("rotates right by 90 degrees", () => {
    const next = twoDViewportReducer(initialTwoDViewportState, {
      type: "rotate",
      direction: "right",
    });
    expect(next.rotation).toBe(90);
  });

  it("zooms within bounds", () => {
    const next = twoDViewportReducer(initialTwoDViewportState, {
      type: "zoom",
      delta: 0.5,
    });
    expect(next.scale).toBe(1.5);
  });

  it.each([0, 90, 180, 270])("keeps the anchor point stable during zoomAt at rotation %s", (rotation) => {
    const state = {
      scale: 1,
      rotation,
      offsetX: 120,
      offsetY: -80,
    };
    const stageWidth = 960;
    const stageHeight = 640;
    const pagePoint = { x: 70, y: -30 };
    const anchor = toStagePoint(
      state.scale,
      state.rotation,
      state.offsetX,
      state.offsetY,
      pagePoint.x,
      pagePoint.y,
    );

    const next = twoDViewportReducer(state, {
      type: "zoomAt",
      delta: 0.5,
      anchorX: anchor.x + stageWidth / 2,
      anchorY: anchor.y + stageHeight / 2,
      stageWidth,
      stageHeight,
    });

    const nextAnchor = toStagePoint(
      next.scale,
      next.rotation,
      next.offsetX,
      next.offsetY,
      pagePoint.x,
      pagePoint.y,
    );

    expect(nextAnchor.x).toBeCloseTo(anchor.x, 1);
    expect(nextAnchor.y).toBeCloseTo(anchor.y, 1);
  });
});
