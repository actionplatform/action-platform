import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Matrix } from "@/lib/api";
import { useAppWizard } from "./use-app-wizard";

vi.mock("./actions", () => ({ createAppFromTemplate: vi.fn() }));

const matrix: Matrix = {
  projects: [
    { type: "web", stack: "python", template: "fastapi", default: true, description: "", source: "official", plain: false },
    { type: "web", stack: "node", template: "fastify", default: true, description: "", source: "official", plain: false },
    { type: "empty", stack: "", template: "empty", default: true, description: "", source: "official", plain: false },
  ],
  clouds: [{ name: "aws/lambda", types: ["web"], languages: ["python"], description: "", source: "official" }],
  services: [],
  sources: [],
  types: [{ id: "web", label: "Web", description: "" }, { id: "empty", label: "Empty", description: "" }],
  stacks: [{ id: "python", label: "Python" }, { id: "node", label: "Node" }],
};

const hosts = [{ id: "h1", name: "GitHub", kind: "github", defaultOwner: "acme", owners: [], installUrl: null, problem: null }];

function wizard(preset: Parameters<typeof useAppWizard>[0]["preset"] = null) {
  return renderHook(() => useAppWizard({ matrix, preset, projectId: "p1", projects: [{ id: "p1", name: "Shop" }], hosts }));
}

describe("useAppWizard", () => {
  it("walks type → stack → configuration when the stack has one template", () => {
    const { result } = wizard();

    expect(result.current.canContinue).toBe(false);
    act(() => result.current.pickType("web"));
    expect(result.current.canContinue).toBe(true);
    act(() => result.current.next());
    expect(result.current.step).toBe(1);
    act(() => result.current.pickStack("python"));
    expect(result.current.template).toBe("fastapi");
    act(() => result.current.next());
    expect(result.current.step).toBe(3);
  });

  it("skips the stack and the template for a type without stacks", () => {
    const { result } = wizard();

    act(() => result.current.pickType("empty"));
    act(() => result.current.next());
    expect(result.current.step).toBe(3);
    expect(result.current.template).toBe("empty");
  });

  it("derives directory and package name from the name until edited", () => {
    const { result } = wizard();

    act(() => result.current.setConfig({ ...result.current.config, name: "Orders API" }));
    expect(result.current.config.directory).toBe("orders-api");
    expect(result.current.config.packageName).toBe("orders_api");
    act(() => result.current.setDirectory("custom dir"));
    act(() => result.current.setConfig({ ...result.current.config, name: "Other" }));
    expect(result.current.config.directory).toBe("custom-dir");
    expect(result.current.config.packageName).toBe("other");
  });

  it("offers only the clouds that fit the chosen template", () => {
    const { result } = wizard();

    act(() => result.current.pickType("web"));
    act(() => result.current.pickStack("node"));
    expect(result.current.clouds).toEqual([]);
    act(() => result.current.pickStack("python"));
    expect(result.current.clouds.map((c) => c.name)).toEqual(["aws/lambda"]);
  });

  it("starts at configuration with a preset and needs a name to continue", () => {
    const { result } = wizard({ type: "web", stack: "python", template: "fastapi" });

    expect(result.current.step).toBe(3);
    expect(result.current.canContinue).toBe(false);
    act(() => result.current.setConfig({ ...result.current.config, name: "Shop" }));
    expect(result.current.canContinue).toBe(true);
    expect(result.current.command).toBe(`action-platform init web python --name "Shop" --ci github`);
  });
});
