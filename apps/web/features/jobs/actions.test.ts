import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const v1 = vi.hoisted(() => ({ jobLogs: vi.fn() }));

vi.mock("@/lib/session", () => ({ requireOrg: vi.fn() }));
vi.mock("@/lib/v1", () => ({ v1 }));

import { jobLogs } from "./actions";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("jobLogs", () => {
  it("returns the page of lines after the given sequence", async () => {
    const page = { status: "running", next: 3, lines: [{ seq: 2, line: "building" }] };
    v1.jobLogs.mockResolvedValue(page);
    expect(await jobLogs("j1", 2)).toEqual({ ok: true, data: page });
    expect(v1.jobLogs).toHaveBeenCalledWith("j1", 2);
  });

  it("starts from the first line by default", async () => {
    v1.jobLogs.mockResolvedValue({ status: "queued", next: 0, lines: [] });
    await jobLogs("j1");
    expect(v1.jobLogs).toHaveBeenCalledWith("j1", 0);
  });

  it("shows why the log could not be read", async () => {
    v1.jobLogs.mockRejectedValue(new ApiError(404, "no job j1"));
    expect(await jobLogs("j1")).toEqual({ ok: false, error: "no job j1" });
  });
});
