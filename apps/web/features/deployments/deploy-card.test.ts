import { describe, expect, it } from "vitest";

import { targetsOf } from "./deploy-card";

describe("targetsOf", () => {
  it("reads the single form", () => {
    expect(targetsOf({ target: "aws/lambda" }, "prod")).toBe("aws/lambda");
  });

  it("reads [[deploy.targets]] and honours stages", () => {
    const deploy = { targets: [{ name: "pypi", kind: "pypi" }, { name: "lambda", kind: "aws/lambda", stages: ["dev"] }] };
    expect(targetsOf(deploy, "library-production")).toBe("pypi");
    expect(targetsOf(deploy, "dev")).toBe("pypi, lambda");
  });

  it("is null without targets", () => {
    expect(targetsOf({}, "prod")).toBeNull();
  });
});
