import { readFileSync, writeFileSync } from "node:fs";

const file = process.argv[2];
const source = readFileSync(file, "utf8");
const stripped = source
  .replace(/^[ \t]*\/\*\*[\s\S]*?\*\/[ \t]*\n/gm, "")
  .replace(/[ \t]*\/\*\*[\s\S]*?\*\//g, "")
  .replace(/^[ \t]*\/\/.*\n/gm, "")
  .replace(/\n{3,}/g, "\n\n").replace(/^\n+/, "");
writeFileSync(file, stripped);
