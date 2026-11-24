import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SetupStatus } from "@/lib/setup";

const deps = vi.hoisted(() => ({
  setupStatus: vi.fn(),
  getSession: vi.fn(),
  signUp: vi.fn(),
  redirect: vi.fn((to: string) => {
    throw new Error(`redirect:${to}`);
  }),
}));

vi.mock("next/navigation", () => ({ redirect: deps.redirect }));
vi.mock("next/headers", () => ({ headers: async () => new Headers({ host: "ap.example.com" }) }));
vi.mock("@/lib/setup", () => ({ setupStatus: deps.setupStatus }));
vi.mock("@/lib/session", () => ({ getSession: deps.getSession }));
vi.mock("@/lib/oauth", () => ({ oauthApps: vi.fn() }));
vi.mock("@/lib/auth", () => ({ sessionCookie: vi.fn() }));
vi.mock("@/lib/auth-actions", () => ({ signUp: deps.signUp }));
vi.mock("@/lib/auth-api", () => ({ authApi: {} }));
vi.mock("@/lib/v1", () => ({ v1: {} }));

import { createAdmin } from "./actions";
import SetupPage from "./page";

const base: SetupStatus = { configured: true, dbOk: true, hasUser: false, hasOrg: false, complete: false, open: true, passwordRecovery: false, google: false };
const unclaimed = base;
const claimed: SetupStatus = { ...base, hasUser: true, hasOrg: true, complete: true, open: false };
const admin = { setupToken: "ABCD-EFGH-IJKL-MNOP", name: "Ana", email: "ana@example.com", password: "password1" };

function open(search: Record<string, string> = {}) {
  return SetupPage({ searchParams: Promise.resolve(search) });
}

beforeEach(() => {
  vi.clearAllMocks();
  deps.signUp.mockResolvedValue({ ok: true, data: null });
});

describe("/setup", () => {
  it("renders the wizard while nobody has signed up", async () => {
    deps.setupStatus.mockResolvedValue(unclaimed);
    await expect(open()).resolves.toBeTruthy();
    expect(deps.redirect).not.toHaveBeenCalled();
  });

  it("sends a visitor to /login once an account exists", async () => {
    deps.setupStatus.mockResolvedValue(claimed);
    deps.getSession.mockResolvedValue(null);
    await expect(open()).rejects.toThrow("redirect:/login");
  });

  it("sends a visitor to /login when the account exists but no organization yet", async () => {
    deps.setupStatus.mockResolvedValue({ ...claimed, hasOrg: false, complete: false });
    deps.getSession.mockResolvedValue(null);
    await expect(open()).rejects.toThrow("redirect:/login");
  });

  it("sends the signed-in owner of a finished instance to /projects", async () => {
    deps.setupStatus.mockResolvedValue(claimed);
    deps.getSession.mockResolvedValue({ user: { id: "u1" } });
    await expect(open()).rejects.toThrow("redirect:/projects");
  });
});

describe("createAdmin", () => {
  it("refuses without the setup token", async () => {
    deps.setupStatus.mockResolvedValue(unclaimed);
    expect(await createAdmin({ ...admin, setupToken: "  " })).toEqual({ ok: false, error: "enter the setup token" });
    expect(deps.signUp).not.toHaveBeenCalled();
  });

  it("passes the token to the API and reports its refusal", async () => {
    deps.setupStatus.mockResolvedValue(unclaimed);
    deps.signUp.mockResolvedValue({ ok: false, error: "the first account needs the setup token" });

    expect(await createAdmin({ ...admin, setupToken: " WRONG-TOKEN " })).toEqual({ ok: false, error: "the first account needs the setup token" });
    expect(deps.signUp).toHaveBeenCalledWith("Ana", "ana@example.com", "password1", null, "WRONG-TOKEN");
  });

  it("creates the first account with the right token", async () => {
    deps.setupStatus.mockResolvedValue(unclaimed);
    expect(await createAdmin(admin)).toEqual({ ok: true });
    expect(deps.signUp).toHaveBeenCalledWith("Ana", "ana@example.com", "password1", null, admin.setupToken);
  });

  it("refuses a second setup once an account exists", async () => {
    deps.setupStatus.mockResolvedValue(claimed);
    expect(await createAdmin(admin)).toEqual({ ok: false, error: "an account already exists — sign in instead" });
    expect(deps.signUp).not.toHaveBeenCalled();
  });
});
