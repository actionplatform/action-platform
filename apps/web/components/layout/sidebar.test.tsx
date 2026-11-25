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

  it("lists Overview, Releases, Deployments, Activity and Settings", () => {
    const menu = renderApp("/projects/p1/apps/a1");
    const links = menu.getAllByRole("link").slice(1).map((a) => [a.textContent, a.getAttribute("href")]);
    expect(links).toEqual([
      ["Overview", "/projects/p1/apps/a1"],
      ["Releases", "/projects/p1/apps/a1/releases"],
      ["Deployments", "/projects/p1/apps/a1/deployments"],
      ["Activity", "/projects/p1/apps/a1/activity"],
      ["Settings", "/projects/p1/apps/a1/settings"],
    ]);
    expect(menu.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });

  it("opens the settings pages under Settings", () => {
    const menu = renderApp("/projects/p1/apps/a1/settings/scopes/new");
    expect(menu.getByRole("link", { name: "General" })).toHaveAttribute("href", "/projects/p1/apps/a1/settings");
    expect(menu.getByRole("link", { name: "Scopes" })).toHaveAttribute("aria-current", "page");
    expect(menu.getByRole("link", { name: "Configuration" })).toHaveAttribute("href", "/projects/p1/apps/a1/settings/configuration");
    expect(menu.getByRole("link", { name: "CI" })).toHaveAttribute("href", "/projects/p1/apps/a1/settings/ci");
    expect(menu.getByRole("link", { name: "General" })).not.toHaveAttribute("aria-current");
  });
});
