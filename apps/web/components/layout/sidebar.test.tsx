import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppScopeMarker, ScopeProvider } from "./scope";
import { Sidebar } from "./sidebar";

const nav = vi.hoisted(() => ({ pathname: "/projects/p1/apps/a1" }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }), usePathname: () => nav.pathname }));
vi.mock("@/app/(app)/actions", () => ({ switchOrganization: vi.fn() }));
vi.mock("@/lib/auth-actions", () => ({ signOut: vi.fn() }));

const org = { id: "o1", name: "Acme", slug: "acme" };

function renderApp(pathname: string) {
  nav.pathname = pathname;
  render(
    <ScopeProvider>
      <AppScopeMarker projectId="p1" projectName="Shop" appId="a1" appName="api" />
      <Sidebar versions={{ web: "1", api: "1", lib: "1" }} user={{ name: "Ana", email: "ana@example.com" }} org={org} orgs={[org]} />
    </ScopeProvider>,
  );
  return within(screen.getAllByRole("navigation", { name: "api" })[0]);
}

describe("Sidebar inside an app", () => {
  afterEach(cleanup);

  it("lists Overview, Releases, Scopes, Deployments, Pipelines, Activity and Settings", () => {
    const menu = renderApp("/projects/p1/apps/a1");
    const links = menu.getAllByRole("link").slice(1).map((a) => [a.textContent, a.getAttribute("href")]);
    expect(links).toEqual([
      ["Overview", "/projects/p1/apps/a1"],
      ["Releases", "/projects/p1/apps/a1/releases"],
      ["Scopes", "/projects/p1/apps/a1/scopes"],
      ["Deployments", "/projects/p1/apps/a1/deployments"],
      ["Pipelines", "/projects/p1/apps/a1/pipelines"],
      ["Activity", "/projects/p1/apps/a1/activity"],
      ["Settings", "/projects/p1/apps/a1/settings"],
    ]);
    expect(menu.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });

  it("keeps Scopes a tab of its own", () => {
    for (const [path, name] of [["/projects/p1/apps/a1/scopes/new", "Scopes"]]) {
      cleanup();
      const menu = renderApp(path);
      expect(menu.getByRole("link", { name })).toHaveAttribute("aria-current", "page");
    }
  });

  it("has no sub-navigation under Settings", () => {
    const menu = renderApp("/projects/p1/apps/a1/settings");
    expect(menu.getByRole("link", { name: "Settings" })).toHaveAttribute("aria-current", "page");
    expect(menu.getAllByRole("link")).toHaveLength(8);
  });
});
