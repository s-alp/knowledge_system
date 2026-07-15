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
