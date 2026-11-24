import { describe, expect, it } from "vitest";
import { tokenRequest } from "./new-token";

describe("tokenRequest", () => {
  it("keeps the reach under one organization", () => {
    expect(tokenRequest({ name: " ci ", scope: ["write", "read"], organizationId: "o1", projectId: "p1", appId: "a1" })).toEqual({ name: "ci", scope: "read write", organization_id: "o1", project_id: "p1", app_id: "a1" });
  });

  it("drops project and app when the token reaches every organization", () => {
    expect(tokenRequest({ name: "bot", scope: ["read"], organizationId: "*", projectId: "p1", appId: "a1" })).toEqual({ name: "bot", scope: "read", organization_id: "*", project_id: null, app_id: null });
  });

  it("drops an app without a project and falls back to read", () => {
    expect(tokenRequest({ name: "bot", scope: [], organizationId: "o1", projectId: null, appId: "a1" })).toEqual({ name: "bot", scope: "read", organization_id: "o1", project_id: null, app_id: null });
  });
});
