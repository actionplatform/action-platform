import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ReadinessSummary } from "./readiness-badges";

const many = { dev: "ok", "prod-lambda": "ok", "prod-dokploy": "blocked", "danger-worker-one": "blocked", "prod-worker-two": "ok" } as const;

describe("ReadinessSummary", () => {
  afterEach(cleanup);

  it("shows a dash with no readiness", () => {
    render(<ReadinessSummary readiness={{}} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows one ready badge when every scope is ready", () => {
    render(<ReadinessSummary readiness={{ a: "ok", b: "ok", c: "ok" }} />);
    expect(screen.getByText("3 ready")).toBeInTheDocument();
    expect(screen.queryByText(/blocked/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "3 scopes: 3 ready" })).toBeInTheDocument();
  });

  it("shows counts per state", () => {
    render(<ReadinessSummary readiness={{ ...many, p: "pending" }} />);
    expect(screen.getByText("2 blocked")).toBeInTheDocument();
    expect(screen.getByText("1 checking")).toBeInTheDocument();
    expect(screen.getByText("3 ready")).toBeInTheDocument();
  });

  it("lists every scope untruncated on hover and on click", () => {
    render(<ReadinessSummary readiness={many} />);
    const trigger = screen.getByRole("button", { name: /5 scopes/ });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.mouseEnter(trigger.parentElement!);
    const tip = screen.getByRole("tooltip");
    expect(tip).toHaveTextContent("danger-worker-one");
    expect(tip).toHaveTextContent("prod-dokploy");
    expect(tip.textContent).toContain("blocked");
    fireEvent.mouseLeave(trigger.parentElement!);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.click(trigger);
    expect(screen.getByRole("tooltip")).toHaveTextContent("prod-lambda");
  });

  it("opens on keyboard focus", () => {
    render(<ReadinessSummary readiness={many} />);
    fireEvent.focus(screen.getByRole("button", { name: /5 scopes/ }));
    expect(screen.getByRole("tooltip")).toHaveTextContent("prod-worker-two");
  });
});
