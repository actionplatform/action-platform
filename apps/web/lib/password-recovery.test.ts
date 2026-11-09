import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";

const api = vi.hoisted(() => ({
  status: vi.fn(),
  forgotPassword: vi.fn(),
  resetPassword: vi.fn(),
}));

vi.mock("./auth-api", async (original) => ({
  ...(await original<typeof import("./auth-api")>()),
  authApi: api,
}));

vi.mock("./auth", () => ({
  requestClient: async () => ({ ip: "203.0.113.7", userAgent: "vitest" }),
  setSessionCookie: vi.fn(),
  clearSessionCookie: vi.fn(),
  sessionCookie: vi.fn(),
}));

import { requestPasswordReset, resetPassword } from "./auth-actions";
import { setupStatus } from "./setup";

beforeEach(() => vi.clearAllMocks());

describe("setupStatus", () => {
  it("says whether the API can send a reset link", async () => {
    api.status.mockResolvedValue({ configured: true, users: 1, organizations: 1, password_recovery: true });
    expect((await setupStatus()).passwordRecovery).toBe(true);

    api.status.mockResolvedValue({ configured: true, users: 1, organizations: 1, password_recovery: false });
    expect((await setupStatus()).passwordRecovery).toBe(false);
  });
});

describe("requestPasswordReset", () => {
  it("forwards the email with the client address", async () => {
    api.forgotPassword.mockResolvedValue(null);
    expect(await requestPasswordReset("ana@example.com")).toEqual({ ok: true, data: null });
    expect(api.forgotPassword).toHaveBeenCalledWith("ana@example.com", "203.0.113.7");
  });

  it("names a rate limit and a platform without email", async () => {
    api.forgotPassword.mockRejectedValueOnce(new ApiError(429, "too many"));
    expect(await requestPasswordReset("ana@example.com")).toEqual({ ok: false, error: "too many attempts, wait a minute" });

    api.forgotPassword.mockRejectedValueOnce(new ApiError(503, "no smtp"));
    expect(await requestPasswordReset("ana@example.com")).toEqual({ ok: false, error: "password recovery is not available on this platform" });
  });
});

describe("resetPassword", () => {
  it("sends the token and the new password", async () => {
    api.resetPassword.mockResolvedValue(null);
    expect(await resetPassword("tok", "new-password1")).toEqual({ ok: true, data: null });
    expect(api.resetPassword).toHaveBeenCalledWith({ token: "tok", password: "new-password1" }, "203.0.113.7");
  });

  it("shows what the API refused", async () => {
    api.resetPassword.mockRejectedValueOnce(new ApiError(400, "this link is invalid or has expired"));
    expect(await resetPassword("old", "new-password1")).toEqual({ ok: false, error: "this link is invalid or has expired" });
  });
});
