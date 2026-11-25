import { Target } from "lucide-react";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Cell, type Column, DataTable } from "./data-table";
import { Td, Th } from "./table";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), usePathname: () => "/", useSearchParams: () => new URLSearchParams() }));

type Row = { id: string; name: string; count: number };

const rows: Row[] = [{ id: "1", name: "production-eu-west-with-a-long-name", count: 12 }];

const columns: Column<Row>[] = [
  { key: "name", label: "Name", width: 60, render: (r) => <Cell>{r.name}</Cell> },
  { key: "notes", label: "Notes", width: 20, wrap: true, render: () => <Cell wrap>candidate, stable, hotfix</Cell> },
  { key: "count", label: "Runs", width: 14, numeric: true, render: (r) => r.count },
  { key: "actions", label: "Actions", width: "56px", actions: true, render: (r) => <button type="button">Open {r.name}</button> },
];

function table() {
  render(<DataTable title="Things" rows={rows} rowKey={(r) => r.id} columns={columns} noun={["thing", "things"]} empty={{ icon: Target, title: "None" }} />);
  return screen.getByRole("table");
}

function overflowing(scroll: number, client: number) {
  const scrollWidth = vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(scroll);
  const clientWidth = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(client);
  return () => { scrollWidth.mockRestore(); clientWidth.mockRestore(); };
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("DataTable columns", () => {
  it("sizes each column from its width, as a percentage or a CSS length", () => {
    const cols = table().querySelectorAll("col");
    expect([...cols].map((c) => c.style.width)).toEqual(["60%", "20%", "14%", "56px"]);
  });

  it("right-aligns numeric columns, header included, with tabular figures", () => {
    const t = table();
    const header = within(t).getByRole("columnheader", { name: "Runs" });
    const cell = within(t).getByText("12").closest("td")!;
    for (const el of [header, cell]) expect(el).toHaveClass("text-right", "tabular-nums");
    expect(within(t).getByRole("columnheader", { name: "Name" })).not.toHaveClass("text-right");
  });

  it("gives header and cells of a column the same horizontal padding", () => {
    const t = table();
    const header = within(t).getByRole("columnheader", { name: "Name" });
    const cell = within(t).getAllByText(rows[0].name)[0].closest("td")!;
    for (const cls of ["px-3", "first:pl-4", "last:pr-4"]) {
      expect(header).toHaveClass(cls);
      expect(cell).toHaveClass(cls);
    }
  });

  it("lets a wrapping column grow and keeps the others on one line", () => {
    const t = table();
    expect(within(t).getByText("candidate, stable, hotfix").closest("td")).toHaveClass("whitespace-normal");
    expect(within(t).getByText("candidate, stable, hotfix")).not.toHaveClass("truncate");
    expect(within(t).getAllByText(rows[0].name)[0].closest("td")).toHaveClass("whitespace-nowrap");
  });

  it("keeps the actions column narrow, right-aligned and labelled for screen readers", () => {
    const t = table();
    const header = within(t).getByRole("columnheader", { name: "Actions" });
    expect(header).toHaveClass("text-right");
    expect(header.querySelector(".sr-only")).toHaveTextContent("Actions");
    expect(within(t).getByRole("button", { name: `Open ${rows[0].name}` }).closest("td")).toHaveClass("text-right");
  });

  it("puts the actions next to the identifying column on small screens", () => {
    render(<DataTable title="Things" rows={rows} rowKey={(r) => r.id} columns={columns} noun={["thing", "things"]} empty={{ icon: Target, title: "None" }} />);
    const card = screen.getAllByRole("listitem")[0];
    const buttons = within(card).getAllByRole("button", { name: `Open ${rows[0].name}` });
    expect(buttons).toHaveLength(1);
    expect(within(card).queryByText("Actions")).toBeNull();
  });
});

describe("Cell", () => {
  it("adds no tab stop or tooltip when the value fits", () => {
    const restore = overflowing(80, 120);
    render(<Cell>stable</Cell>);
    const cell = screen.getByText("stable");
    expect(cell).not.toHaveAttribute("tabindex");
    expect(cell).toHaveClass("truncate");
    restore();
  });

  it("makes a truncated value focusable and shows it in full on hover and focus", async () => {
    const restore = overflowing(400, 120);
    render(<Cell>production-eu-west-with-a-long-name</Cell>);
    const cell = await screen.findByText("production-eu-west-with-a-long-name");
    expect(cell).toHaveAttribute("tabindex", "0");
    act(() => { fireEvent.focus(cell); });
    expect(screen.getByRole("tooltip")).toHaveTextContent("production-eu-west-with-a-long-name");
    act(() => { fireEvent.blur(cell); });
    expect(screen.queryByRole("tooltip")).toBeNull();
    fireEvent.mouseEnter(cell.parentElement!);
    expect(screen.getByRole("tooltip")).toHaveTextContent("production-eu-west-with-a-long-name");
    restore();
  });

  it("uses the given title as the full value of rich content", async () => {
    const restore = overflowing(400, 120);
    render(<Cell title="main → feature/645">{["main", " → ", "feature/645"]}</Cell>);
    const cell = await screen.findByText("main → feature/645");
    expect(cell).toHaveAttribute("tabindex", "0");
    act(() => { fireEvent.focus(cell); });
    expect(screen.getByRole("tooltip")).toHaveTextContent("main → feature/645");
    restore();
  });

  it("reads the full value of rich content from what it rendered", async () => {
    const restore = overflowing(400, 120);
    render(<Cell><a href="/x">feature/645-table-density</a></Cell>);
    const link = await screen.findByRole("link", { name: "feature/645-table-density" });
    const cell = link.parentElement!;
    expect(cell).toHaveAttribute("tabindex", "0");
    act(() => { fireEvent.focus(cell); });
    expect(screen.getByRole("tooltip")).toHaveTextContent("feature/645-table-density");
    restore();
  });

  it("never truncates a wrapping cell", () => {
    const restore = overflowing(400, 120);
    render(<Cell wrap>candidate, stable, hotfix</Cell>);
    const cell = screen.getByText("candidate, stable, hotfix");
    expect(cell).not.toHaveAttribute("tabindex");
    expect(cell).toHaveClass("whitespace-normal");
    restore();
  });
});

describe("Th and Td", () => {
  it("share the header and cell styles and align by prop", () => {
    render(<table><thead><tr><Th numeric>Queued</Th><Th align="center">Role</Th></tr></thead><tbody><tr><Td numeric>3</Td><Td align="center">x</Td></tr></tbody></table>);
    expect(screen.getByText("Queued")).toHaveClass("text-right", "tabular-nums", "font-medium", "text-secondary");
    expect(screen.getByText("3")).toHaveClass("text-right", "tabular-nums", "px-3");
    expect(screen.getByText("Role")).toHaveClass("text-center");
    expect(screen.getByText("x")).toHaveClass("text-center");
  });
});
