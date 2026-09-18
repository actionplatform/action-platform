import { describe, expect, it } from "vitest";
import { ciState, duration } from "./ci-kinds";

describe("duration", () => {
  it("says it the way a person would", () => {
    expect(duration(null)).toBe("—");
    expect(duration(12_000)).toBe("12s");
    expect(duration(125_000)).toBe("2m 5s");
    expect(duration(3_900_000)).toBe("1h 5m");
  });
});

describe("ciState", () => {
  it("shapes the API answer", () => {
    const state = ciState({
      link: { kind: "jenkins", ci_host_id: "h1", job: "team/app" },
      runs: [{ id: "r1", source: "jenkins", number: 7, status: "success", synced_at: "2026-09-17T10:00:00" }],
      error: null,
    });
    expect(state.link).toEqual({ kind: "jenkins", ciHostId: "h1", job: "team/app" });
    expect(state.runs[0]).toMatchObject({ number: 7, status: "success", branch: null, durationMs: null });
    expect(state.error).toBeNull();
  });
});
