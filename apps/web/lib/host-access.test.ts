import { describe, expect, it, vi } from "vitest";

const v1 = vi.hoisted(() => ({ hostAccess: vi.fn() }));

vi.mock("./v1", () => ({ v1 }));

import { hostAccess } from "./host-access";

describe("hostAccess", () => {
  it("passes the access report through", async () => {
    const report = { ok: true, kind: "github", login: "octocat", installations: [], installUrl: null, problems: [] };
    v1.hostAccess.mockResolvedValue(report);
    expect(await hostAccess("org1", "h1")).toEqual(report);
    expect(v1.hostAccess).toHaveBeenCalledWith("h1");
  });

  it("turns a failure into a reconnect hint", async () => {
    v1.hostAccess.mockRejectedValue(new Error("401 bad credentials"));
    expect(await hostAccess("org1", "h1")).toEqual({ ok: false, error: "401 bad credentials; reconnect the host" });
  });
});
