import { describe, expect, it } from "vitest";
import { config } from "./middleware";

function matches(pattern: string, path: string): boolean {
  const source = pattern.replace(/:path\*$/, "(?:.*)");
  return new RegExp(`^${source}$`).test(path);
}

describe("middleware matcher", () => {
  it("proxies API paths whose segments carry a dot", () => {
    const path = "/api/v1/projects/p/apps/a/releases/v1.2.3/readiness";
    expect(config.matcher.some((m) => matches(m, path))).toBe(true);
  });

  it("proxies auth paths with a dot", () => {
    expect(config.matcher.some((m) => matches(m, "/api/auth/device/v1.0"))).toBe(true);
  });

  it("leaves static files alone", () => {
    expect(config.matcher.some((m) => matches(m, "/favicon.ico"))).toBe(false);
  });
});
