import { describe, expect, it } from "vitest";
import { summarize } from "./run-alert";

describe("summarize", () => {
  it("names the missing build tool", () => {
    expect(summarize("sam build failed: Path resolution for runtime: provided of binary: make was not successful")).toBe("Build dependency “make” could not be resolved.");
  });

  it("reads the proxy's status", () => {
    expect(summarize("proxy POST /apps/a/b/c/credentials: 403 org:x may not deploy a/b/c")).toBe("The deploy proxy answered 403: org:x may not deploy a/b/c.");
  });

  it("trims a long first line", () => {
    expect(summarize("x".repeat(200)).length).toBeLessThanOrEqual(161);
  });
});
