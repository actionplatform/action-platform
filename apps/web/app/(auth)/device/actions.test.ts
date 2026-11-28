import { beforeEach, describe, expect, it, vi } from "vitest";

const tokens = vi.hoisted(() => ({ approveDevice: vi.fn(), denyDevice: vi.fn(), deviceRequest: vi.fn() }));

vi.mock("@/lib/session", () => ({ requireSession: vi.fn(), requireOrg: vi.fn() }));
vi.mock("@/lib/api-tokens", () => tokens);
vi.mock("@/lib/v1", () => ({ v1: {} }));
vi.mock("@/lib/projects", () => ({ appsOf: vi.fn(), projectsOf: vi.fn() }));

import { approveDeviceRequest } from "./actions";

beforeEach(() => {
  vi.clearAllMocks();
  tokens.approveDevice.mockResolvedValue(undefined);
});

describe("approveDeviceRequest", () => {
  it("sends * for all organizations and drops project and app", async () => {
    const result = await approveDeviceRequest(" abcd1234 ", { scope: ["read", "write"], organizationId: "*", projectId: "p1", appId: "a1" });
    expect(result).toEqual({ ok: true, data: null });
    expect(tokens.approveDevice).toHaveBeenCalledWith("ABCD1234", { scope: ["read", "write"], organizationId: "*", projectId: null, appId: null });
  });

  it("keeps the chosen organization, project and app", async () => {
    await approveDeviceRequest("ABCD1234", { scope: ["read"], organizationId: "o1", projectId: "p1", appId: "a1" });
    expect(tokens.approveDevice).toHaveBeenCalledWith("ABCD1234", { scope: ["read"], organizationId: "o1", projectId: "p1", appId: "a1" });
  });
});
