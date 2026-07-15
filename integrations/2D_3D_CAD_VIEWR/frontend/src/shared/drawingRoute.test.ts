import { describe, expect, it } from "vitest";

import { resolveDrawingIdFromCandidate, resolveDrawingIdFromLocation } from "./drawingRoute";

describe("resolveDrawingIdFromLocation", () => {
  it("extracts drawingId from pathname", () => {
    expect(
      resolveDrawingIdFromLocation(
        "/web/drawing/35463219-5fe5-49a0-ae7f-ed25c5661be9",
        "",
      ),
    ).toBe("35463219-5fe5-49a0-ae7f-ed25c5661be9");
  });

  it("falls back to drawingId query", () => {
    expect(resolveDrawingIdFromLocation("/", "?drawingId=35463219-5fe5-49a0-ae7f-ed25c5661be9")).toBe(
      "35463219-5fe5-49a0-ae7f-ed25c5661be9",
    );
  });

  it("returns null for invalid identifiers", () => {
    expect(resolveDrawingIdFromLocation("/web/drawing/not-a-uuid", "")).toBeNull();
  });

  it("extracts drawingId from a full URL candidate", () => {
    expect(
      resolveDrawingIdFromCandidate("http://localhost:5173/drawing/35463219-5fe5-49a0-ae7f-ed25c5661be9"),
    ).toBe("35463219-5fe5-49a0-ae7f-ed25c5661be9");
  });

  it("extracts drawingId from a direct UUID candidate", () => {
    expect(resolveDrawingIdFromCandidate("35463219-5fe5-49a0-ae7f-ed25c5661be9")).toBe(
      "35463219-5fe5-49a0-ae7f-ed25c5661be9",
    );
  });
});
