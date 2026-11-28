import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type Config, type JsonSchema, type StrategyDef, FALLBACK_SAFETY, defaultsOf, safetyDefaults } from "./strategies";
import { SafetyFields, SchemaForm, StrategyPicker } from "./strategy-form";

afterEach(cleanup);

const rolling: JsonSchema = { type: "object", properties: { batch_percent: { type: "integer", minimum: 1, maximum: 100, default: 25 }, pause_seconds: { type: "integer", minimum: 0, default: 60 } } };
const canary: JsonSchema = { type: "object", properties: { steps: { type: "array", minItems: 1, items: { type: "object" }, default: [{ weight: 5, pause_seconds: 300 }, { weight: 100, pause_seconds: 0 }] } } };

const defs: StrategyDef[] = ["recreate", "rolling", "blue_green", "canary", "shadow"].map((id) => ({ id, label: id, description: id, config_schema: { type: "object", properties: {} } }));

function Host({ schema, onValue }: { schema: JsonSchema; onValue?: (v: Config) => void }) {
  const [value, setValue] = useState<Config>(defaultsOf(schema));
  return <SchemaForm schema={schema} value={value} onChange={(v) => { setValue(v); onValue?.(v); }} />;
}

describe("SchemaForm", () => {
  it("renders a number input per property with the schema defaults", () => {
    render(<Host schema={rolling} />);
    expect(screen.getByLabelText(/Batch percent/)).toHaveValue(25);
    expect(screen.getByLabelText(/Pause seconds/)).toHaveValue(60);
  });

  it("renders booleans as checkboxes and reports changes", () => {
    const seen = vi.fn();
    render(<Host schema={{ type: "object", properties: { enabled: { type: "boolean", default: true } } }} onValue={seen} />);
    const box = screen.getByLabelText("Enabled");
    expect(box).toBeChecked();
    fireEvent.click(box);
    expect(seen).toHaveBeenLastCalledWith({ enabled: false });
  });

  it("edits the canary steps: add, change and remove rows", () => {
    const seen = vi.fn();
    render(<Host schema={canary} onValue={seen} />);
    expect(screen.getByLabelText("Weight progression")).toHaveTextContent("5% → 100%");
    fireEvent.click(screen.getByRole("button", { name: /Add step/ }));
    expect(screen.getByLabelText("Step 3 weight")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Step 2 weight"), { target: { value: "50" } });
    expect(screen.getByLabelText("Weight progression")).toHaveTextContent("5% → 50% → 100%");
    fireEvent.click(screen.getByRole("button", { name: "Remove step 1" }));
    expect(screen.queryByLabelText("Step 3 weight")).not.toBeInTheDocument();
    expect(seen).toHaveBeenCalled();
  });

  it("asks for a last step at 100%", () => {
    render(<Host schema={canary} />);
    fireEvent.change(screen.getByLabelText("Step 2 weight"), { target: { value: "60" } });
    expect(screen.getByRole("alert")).toHaveTextContent("last step must reach 100%");
  });

  it("keeps the last step from being removed", () => {
    render(<Host schema={{ type: "object", properties: { steps: { type: "array", default: [{ weight: 100, pause_seconds: 0 }] } } }} />);
    expect(screen.getByRole("button", { name: "Remove step 1" })).toBeDisabled();
  });
});

describe("StrategyPicker", () => {
  it("shows the five strategies and selects one", () => {
    const pick = vi.fn();
    render(<StrategyPicker strategies={defs} support={null} value="recreate" onChange={pick} />);
    expect(screen.getAllByRole("radio")).toHaveLength(5);
    expect(screen.getByText("Replace all instances at once.")).toBeInTheDocument();
    expect(screen.getByText("Mirror traffic to a new version.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: /Canary/ }));
    expect(pick).toHaveBeenCalledWith("canary");
  });

  it("disables what the scope cannot run and says why", () => {
    const pick = vi.fn();
    const support = [{ id: "recreate", supported: true }, { id: "canary", supported: false, reason: "aws/lambda cannot run canary: it lacks shift" }];
    render(<StrategyPicker strategies={defs} support={support} value="recreate" onChange={pick} />);
    const radio = screen.getByRole("radio", { name: /Canary/ });
    expect(radio).toBeDisabled();
    expect(screen.getByText("aws/lambda cannot run canary: it lacks shift")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Recreate/ })).toBeEnabled();
  });
});

describe("SafetyFields", () => {
  it("starts from the schema defaults", () => {
    expect(safetyDefaults(FALLBACK_SAFETY)).toEqual({ auto_rollback: true, manual_approval: false, bake_seconds: 0 });
  });

  it("reports each toggle", () => {
    const seen = vi.fn();
    render(<SafetyFields schema={FALLBACK_SAFETY} value={safetyDefaults(FALLBACK_SAFETY)} onChange={seen} />);
    fireEvent.click(screen.getByLabelText("Require manual approval"));
    expect(seen).toHaveBeenLastCalledWith({ auto_rollback: true, manual_approval: true, bake_seconds: 0 });
    fireEvent.click(screen.getByLabelText("Automatic rollback"));
    expect(seen).toHaveBeenLastCalledWith({ auto_rollback: false, manual_approval: false, bake_seconds: 0 });
  });
});
