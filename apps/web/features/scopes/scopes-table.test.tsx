import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Scope } from "@/lib/scope-kinds";

const actions = vi.hoisted(() => ({ deleteScope: vi.fn() }));
const nav = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("./actions", () => actions);
vi.mock("next/navigation", () => ({ useRouter: () => nav, usePathname: () => "/", useSearchParams: () => new URLSearchParams() }));

import { ScopesTable } from "./scopes-table";

const scopes: Scope[] = [
  { id: "s1", name: "prod", kind: "aws", criticality: "critical", created_at: "2026-01-01T00:00:00Z" },
  { id: "s2", name: "sandbox", kind: "aws", criticality: "test", created_at: "2026-01-01T00:00:00Z" },
];

function table(canEdit: boolean, rows = scopes) {
  render(<ScopesTable scopes={rows} projectId="p1" appId="a1" canEdit={canEdit} newHref="/projects/p1/apps/a1/scopes/new" />);
  return within(screen.getAllByRole("table")[0]);
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(cleanup);

describe("ScopesTable", () => {
  it("lists each scope with the releases its criticality accepts", () => {
    const t = table(false);
    expect(t.getByText("prod")).toBeInTheDocument();
    expect(t.getByText("stable, hotfix")).toBeInTheDocument();
    expect(t.getByText("candidate, stable, hotfix")).toBeInTheDocument();
  });

  it("offers no actions to someone who cannot edit", () => {
    const t = table(false);
    expect(t.queryByRole("button", { name: /Actions for/ })).not.toBeInTheDocument();
    expect(screen.queryByText("New scope")).not.toBeInTheDocument();
  });

  it("explains an empty list", () => {
    render(<ScopesTable scopes={[]} projectId="p1" appId="a1" canEdit newHref="/x/new" />);
    expect(screen.getAllByText("No scopes yet").length).toBeGreaterThan(0);
  });

  it("asks before deleting and deletes the chosen scope", async () => {
    actions.deleteScope.mockResolvedValue({ ok: true, data: { items: [], kinds: [], criticalities: [] } });
    const t = table(true);
    fireEvent.click(t.getByRole("button", { name: "Actions for prod" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Delete" }));
    expect(screen.getByText("Delete scope prod?")).toBeInTheDocument();
    expect(actions.deleteScope).not.toHaveBeenCalled();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Delete scope" })); });
    expect(actions.deleteScope).toHaveBeenCalledWith("p1", "a1", "prod");
    expect(nav.refresh).toHaveBeenCalled();
  });

  it("keeps the dialog and shows the reason when the delete fails", async () => {
    actions.deleteScope.mockResolvedValue({ ok: false, error: "a deploy is running there" });
    const t = table(true);
    fireEvent.click(t.getByRole("button", { name: "Actions for prod" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Delete" }));
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Delete scope" })); });
    expect(screen.getByRole("alert")).toHaveTextContent("a deploy is running there");
    expect(nav.refresh).not.toHaveBeenCalled();
  });

  it("opens the scope in the editor", async () => {
    const t = table(true);
    fireEvent.click(t.getByRole("button", { name: "Actions for sandbox" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Edit" }));
    expect(nav.push).toHaveBeenCalledWith("/projects/p1/apps/a1/scopes/sandbox");
  });
});
