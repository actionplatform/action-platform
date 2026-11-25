import { describe, expect, it } from "vitest";
import { latestRunOn, openPullFrom, proposeBlocker } from "./current-branch";

const view = (over: Partial<Parameters<typeof proposeBlocker>[0]> = {}) => ({
  branch: "feature/7-login",
  can: { "app.flow": true } as Parameters<typeof proposeBlocker>[0]["can"],
  repositoryUrl: "https://github.com/acme/app",
  onProtectedBranch: false,
  workingTree: "clean" as const,
  health: { branch: "feature/7-login", problems: [], checked_commits: 2, ok: true },
  ...over,
});

describe("proposeBlocker", () => {
  it("lets a work branch with commits be proposed", () => {
    expect(proposeBlocker(view(), null)).toBeNull();
  });

  it("names what stops the pull request", () => {
    expect(proposeBlocker(view({ can: {} as never }), null)).toBe("Your role cannot open pull requests.");
    expect(proposeBlocker(view({ repositoryUrl: null }), null)).toBe("Push the repository first.");
    expect(proposeBlocker(view({ branch: "develop", onProtectedBranch: true }), null)).toMatch(/^develop is protected/);
    expect(proposeBlocker(view(), { number: 9 })).toBe("Pull request #9 is already open from feature/7-login.");
    expect(proposeBlocker(view({ workingTree: "dirty" }), null)).toBe("Commit or discard the pending changes first.");
    expect(proposeBlocker(view({ health: { branch: "feature/7-login", problems: [], checked_commits: 0, ok: true } }), null)).toBe("feature/7-login has no commits beyond its base yet.");
  });
});

describe("latestRunOn", () => {
  it("takes the first run of the branch in the newest-first list", () => {
    const runs = [{ id: "r3", branch: "main" }, { id: "r2", branch: "feature/7-login" }, { id: "r1", branch: "feature/7-login" }] as Parameters<typeof latestRunOn>[0];
    expect(latestRunOn(runs, "feature/7-login")?.id).toBe("r2");
    expect(latestRunOn(runs, "develop")).toBeNull();
  });
});

describe("openPullFrom", () => {
  it("finds only an open pull request from the branch", () => {
    const pulls = [{ number: 1, head: "feature/7-login", state: "merged" as const, url: "u1" }, { number: 2, head: "feature/7-login", state: "open" as const, url: "u2" }];
    expect(openPullFrom(pulls, "feature/7-login")?.number).toBe(2);
    expect(openPullFrom(pulls.slice(0, 1), "feature/7-login")).toBeNull();
  });
});
