import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({ apps: { writeManifest: vi.fn(), exportManifest: vi.fn(), setCloud: vi.fn(), addService: vi.fn(), commit: vi.fn(), discard: vi.fn() } }));
const refreshProject = vi.hoisted(() => vi.fn());

vi.mock("@/lib/revalidate", () => ({ refreshProject }));
vi.mock("@/lib/session", () => ({ requireOrg: vi.fn() }));
vi.mock("@/lib/api", async (original) => ({ ...(await original<typeof import("@/lib/api")>()), api }));

import { addService, commitChanges, discardChanges, exportManifest, saveManifest, setCloudTarget } from "./actions";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("saveManifest", () => {
  it("writes the manifest and refreshes the project", async () => {
    api.apps.writeManifest.mockResolvedValue({ content: "[project]", mirrored: true });
    expect(await saveManifest("p1", "r1", "[project]")).toEqual({ ok: true, data: { content: "[project]", mirrored: true } });
    expect(api.apps.writeManifest).toHaveBeenCalledWith("r1", "[project]");
    expect(refreshProject).toHaveBeenCalledWith("p1");
  });

  it("shows the platform's refusal and does not refresh", async () => {
    api.apps.writeManifest.mockRejectedValue(new ApiError(422, "manifest is not valid TOML"));
    expect(await saveManifest("p1", "r1", "{")).toEqual({ ok: false, error: "manifest is not valid TOML" });
    expect(refreshProject).not.toHaveBeenCalled();
  });
});

describe("exportManifest", () => {
  it("returns the manifest of the clone", async () => {
    api.apps.exportManifest.mockResolvedValue({ content: "x" });
    expect(await exportManifest("p1", "r1")).toEqual({ ok: true, data: { content: "x" } });
  });
});

describe("setCloudTarget", () => {
  it("sets the target with no source by default", async () => {
    api.apps.setCloud.mockResolvedValue({ target: "aws" });
    expect(await setCloudTarget("p1", "r1", "aws")).toEqual({ ok: true, data: { target: "aws" } });
    expect(api.apps.setCloud).toHaveBeenCalledWith("r1", "aws", null);
  });
});

describe("addService", () => {
  it("adds the service with its provider and source", async () => {
    api.apps.addService.mockResolvedValue({ name: "db" });
    expect(await addService("p1", "r1", "db", "postgres", "acme")).toEqual({ ok: true, data: { name: "db" } });
    expect(api.apps.addService).toHaveBeenCalledWith("r1", "db", "postgres", "acme");
  });
});

describe("commitChanges", () => {
  const input = { message: "feat: x", push: true, pullRequest: true, branch: { kind: "feature", code: "12", slug: "" } };

  it("sends the branch with an empty slug as null", async () => {
    api.apps.commit.mockResolvedValue({ sha: "abc", branch: "feature/12", pushed: true });
    await commitChanges("p1", "a1", "r1", input);
    expect(api.apps.commit).toHaveBeenCalledWith("r1", { message: "feat: x", push: true, branch: { kind: "feature", code: "12", slug: null }, pull_request: true });
  });

  it("commits on the current branch when none is given", async () => {
    api.apps.commit.mockResolvedValue({ sha: "abc", branch: "main", pushed: false });
    await commitChanges("p1", "a1", "r1", { ...input, branch: null });
    expect(api.apps.commit).toHaveBeenCalledWith("r1", expect.objectContaining({ branch: null }));
  });

  it("shows a protected-branch refusal", async () => {
    api.apps.commit.mockRejectedValue(new ApiError(409, "main is protected"));
    expect(await commitChanges("p1", "a1", "r1", { ...input, branch: null })).toEqual({ ok: false, error: "main is protected" });
  });
});

describe("discardChanges", () => {
  it("reports the files that were dropped", async () => {
    api.apps.discard.mockResolvedValue({ files: ["platform.toml"], clean: true });
    expect(await discardChanges("p1", "r1")).toEqual({ ok: true, data: { files: ["platform.toml"], clean: true } });
    expect(refreshProject).toHaveBeenCalledWith("p1");
  });
});
