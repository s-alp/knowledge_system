import { describe, expect, it } from "vitest";

import { resolveDrawingIdFromCandidate, resolveDrawingIdFromLocation, resolveViewerModeFromSearch } from "./drawingRoute";

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

describe("resolveViewerModeFromSearch", () => {
  it("extracts 2D or 3D mode from query parameters", () => {
    expect(resolveViewerModeFromSearch("?mode=2d")).toBe("2d");
    expect(resolveViewerModeFromSearch("?mode=3D")).toBe("3d");
  });

  it("returns null when the mode is absent or unsupported", () => {
    expect(resolveViewerModeFromSearch("")).toBeNull();
    expect(resolveViewerModeFromSearch("?mode=pdf")).toBeNull();
  });
});
