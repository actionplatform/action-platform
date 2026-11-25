import { describe, expect, it } from "vitest";
import { ciState, duration, runOfRelease } from "./ci-kinds";

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
      total: 1,
      page: 1,
      per: 10,
    });
    expect(state.link).toEqual({ kind: "jenkins", ciHostId: "h1", job: "team/app" });
    expect(state.runs[0]).toMatchObject({ number: 7, status: "success", branch: null, durationMs: null });
    expect(state.error).toBeNull();
  });
});

describe("runOfRelease", () => {
  const run = (id: string, branch: string | null, sha: string | null) => ({ id, source: "github_actions", number: Number(id.slice(1)), status: "success" as const, name: null, url: null, branch, sha, trigger: null, startedAt: null, durationMs: null, syncedAt: "2026-11-25T10:00:00" });

  it("takes the newest run on the tag, the version or the release commit", () => {
    const runs = [run("r3", "main", "abc"), run("r2", "v1.2.0", null), run("r1", "1.1.0", null)];
    expect(runOfRelease(runs, { tag: "v1.2.0", version: "1.2.0", sha: null })?.id).toBe("r2");
    expect(runOfRelease(runs, { tag: "v1.1.0", version: "1.1.0", sha: null })?.id).toBe("r1");
    expect(runOfRelease(runs, { tag: "v1.3.0", version: "1.3.0", sha: "abc" })?.id).toBe("r3");
  });

  it("finds nothing rather than guessing", () => {
    expect(runOfRelease([run("r1", "main", "abc")], { tag: "v2.0.0", version: "2.0.0", sha: null })).toBeNull();
    expect(runOfRelease([run("r1", "main", null)], { tag: "v2.0.0", version: "", sha: null })).toBeNull();
  });
});
