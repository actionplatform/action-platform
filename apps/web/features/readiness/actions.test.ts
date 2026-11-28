import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const v1 = vi.hoisted(() => ({ checkReadiness: vi.fn(), readiness: vi.fn() }));
const refreshProject = vi.hoisted(() => vi.fn());

vi.mock("@/lib/revalidate", () => ({ refreshProject }));
vi.mock("@/lib/session", () => ({ requireOrg: vi.fn() }));
vi.mock("@/lib/v1", () => ({ v1 }));

import { checkReadiness, readiness } from "./actions";

const row = { stage: "dev", verdict: "ok", status: "done", checks: [] };

beforeEach(() => {
  vi.clearAllMocks();
});

describe("checkReadiness", () => {
  it("returns the jobs and rows and refreshes the project", async () => {
    v1.checkReadiness.mockResolvedValue({ jobs: ["j1"], readiness: [row], extra: true });
    expect(await checkReadiness("p1", "a1", "v1.0.0", "dev")).toEqual({ ok: true, data: { jobs: ["j1"], readiness: [row] } });
    expect(v1.checkReadiness).toHaveBeenCalledWith("p1", "a1", "v1.0.0", "dev");
    expect(refreshProject).toHaveBeenCalledWith("p1");
  });

  it("checks every stage when none is named", async () => {
    v1.checkReadiness.mockResolvedValue({ jobs: [], readiness: [] });
    await checkReadiness("p1", "a1", "v1.0.0");
    expect(v1.checkReadiness).toHaveBeenCalledWith("p1", "a1", "v1.0.0", null);
  });

  it("shows the platform's refusal", async () => {
    v1.checkReadiness.mockRejectedValue(new ApiError(403, "org:x may not check readiness"));
    expect(await checkReadiness("p1", "a1", "v1.0.0")).toEqual({ ok: false, error: "org:x may not check readiness" });
    expect(refreshProject).not.toHaveBeenCalled();
  });
});

describe("readiness", () => {
  it("returns the rows of a release", async () => {
    v1.readiness.mockResolvedValue([row]);
    expect(await readiness("p1", "a1", "v1.0.0")).toEqual({ ok: true, data: [row] });
  });

  it("hides a server failure behind the generic message", async () => {
    v1.readiness.mockRejectedValue(new ApiError(500, "traceback"));
    expect(await readiness("p1", "a1", "v1.0.0")).toEqual({ ok: false, error: "Something went wrong. Try again in a moment." });
  });
});
