import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  githubInstall: vi.fn(),
  getSession: vi.fn(),
}));

vi.mock("@/lib/v1", () => ({ v1: { githubInstall: mocks.githubInstall } }));
vi.mock("@/lib/session", () => ({ getSession: mocks.getSession }));
vi.mock("next/navigation", () => ({
  redirect: (to: string) => {
    throw Object.assign(new Error("redirect"), { to });
  },
}));

import { ApiError } from "@/lib/api";
import { GET } from "./route";

const request = (query = "return=/connect/git") =>
  new Request(`https://ap.example.com/api/oauth/github/install?${query}`);

async function redirected(req: Request): Promise<string> {
  try {
    await GET(req);
  } catch (e) {
    return (e as { to: string }).to;
  }
  throw new Error("no redirect");
}

beforeEach(() => {
  mocks.getSession.mockResolvedValue({ user: "u" });
  mocks.githubInstall.mockReset();
});

describe("github install route", () => {
  it("sends the browser to the install page", async () => {
    mocks.githubInstall.mockResolvedValue({ url: "https://github.com/apps/ap/installations/select_target?state=s" });
    expect(await redirected(request())).toBe("https://github.com/apps/ap/installations/select_target?state=s");
  });

  it("creates the app again when it was deleted on GitHub", async () => {
    mocks.githubInstall.mockRejectedValue(new ApiError(409, "the GitHub App was deleted on GitHub; create it again"));
    expect(await redirected(request("return=/connect/git"))).toBe("/api/oauth/github/manifest?return=%2Fconnect%2Fgit");
  });

  it("answers other failures as JSON", async () => {
    mocks.githubInstall.mockRejectedValue(new ApiError(400, "GitHub App is not configured"));
    const res = await GET(request());
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ detail: "GitHub App is not configured" });
  });
});
