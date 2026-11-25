import { describe, expect, it } from "vitest";
import { APP_REDIRECTS, APP_SETTINGS_PAGES, appPath } from "./app-routes";

function redirect(path: string): string | null {
  for (const { source, destination } of APP_REDIRECTS) {
    const names: string[] = [];
    const pattern = source.replace(/:(\w+)(\+)?/g, (_, name: string, plus?: string) => { names.push(name); return plus ? "(.+)" : "([^/]+)"; });
    const match = new RegExp(`^${pattern}$`).exec(path);
    if (!match) continue;
    return names.reduce((out, name, i) => out.replace(new RegExp(`:${name}\\+?`), match[i + 1]), destination);
  }
  return null;
}

describe("app redirects", () => {
  it("send the old app tabs to their new homes", () => {
    expect(redirect("/projects/p1/apps/a1/ci")).toBe("/projects/p1/apps/a1/activity?kind=ci_run");
    expect(redirect("/projects/p1/apps/a1/ci/connect")).toBe("/projects/p1/apps/a1/settings/ci");
    expect(redirect("/projects/p1/apps/a1/scopes")).toBe("/projects/p1/apps/a1/settings/scopes");
    expect(redirect("/projects/p1/apps/a1/scopes/new")).toBe("/projects/p1/apps/a1/settings/scopes/new");
    expect(redirect("/projects/p1/apps/a1/scopes/prod")).toBe("/projects/p1/apps/a1/settings/scopes/prod");
    expect(redirect("/projects/p1/apps/a1/configuration")).toBe("/projects/p1/apps/a1/settings/configuration");
    expect(redirect("/projects/p1/apps/a1/activity/new")).toBe("/projects/p1/apps/a1/pull-requests/new");
  });

  it("leave the tabs that stay where they are", () => {
    for (const tab of ["", "/activity", "/releases", "/deployments", "/settings", "/settings/scopes", "/pull-requests/new"]) {
      expect(redirect(`/projects/p1/apps/a1${tab}`)).toBeNull();
    }
  });
});

describe("app settings pages", () => {
  it("are General, Scopes, Configuration and CI under the app", () => {
    expect(APP_SETTINGS_PAGES.map((p) => [p.label, appPath("p1", "a1", p.tab)])).toEqual([
      ["General", "/projects/p1/apps/a1/settings"],
      ["Scopes", "/projects/p1/apps/a1/settings/scopes"],
      ["Configuration", "/projects/p1/apps/a1/settings/configuration"],
      ["CI", "/projects/p1/apps/a1/settings/ci"],
    ]);
  });
});
