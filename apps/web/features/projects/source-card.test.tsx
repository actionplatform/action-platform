import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { AppView } from "./model";
import { SourceCard } from "./source-card";

function view(targets: number, services: number): AppView {
  return {
    sourceKind: "github",
    repository: "org/repo",
    releaseStrategy: "semver",
    commitConvention: "conventional",
    ci: "github",
    deploy: { targets: Array.from({ length: targets }, (_, i) => ({ name: `t${i}` })) },
    services: Array.from({ length: services }, (_, i) => `svc${i}`),
  } as unknown as AppView;
}

describe("SourceCard", () => {
  afterEach(cleanup);

  it("collapses many targets and services into chips", () => {
    render(<SourceCard view={view(10, 10)} base="/projects/p/apps/a" />);
    expect(screen.getAllByText("+7")).toHaveLength(2);
    expect(screen.queryByText("t5")).not.toBeInTheDocument();
  });

  it("keeps the empty states", () => {
    render(<SourceCard view={view(0, 0)} base="/projects/p/apps/a" />);
    expect(screen.getByText("Not configured", { selector: "span.min-w-0" })).toBeInTheDocument();
    expect(screen.getByText("No services")).toBeInTheDocument();
  });
});
