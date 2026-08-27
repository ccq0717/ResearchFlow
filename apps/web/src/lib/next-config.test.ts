import { afterEach, describe, expect, it, vi } from "vitest";

const originalDistDir = process.env.NEXT_DIST_DIR;

afterEach(() => {
  if (originalDistDir === undefined) {
    delete process.env.NEXT_DIST_DIR;
  } else {
    process.env.NEXT_DIST_DIR = originalDistDir;
  }
  vi.resetModules();
});

describe("Next.js build directory", () => {
  it("allows E2E runs to use an isolated cache", async () => {
    process.env.NEXT_DIST_DIR = ".next-e2e";
    vi.resetModules();

    const { default: config } = await import("../../next.config");

    expect(config.distDir).toBe(".next-e2e");
  });
});
