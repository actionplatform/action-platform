import { describe, expect, it } from "vitest";
import type { Matrix } from "@/lib/api";
import { itemsFrom, listTitle } from "./template-item";

const matrix = {
  types: [{ id: "web", label: "Web", description: "" }],
  stacks: [
    { id: "python", label: "Python", icon: "/py.svg" },
    { id: "node", label: "Node.js", icon: null },
  ],
  projects: [
    { source: "official", type: "web", stack: "python", template: "fastapi", description: "API", default: true, plain: false },
    { source: "acme", type: "web", stack: "", template: "blank", description: "Plain", default: false, plain: true, url: "https://git.example.com/acme/blank" },
    { source: "official", type: "web", stack: "node", template: "next", description: "App", default: false, plain: false, icon: "/next.svg", stack_icon: "/node.svg" },
  ],
  clouds: [{ source: "official", name: "aws-lambda", description: "Lambda", languages: ["python", "go"], icon: "/aws.svg" }],
} as unknown as Matrix;

describe("itemsFrom", () => {
  const items = itemsFrom(matrix);

  it("lists projects before clouds", () => {
    expect(items.map((i) => i.name)).toEqual(["fastapi", "blank", "next", "aws-lambda"]);
  });

  it("builds the new-app link from the template, adding the source only when it is not official", () => {
    expect(items[0].href).toBe("/projects/_/apps/new?type=web&stack=python&template=fastapi");
    expect(items[1].href).toBe("/projects/_/apps/new?type=web&template=blank&source=acme");
  });

  it("files a plain repository under repos with no language", () => {
    expect(items[1]).toMatchObject({ categoryId: "repos", categoryLabel: "Repository", stack: null, language: null, plain: true, url: "https://git.example.com/acme/blank" });
  });

  it("labels a project by its type and its stack", () => {
    expect(items[0]).toMatchObject({ categoryId: "web", categoryLabel: "Web", language: "Python", isDefault: true, id: "official:web/python/fastapi" });
  });

  it("prefers the stack icon the template carries over the matrix's", () => {
    expect(items[0].stackIcon).toBe("/py.svg");
    expect(items[2].stackIcon).toBe("/node.svg");
    expect(items[2].icon).toBe("/next.svg");
  });

  it("describes a cloud overlay with the languages it supports and no link", () => {
    expect(items[3]).toMatchObject({ id: "official:cloud/aws-lambda", categoryId: "cloud", categoryLabel: "Cloud overlay", language: "Python, go", href: null, icon: "/aws.svg", stackIcon: null });
  });
});

describe("listTitle", () => {
  it("names the all, cloud and repository lists", () => {
    expect(listTitle(matrix, "all")).toBe("All templates");
    expect(listTitle(matrix, "cloud")).toBe("Cloud templates");
    expect(listTitle(matrix, "repos")).toBe("Repositories added by your organization");
  });

  it("names a type's list by its label", () => {
    expect(listTitle(matrix, "web")).toBe("Web templates");
  });

  it("falls back for a category that no longer exists", () => {
    expect(listTitle(matrix, "gone")).toBe("Templates templates");
  });
});
