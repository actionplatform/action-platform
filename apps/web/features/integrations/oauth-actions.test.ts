import { beforeEach, describe, expect, it, vi } from "vitest";

const v1 = vi.hoisted(() => ({ saveOAuthApp: vi.fn(), clearOAuthApp: vi.fn(), disconnectOAuthHost: vi.fn(), disconnectService: vi.fn() }));
const revalidatePath = vi.hoisted(() => vi.fn());
const requireSession = vi.hoisted(() => vi.fn());

vi.mock("next/cache", () => ({ revalidatePath }));
vi.mock("@/lib/session", () => ({ requireSession }));
vi.mock("@/lib/v1", () => ({ v1 }));

import { disconnectHost, disconnectService, removeOAuthApp, saveOAuthApp } from "./oauth-actions";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("saveOAuthApp", () => {
  const input = { provider: "github" as const, clientId: "id", clientSecret: "secret", baseUrl: "https://github.com" };

  it("sends the credentials in the API's shape and refreshes the layout", async () => {
    v1.saveOAuthApp.mockResolvedValue(undefined);
    expect(await saveOAuthApp(input)).toEqual({ ok: true });
    expect(v1.saveOAuthApp).toHaveBeenCalledWith("github", { client_id: "id", client_secret: "secret", base_url: "https://github.com" });
    expect(revalidatePath).toHaveBeenCalledWith("/", "layout");
  });

  it("refuses a provider the platform does not know before any call", async () => {
    const result = await saveOAuthApp({ ...input, provider: "svn" as never });
    expect(result).toEqual({ ok: false, error: "unknown provider" });
    expect(requireSession).not.toHaveBeenCalled();
    expect(v1.saveOAuthApp).not.toHaveBeenCalled();
  });

  it("returns the API's message and does not refresh on failure", async () => {
    v1.saveOAuthApp.mockRejectedValue(new Error("client secret rejected"));
    expect(await saveOAuthApp(input)).toEqual({ ok: false, error: "client secret rejected" });
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});

describe("removeOAuthApp", () => {
  it("clears the app of a known provider", async () => {
    v1.clearOAuthApp.mockResolvedValue(undefined);
    expect(await removeOAuthApp("gitlab")).toEqual({ ok: true });
    expect(v1.clearOAuthApp).toHaveBeenCalledWith("gitlab");
  });

  it("refuses an unknown provider", async () => {
    expect(await removeOAuthApp("svn" as never)).toEqual({ ok: false, error: "unknown provider" });
    expect(v1.clearOAuthApp).not.toHaveBeenCalled();
  });

  it("returns the failure", async () => {
    v1.clearOAuthApp.mockRejectedValue(new Error("boom"));
    expect(await removeOAuthApp("gitlab")).toEqual({ ok: false, error: "boom" });
  });
});

describe("disconnectHost", () => {
  it("disconnects the login on the provider", async () => {
    v1.disconnectOAuthHost.mockResolvedValue(undefined);
    expect(await disconnectHost("github", "octocat")).toEqual({ ok: true });
    expect(v1.disconnectOAuthHost).toHaveBeenCalledWith("github", "octocat");
    expect(revalidatePath).toHaveBeenCalledWith("/", "layout");
  });

  it("returns the failure", async () => {
    v1.disconnectOAuthHost.mockRejectedValue(new Error("not connected"));
    expect(await disconnectHost("github", "octocat")).toEqual({ ok: false, error: "not connected" });
  });
});

describe("disconnectService", () => {
  it("disconnects a known service", async () => {
    v1.disconnectService.mockResolvedValue(undefined);
    expect(await disconnectService("sentry")).toEqual({ ok: true });
    expect(v1.disconnectService).toHaveBeenCalledWith("sentry");
  });

  it("refuses an unknown service", async () => {
    expect(await disconnectService("svn" as never)).toEqual({ ok: false, error: "unknown provider" });
    expect(v1.disconnectService).not.toHaveBeenCalled();
  });
});
