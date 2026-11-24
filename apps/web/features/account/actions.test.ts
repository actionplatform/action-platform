import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({ changePassword: vi.fn() }));
const cookie = vi.hoisted(() => vi.fn());

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
vi.mock("@/lib/session", () => ({ requireSession: vi.fn() }));
vi.mock("@/lib/api-tokens", () => ({ issueUserToken: vi.fn(), revokeToken: vi.fn() }));
vi.mock("@/lib/sessions", () => ({ revokeSession: vi.fn() }));
vi.mock("@/lib/auth", () => ({ requestClient: async () => ({ ip: "203.0.113.7", userAgent: "vitest" }), sessionCookie: cookie }));
vi.mock("@/lib/auth-api", async (original) => ({ ...(await original<typeof import("@/lib/auth-api")>()), authApi: api }));

import { changePassword } from "./actions";

beforeEach(() => {
  vi.clearAllMocks();
  cookie.mockResolvedValue("signed-cookie");
});

describe("changePassword", () => {
  it("sends both passwords with the session and the client address", async () => {
    api.changePassword.mockResolvedValue(null);
    expect(await changePassword("old-password1", "new-password1")).toEqual({ ok: true, data: null });
    expect(api.changePassword).toHaveBeenCalledWith({ cookie: "signed-cookie" }, { current_password: "old-password1", new_password: "new-password1" }, "203.0.113.7");
  });

  it("shows a wrong current password", async () => {
    api.changePassword.mockRejectedValueOnce(new ApiError(400, "the current password is wrong"));
    expect(await changePassword("nope", "new-password1")).toEqual({ ok: false, error: "the current password is wrong" });
  });

  it("names a rate limit", async () => {
    api.changePassword.mockRejectedValueOnce(new ApiError(429, "too many"));
    expect(await changePassword("old-password1", "new-password1")).toEqual({ ok: false, error: "too many attempts, wait a minute" });
  });

  it("needs a session cookie", async () => {
    cookie.mockResolvedValue(undefined);
    expect(await changePassword("old-password1", "new-password1")).toEqual({ ok: false, error: "sign in first" });
    expect(api.changePassword).not.toHaveBeenCalled();
  });
});
