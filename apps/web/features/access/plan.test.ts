import { describe, expect, it } from "vitest";
import type { AccessChange } from "@/lib/v1";
import { canApply, describeChange, groupDrift, needsConnection, summarizePlan, summaryText } from "./plan";

const change = (over: Partial<AccessChange> = {}): AccessChange => ({ action: "add", service: "github", account: "ada", resource: "repo/api", level: "push", status: "planned", ...over });

describe("summarizePlan", () => {
  it("counts by status and action", () => {
    const s = summarizePlan({ changes: [change(), change({ action: "remove" }), change({ action: "change", status: "refused" }), change({ status: "failed" })] });
    expect(s).toMatchObject({ total: 4, planned: 2, refused: 1, failed: 1, add: 2, remove: 1, change: 1 });
  });

  it("says when nothing changes", () => {
    expect(summaryText(summarizePlan({ changes: [] }))).toBe("No changes");
  });

  it("lists the non-zero parts", () => {
    expect(summaryText(summarizePlan({ changes: [change(), change({ action: "remove", status: "refused" })] }))).toBe("1 to add, 1 to remove, 1 refused");
  });
});

describe("canApply", () => {
  it("needs a dry run with something planned", () => {
    expect(canApply({ dry_run: true, bootstrap: false, changes: [change()] })).toBe(true);
    expect(canApply({ dry_run: true, bootstrap: false, changes: [change({ status: "refused" })] })).toBe(false);
    expect(canApply({ dry_run: false, bootstrap: false, changes: [change()] })).toBe(false);
  });

  it("allows applying an import with no changes", () => {
    expect(canApply({ dry_run: true, bootstrap: true, changes: [] })).toBe(true);
  });
});

describe("groupDrift", () => {
  it("groups by service in name order", () => {
    const groups = groupDrift([change({ service: "sentry" }), change({ service: "github" }), change({ service: "github", account: "bob" })]);
    expect(groups.map((g) => [g.service, g.changes.length])).toEqual([["github", 2], ["sentry", 1]]);
  });
});

describe("needsConnection", () => {
  it("matches errors that ask to connect", () => {
    expect(needsConnection("Connect the GitHub account under Settings")).toBe(true);
    expect(needsConnection("token lacks scope")).toBe(false);
    expect(needsConnection(null)).toBe(false);
  });
});

describe("describeChange", () => {
  it("reads each action", () => {
    expect(describeChange(change())).toBe("Add ada on repo/api at push");
    expect(describeChange(change({ action: "remove" }))).toBe("Remove ada on repo/api (push)");
    expect(describeChange(change({ action: "change", previous: "pull" }))).toBe("Change ada on repo/api from pull to push");
  });
});
