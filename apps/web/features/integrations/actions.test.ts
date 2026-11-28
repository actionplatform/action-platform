import { beforeEach, describe, expect, it, vi } from "vitest";

const v1 = vi.hoisted(() => ({ addHost: vi.fn(), removeHost: vi.fn() }));
const revalidatePath = vi.hoisted(() => vi.fn());

vi.mock("next/cache", () => ({ revalidatePath }));
vi.mock("@/lib/session", () => ({ requireOrg: vi.fn() }));
vi.mock("@/lib/v1", () => ({ v1 }));

import { createHost, deleteHost } from "./actions";

function form(fields: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(fields)) data.set(key, value);
  return data;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("createHost", () => {
  it("refuses a kind the platform has no host for", async () => {
    expect(await createHost(null, form({ kind: "svn", token: "t" }))).toEqual({ error: "unknown host kind" });
    expect(v1.addHost).not.toHaveBeenCalled();
  });

  it("requires a token, even when it is only spaces", async () => {
    expect(await createHost(null, form({ kind: "github", token: "   " }))).toEqual({ error: "token is required" });
    expect(v1.addHost).not.toHaveBeenCalled();
  });

  it("trims every field into the API's shape", async () => {
    v1.addHost.mockResolvedValue(undefined);
    const result = await createHost(null, form({ kind: "gitlab", name: " Work ", baseUrl: " https://gitlab.example.com ", username: " ana ", token: " glpat ", defaultOwner: " acme " }));
    expect(result).toEqual({ error: undefined });
    expect(v1.addHost).toHaveBeenCalledWith({ kind: "gitlab", name: "Work", base_url: "https://gitlab.example.com", username: "ana", token: "glpat", default_owner: "acme" });
    expect(revalidatePath).toHaveBeenCalledWith("/", "layout");
  });

  it("shows the API's message and does not refresh when the host is rejected", async () => {
    v1.addHost.mockRejectedValue(new Error("token cannot list repositories"));
    expect(await createHost(null, form({ kind: "github", token: "t" }))).toEqual({ error: "token cannot list repositories" });
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});

describe("deleteHost", () => {
  it("removes the host and refreshes the layout", async () => {
    v1.removeHost.mockResolvedValue(undefined);
    await deleteHost("h1");
    expect(v1.removeHost).toHaveBeenCalledWith("h1");
    expect(revalidatePath).toHaveBeenCalledWith("/", "layout");
  });
});
