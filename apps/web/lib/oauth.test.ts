import { beforeEach, describe, expect, it, vi } from "vitest";

const v1 = vi.hoisted(() => ({ oauthApps: vi.fn() }));

vi.mock("./v1", () => ({ v1 }));

import { appFor, isConfigured, oauthApps } from "./oauth";

beforeEach(() => {
  v1.oauthApps.mockResolvedValue([
    { provider: "github", configured: true, client_id: "gh" },
    { provider: "gitlab", configured: false },
  ]);
});

describe("oauthApps", () => {
  it("indexes the apps by provider", async () => {
    const apps = await oauthApps();
    expect(Object.keys(apps)).toEqual(["github", "gitlab"]);
    expect(apps.github).toMatchObject({ client_id: "gh" });
  });
});

describe("appFor", () => {
  it("returns the app of a configured provider", async () => {
    expect(await appFor("github")).toMatchObject({ provider: "github" });
  });

  it("returns null when the provider is registered but not configured", async () => {
    expect(await appFor("gitlab")).toBeNull();
  });

  it("returns null for a provider with no row", async () => {
    expect(await appFor("bitbucket")).toBeNull();
  });
});

describe("isConfigured", () => {
  it("is true only for a configured provider", async () => {
    expect(await isConfigured("github")).toBe(true);
    expect(await isConfigured("gitlab")).toBe(false);
    expect(await isConfigured("sentry")).toBe(false);
  });
});
