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
  options: [{ key: "role_arn", label: "AWS account", kind: "text", help: "", required: true, action_label: "Connect AWS", action_url: "https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate" }],
  values: {},
};

describe("PluginCards", () => {
  afterEach(cleanup);

  it("shows a required option as not configured until it has a value", () => {
    render(<PluginCards plugins={[lambda]} canManage />);
    expect(screen.getByText("Not configured")).toBeInTheDocument();
    cleanup();

    render(<PluginCards plugins={[{ ...lambda, values: { role_arn: "123456789012" } }]} canManage />);
    expect(screen.getByText("Configured")).toBeInTheDocument();
  });

  it("a plugin without options is just installed, with no button", () => {
    render(<PluginCards plugins={[{ ...lambda, options: [] }]} canManage />);
    expect(screen.getByText("Installed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /configure/i })).toBeNull();
  });

  it("saves the form through the action", async () => {
    render(<PluginCards plugins={[lambda]} canManage />);
    fireEvent.click(screen.getByRole("button", { name: /configure/i }));
    fireEvent.change(screen.getByLabelText("AWS account"), { target: { value: "123456789012" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(savePluginOptions).toHaveBeenCalledWith("aws-lambda", { role_arn: "123456789012" }));
  });

  it("an option with an action copies its command and opens its page from a button", async () => {
    const open = vi.spyOn(window, "open").mockImplementation(() => null);
    const writeText = vi.fn(async () => undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const withCopy = { ...lambda, options: [{ ...lambda.options[0], action_copy: "aws cloudformation deploy" }] };
    render(<PluginCards plugins={[withCopy]} canManage />);
    fireEvent.click(screen.getByRole("button", { name: /configure/i }));
    fireEvent.click(screen.getByRole("button", { name: "Connect AWS" }));

    await waitFor(() => expect(open).toHaveBeenCalledWith("https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate", "_blank", "noopener,noreferrer"));
    expect(writeText).toHaveBeenCalledWith("aws cloudformation deploy");
    await waitFor(() => expect(screen.getByText(/Command copied/)).toBeInTheDocument());
  });

  it("a plugin that failed to load says why", () => {
    render(<PluginCards plugins={[{ ...lambda, error: "ImportError: boto3" }]} canManage />);
    expect(screen.getByText("Failed to load")).toBeInTheDocument();
    expect(screen.getByText("ImportError: boto3")).toBeInTheDocument();
  });
});
