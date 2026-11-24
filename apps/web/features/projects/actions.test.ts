import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ apps: { sync: vi.fn() } }));
const v1 = vi.hoisted(() => ({ job: vi.fn(), syncImports: vi.fn() }));

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
vi.mock("@/lib/revalidate", () => ({ refreshProject: vi.fn() }));
vi.mock("@/lib/session", () => ({ requireOrg: vi.fn() }));
vi.mock("@/lib/v1", () => ({ v1 }));
vi.mock("@/lib/api", async (original) => ({ ...(await original<typeof import("@/lib/api")>()), api }));

import { syncApp } from "./actions";

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
  api.apps.sync.mockResolvedValue({ job: "j1", status: "queued", poll: "/api/v1/jobs/j1" });
  v1.syncImports.mockResolvedValue({ releases: [] });
});

afterEach(() => {
  vi.useRealTimers();
});

async function sync() {
  const pending = syncApp("p1", "a1", "r1");
  await vi.runAllTimersAsync();
  return pending;
}

describe("syncApp", () => {
  it("imports releases once the sync job is done", async () => {
    v1.job.mockResolvedValueOnce({ status: "running" }).mockResolvedValueOnce({ status: "done" });
    expect(await sync()).toEqual({ ok: true });
    expect(v1.syncImports).toHaveBeenCalledWith("p1", "a1");
  });

  it("shows the job's error when the sync failed", async () => {
    v1.job.mockResolvedValue({ status: "failed", error: "fetch refused" });
    expect(await sync()).toEqual({ ok: false, error: "fetch refused" });
    expect(v1.syncImports).not.toHaveBeenCalled();
  });

  it("does not claim success while the job still runs", async () => {
    v1.job.mockResolvedValue({ status: "running" });
    const result = await sync();
    expect(result.ok).toBe(false);
    expect(result).toEqual({ ok: false, error: "sync still running (job j1): reload in a moment" });
    expect(v1.syncImports).not.toHaveBeenCalled();
  });
});
