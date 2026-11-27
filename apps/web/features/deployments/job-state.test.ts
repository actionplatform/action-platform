import { describe, expect, it } from "vitest";
import type { JobRow } from "@/lib/v1";
import { canRedeploy, deploymentHref, releaseTag, statusOf, versionOf } from "./job-state";

const job = (over: Partial<JobRow>): JobRow => ({ id: "j1", kind: "deploy", status: "done", attempts: 1, created_at: "2026-11-27T03:00:00Z", updated_at: "2026-11-27T03:01:00Z", ...over }) as JobRow;

describe("job state", () => {
  it("reads a failed target as a failed deployment", () => {
    expect(statusOf(job({ result: [{ ok: false, target: "dev", version: "1.2.0" }] })).label).toBe("Failed");
    expect(statusOf(job({ result: [{ ok: true, target: "dev", version: "1.2.0" }] })).label).toBe("Successful");
    expect(statusOf(job({ status: "queued", no_worker: true })).label).toBe("No worker running");
  });

  it("offers Redeploy only for a deploy with a version and the permission", () => {
    expect(versionOf(job({ result: [{ ok: true, target: "dev", version: "1.2.0" }] }))).toBe("1.2.0");
    expect(canRedeploy(job({ version: "1.2.0" }), true)).toBe(true);
    expect(canRedeploy(job({ version: "1.2.0" }), false)).toBe(false);
    expect(canRedeploy(job({ kind: "destroy", version: "1.2.0" }), true)).toBe(false);
    expect(canRedeploy(job({}), true)).toBe(false);
  });

  it("links the page and the release", () => {
    expect(deploymentHref("/projects/p/apps/a", "j 1")).toBe("/projects/p/apps/a/deployments/j%201");
    expect(releaseTag("1.2.0")).toBe("v1.2.0");
    expect(releaseTag("v1.2.0")).toBe("v1.2.0");
    expect(releaseTag("api/v1.2.0")).toBe("api/v1.2.0");
  });
});
