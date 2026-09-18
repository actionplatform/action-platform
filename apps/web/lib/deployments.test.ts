import { describe, expect, it } from "vitest";
import { type Deployment, type Target, liveOf } from "./deployments-kinds";

const t: Target = { name: "lambda", kind: "aws/lambda", runBy: "platform", stages: ["dev", "prod"], workflow: null, job: null };
const row = (o: Partial<Deployment>): Deployment => ({ id: "x", target: "lambda", kind: "aws/lambda", stage: null, version: "1.0.0", sha: null, status: "success", executor: "platform", jobId: null, ciRunId: null, url: null, actor: null, error: null, startedAt: null, finishedAt: null, verifiedAt: null, syncedAt: "2026-09-17T00:00:00", ...o });

describe("liveOf", () => {
  it("names the last good version per stage, newest first wins", () => {
    const rows = [row({ stage: "prod", version: "1.4.0", status: "failure" }), row({ stage: "prod", version: "1.3.0", status: "verified" }), row({ stage: "dev", version: "1.4.0" })];
    expect(liveOf(t, rows)).toEqual([
      { stage: "dev", version: "1.4.0", status: "success", at: null },
      { stage: "prod", version: "1.3.0", status: "verified", at: null },
    ]);
  });

  it("a target without stages has one line", () => {
    const pypi: Target = { ...t, name: "pypi", kind: "pypi", stages: [] };
    expect(liveOf(pypi, [row({ target: "pypi", version: "2.0.0", status: "verified" })])).toEqual([{ stage: null, version: "2.0.0", status: "verified", at: null }]);
    expect(liveOf(pypi, [])[0].version).toBe("—");
  });
});
