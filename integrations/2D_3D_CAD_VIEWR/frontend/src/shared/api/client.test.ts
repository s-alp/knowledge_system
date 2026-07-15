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
