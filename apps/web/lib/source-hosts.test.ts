import { beforeEach, describe, expect, it, vi } from "vitest";

const v1 = vi.hoisted(() => ({ hosts: vi.fn() }));

vi.mock("./v1", () => ({ v1 }));

import { hostById, hostsOf } from "./source-hosts";

const rows = [
  { id: "h1", kind: "github", name: "GitHub", base_url: null, username: null, default_owner: "acme", auth_kind: "oauth", login: "octocat", created_at: "2026-01-02T03:04:05Z" },
  { id: "h2", kind: "gitlab", name: "Self-hosted", base_url: "https://git.example.com", username: "ana", default_owner: null, auth_kind: "token", created_at: "2026-02-01T00:00:00Z" },
];

beforeEach(() => {
  v1.hosts.mockResolvedValue(rows);
});

describe("hostsOf", () => {
  it("maps rows to hosts of the organization", async () => {
    const [github, gitlab] = await hostsOf("org1");
    expect(github).toMatchObject({ id: "h1", organizationId: "org1", kind: "github", baseUrl: null, defaultOwner: "acme", authKind: "oauth", login: "octocat" });
    expect(gitlab).toMatchObject({ baseUrl: "https://git.example.com", username: "ana", defaultOwner: null, login: null });
  });

  it("parses the creation date", async () => {
    const [github] = await hostsOf("org1");
    expect(github.createdAt.toISOString()).toBe("2026-01-02T03:04:05.000Z");
  });
});

describe("hostById", () => {
  it("finds a host", async () => {
    expect((await hostById("org1", "h2"))?.name).toBe("Self-hosted");
  });

  it("answers null for a host the organization does not have", async () => {
    expect(await hostById("org1", "nope")).toBeNull();
  });
});
