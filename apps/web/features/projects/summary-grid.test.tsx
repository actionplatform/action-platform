import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { AppView } from "./model";
import { SummaryGrid } from "./summary-grid";

const names = Array.from({ length: 10 }, (_, i) => `target-number-${i}-with-a-long-name`);

function view(count: number, extra: Partial<AppView> = {}): AppView {
  return {
    projectId: "p1",
    appId: "a1",
    branch: "feature/a-very-long-branch-name-that-keeps-going-and-going",
    version: "1.2.3",
    latestTag: "v1.2.3",
    deploy: count === 0 ? {} : { targets: names.slice(0, count).map((name) => ({ name })) },
    ...extra,
  } as AppView;
}

describe("SummaryGrid", () => {
  afterEach(cleanup);

  it("says not configured with no targets", () => {
    render(<SummaryGrid view={view(0)} />);
    expect(screen.getByText("Not configured")).toBeInTheDocument();
    expect(screen.queryByText("Configured")).not.toBeInTheDocument();
  });

  it("shows one target without a +N chip", () => {
    const { container } = render(<SummaryGrid view={view(1)} />);
    expect(screen.getByText(names[0])).toBeInTheDocument();
    expect(screen.getByText("Configured")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\+\d/);
  });

  it("shows three targets as two chips and +1", () => {
    render(<SummaryGrid view={view(3)} />);
    expect(screen.getByText(names[0])).toBeInTheDocument();
    expect(screen.getByText(names[1])).toBeInTheDocument();
    expect(screen.queryByText(names[2])).not.toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
  });

  it("collapses ten targets, links to configuration and keeps card heights equal", () => {
    const { container } = render(<SummaryGrid view={view(10)} />);
    expect(screen.getByText("+8")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /10 deploy targets/ });
    expect(link).toHaveAttribute("href", "/projects/p1/apps/a1/settings/configuration");
    expect(link.getAttribute("aria-label")).toContain(names[9]);
    const cards = Array.from(container.querySelectorAll("div.h-\\[104px\\]"));
    expect(cards).toHaveLength(4);
    cards.forEach((c) => expect(c.className).toContain("overflow-hidden"));
  });

  it("shows the full list in a tooltip on focus", () => {
    render(<SummaryGrid view={view(10)} />);
    fireEvent.focus(screen.getByRole("link", { name: /10 deploy targets/ }));
    expect(screen.getByRole("tooltip")).toHaveTextContent(names.join(", "));
  });

  it("truncates a long branch instead of growing the card", () => {
    render(<SummaryGrid view={view(1)} />);
    const branch = screen.getByText(/a-very-long-branch/);
    expect(branch.className).toContain("truncate");
    expect(branch).toHaveAttribute("title", expect.stringContaining("a-very-long-branch"));
  });
});
