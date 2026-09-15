import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PluginCards, type PluginCardData } from "./plugin-cards";

const savePluginOptions = vi.fn(async () => ({ ok: true as const, data: null }));
vi.mock("./actions", () => ({ savePluginOptions: (...args: unknown[]) => savePluginOptions(...(args as [])) }));

const lambda: PluginCardData = {
  slug: "aws-lambda",
  name: "AWS Lambda",
  version: "0.3.4",
  description: "Deploy to AWS Lambda with SAM",
  error: null,
  options: [{ key: "proxy_url", label: "Deploy proxy URL", kind: "url", help: "", required: true }],
  values: {},
};

describe("PluginCards", () => {
  afterEach(cleanup);

  it("shows a required option as not configured until it has a value", () => {
    render(<PluginCards plugins={[lambda]} canManage />);
    expect(screen.getByText("Not configured")).toBeInTheDocument();
    cleanup();

    render(<PluginCards plugins={[{ ...lambda, values: { proxy_url: "https://x.lambda-url.on.aws" } }]} canManage />);
    expect(screen.getByText("Configured")).toBeInTheDocument();
  });

  it("a plugin without options is just installed, with no form", () => {
    render(<PluginCards plugins={[{ ...lambda, options: [] }]} canManage />);
    expect(screen.getByText("Installed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  });

  it("the form sits on the card and saves through the action once something changed", async () => {
    render(<PluginCards plugins={[lambda]} canManage />);
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Deploy proxy URL"), { target: { value: "https://x.lambda-url.on.aws" } });
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(savePluginOptions).toHaveBeenCalledWith("aws-lambda", { proxy_url: "https://x.lambda-url.on.aws" }));
    expect(screen.getByText("Configured")).toBeInTheDocument();
  });

  it("a viewer sees the values but cannot edit", () => {
    render(<PluginCards plugins={[{ ...lambda, values: { proxy_url: "https://x" } }]} canManage={false} />);
    expect(screen.getByLabelText("Deploy proxy URL")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  });

  it("a plugin that failed to load says why", () => {
    render(<PluginCards plugins={[{ ...lambda, error: "ImportError: boto3" }]} canManage />);
    expect(screen.getByText("Failed to load")).toBeInTheDocument();
    expect(screen.getByText("ImportError: boto3")).toBeInTheDocument();
  });
});
