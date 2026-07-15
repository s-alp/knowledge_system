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
