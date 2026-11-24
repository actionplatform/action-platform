import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { OrgSwitcher } from "./org-switcher";
import { ScopeProvider, useScope } from "./scope";

const nav = vi.hoisted(() => ({ pathname: "/dashboard", router: { push: vi.fn(), refresh: vi.fn() } }));
const switchOrganization = vi.hoisted(() => vi.fn(async () => {}));
vi.mock("next/navigation", () => ({ useRouter: () => nav.router, usePathname: () => nav.pathname }));
vi.mock("@/app/(app)/actions", () => ({ switchOrganization }));

const orgs = [{ id: "o1", name: "Acme", slug: "acme" }, { id: "o2", name: "Globex", slug: "globex" }];

function Switching() {
  const { switchingTo } = useScope();
  return <span data-testid="switching">{switchingTo ?? "none"}</span>;
}

function renderSwitcher() {
  return render(<ScopeProvider><OrgSwitcher org={orgs[0]} orgs={orgs} /><Switching /></ScopeProvider>);
}

describe("OrgSwitcher", () => {
  beforeEach(() => { nav.router.push.mockClear(); nav.router.refresh.mockClear(); switchOrganization.mockClear(); });
  afterEach(cleanup);

  it("stays on the dashboard and marks the switch until the new workspace arrives", async () => {
    nav.pathname = "/dashboard";
    renderSwitcher();
    fireEvent.click(screen.getByRole("button", { name: /Acme/ }));
    fireEvent.click(screen.getByRole("button", { name: "Globex" }));
    expect(screen.getByTestId("switching")).toHaveTextContent("o2");
    await waitFor(() => expect(nav.router.push).toHaveBeenCalledWith("/dashboard"));
    expect(switchOrganization).toHaveBeenCalledWith("o2");
    expect(nav.router.refresh).toHaveBeenCalled();
  });

  it("goes to projects from any other page", async () => {
    nav.pathname = "/projects/p1/apps/a1";
    renderSwitcher();
    fireEvent.click(screen.getByRole("button", { name: /Acme/ }));
    fireEvent.click(screen.getByRole("button", { name: "Globex" }));
    await waitFor(() => expect(nav.router.push).toHaveBeenCalledWith("/projects"));
  });

  it("clears the switch once the layout renders the chosen workspace", () => {
    const { rerender } = renderSwitcher();
    fireEvent.click(screen.getByRole("button", { name: /Acme/ }));
    fireEvent.click(screen.getByRole("button", { name: "Globex" }));
    rerender(<ScopeProvider><OrgSwitcher org={orgs[1]} orgs={orgs} /><Switching /></ScopeProvider>);
    expect(screen.getByTestId("switching")).toHaveTextContent("none");
  });
});
