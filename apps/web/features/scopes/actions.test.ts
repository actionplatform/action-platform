import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const v1 = vi.hoisted(() => ({ createScope: vi.fn(), updateScope: vi.fn(), deleteScope: vi.fn() }));
const refreshProject = vi.hoisted(() => vi.fn());

vi.mock("@/lib/revalidate", () => ({ refreshProject }));
vi.mock("@/lib/session", () => ({ requireOrg: vi.fn() }));
vi.mock("@/lib/v1", () => ({ v1 }));

import { createScope, deleteScope, updateScope } from "./actions";

const scopes = { items: [], kinds: ["aws"], criticalities: ["low"] };
const body = { name: "prod", kind: "aws", criticality: "high" };

beforeEach(() => {
  vi.clearAllMocks();
});

describe("createScope", () => {
  it("returns the scopes and refreshes the project", async () => {
    v1.createScope.mockResolvedValue(scopes);
    expect(await createScope("p1", "a1", body)).toEqual({ ok: true, data: scopes });
    expect(v1.createScope).toHaveBeenCalledWith("p1", "a1", body);
    expect(refreshProject).toHaveBeenCalledWith("p1");
  });

  it("shows a refusal from the platform", async () => {
    v1.createScope.mockRejectedValue(new ApiError(409, "scope prod already exists"));
    expect(await createScope("p1", "a1", body)).toEqual({ ok: false, error: "scope prod already exists" });
    expect(refreshProject).not.toHaveBeenCalled();
  });
});

describe("updateScope", () => {
  it("targets the scope by name", async () => {
    v1.updateScope.mockResolvedValue(scopes);
    expect(await updateScope("p1", "a1", "prod", body)).toEqual({ ok: true, data: scopes });
    expect(v1.updateScope).toHaveBeenCalledWith("p1", "a1", "prod", body);
  });

  it("hides a server failure behind the generic message", async () => {
    v1.updateScope.mockRejectedValue(new ApiError(500, "traceback"));
    expect(await updateScope("p1", "a1", "prod", body)).toEqual({ ok: false, error: "Something went wrong. Try again in a moment." });
  });
});

describe("deleteScope", () => {
  it("deletes by name and refreshes the project", async () => {
    v1.deleteScope.mockResolvedValue(undefined);
    expect(await deleteScope("p1", "a1", "prod")).toEqual({ ok: true, data: null });
    expect(v1.deleteScope).toHaveBeenCalledWith("p1", "a1", "prod");
    expect(refreshProject).toHaveBeenCalledWith("p1");
  });

  it("shows why a scope could not be deleted", async () => {
    v1.deleteScope.mockRejectedValue(new ApiError(404, "no scope prod"));
    expect(await deleteScope("p1", "a1", "prod")).toEqual({ ok: false, error: "no scope prod" });
  });
});
