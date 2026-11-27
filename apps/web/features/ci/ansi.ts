export type Style = { fg?: string; bg?: string; bold?: boolean; dim?: boolean; italic?: boolean; underline?: boolean };

export type Segment = Style & { text: string };

export type LogLine = { number: number; time: string | null; segments: Segment[]; text: string };

const BASE = ["#4b5563", "#dc2626", "#16a34a", "#ca8a04", "#2563eb", "#c026d3", "#0891b2", "#d1d5db"];
const BRIGHT = ["#6b7280", "#ef4444", "#22c55e", "#eab308", "#3b82f6", "#d946ef", "#06b6d4", "#f9fafb"];

const ESCAPE = /\x1b\[([0-9;]*)([A-Za-z])|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Za-z0-9]/g;
const CONCEALED = /\x1b\[8m[\s\S]*?\x1b\[0?m/g;
const STAMP = /^\s*\[?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\]?\s/;

function palette(n: number): string | undefined {
  if (n < 0 || n > 255) return undefined;
  if (n < 8) return BASE[n];
  if (n < 16) return BRIGHT[n - 8];
  if (n >= 232) {
    const v = 8 + (n - 232) * 10;
    return `rgb(${v},${v},${v})`;
  }
  const i = n - 16;
  const level = (x: number) => (x === 0 ? 0 : 55 + x * 40);
  return `rgb(${level(Math.floor(i / 36))},${level(Math.floor(i / 6) % 6)},${level(i % 6)})`;
}

function extended(codes: number[], at: number): { color?: string; used: number } {
  if (codes[at + 1] === 5) return { color: palette(codes[at + 2]), used: 2 };
  if (codes[at + 1] === 2) {
    const [r, g, b] = codes.slice(at + 2, at + 5);
    return { color: [r, g, b].every((c) => c >= 0 && c <= 255) ? `rgb(${r},${g},${b})` : undefined, used: 4 };
  }
  return { used: 0 };
}

export function applySgr(style: Style, params: string): Style {
  const codes = params === "" ? [0] : params.split(";").map((c) => (c === "" ? 0 : Number(c)));
  let next: Style = { ...style };
  for (let i = 0; i < codes.length; i++) {
    const c = codes[i];
    if (c === 0) next = {};
    else if (c === 1) next.bold = true;
    else if (c === 2) next.dim = true;
    else if (c === 3) next.italic = true;
    else if (c === 4) next.underline = true;
    else if (c === 22) { next.bold = false; next.dim = false; }
    else if (c === 23) next.italic = false;
    else if (c === 24) next.underline = false;
    else if (c >= 30 && c <= 37) next.fg = BASE[c - 30];
    else if (c === 39) next.fg = undefined;
    else if (c >= 40 && c <= 47) next.bg = BASE[c - 40];
    else if (c === 49) next.bg = undefined;
    else if (c >= 90 && c <= 97) next.fg = BRIGHT[c - 90];
    else if (c >= 100 && c <= 107) next.bg = BRIGHT[c - 100];
    else if (c === 38 || c === 48) {
      const { color, used } = extended(codes, i);
      if (c === 38) next.fg = color;
      else next.bg = color;
      i += used;
    }
  }
  return next;
}

function same(a: Style, b: Style): boolean {
  return a.fg === b.fg && a.bg === b.bg && !!a.bold === !!b.bold && !!a.dim === !!b.dim && !!a.italic === !!b.italic && !!a.underline === !!b.underline;
}

export function segmentsOf(line: string, start: Style = {}): { segments: Segment[]; style: Style } {
  const segments: Segment[] = [];
  let style = start;
  let last = 0;
  const push = (text: string) => {
    if (!text) return;
    const prev = segments[segments.length - 1];
    if (prev && same(prev, style)) prev.text += text;
    else segments.push({ ...style, text });
  };
  for (const m of line.matchAll(ESCAPE)) {
    push(line.slice(last, m.index));
    if (m[2] === "m") style = applySgr(style, m[1]);
    last = (m.index ?? 0) + m[0].length;
  }
  push(line.slice(last));
  return { segments, style };
}

export function stripAnsi(text: string): string {
  return text.replace(CONCEALED, "").replace(ESCAPE, "");
}

export function parseLog(text: string, first = 1): LogLine[] {
  const lines: LogLine[] = [];
  let style: Style = {};
  const raw = text.replace(CONCEALED, "").replace(/\r\n/g, "\n").split("\n");
  if (raw.length > 0 && raw[raw.length - 1] === "") raw.pop();
  raw.forEach((source, i) => {
    const visible = source.includes("\r") ? source.slice(source.lastIndexOf("\r") + 1) : source;
    const plain = visible.replace(ESCAPE, "");
    const stamp = STAMP.exec(plain);
    const parsed = segmentsOf(stamp ? stripStamp(visible, stamp[0].length) : visible, style);
    style = parsed.style;
    lines.push({ number: first + i, time: stamp ? stamp[1] : null, segments: parsed.segments, text: stamp ? plain.slice(stamp[0].length) : plain });
  });
  return lines;
}

function stripStamp(line: string, visibleLength: number): string {
  let seen = 0;
  let i = 0;
  ESCAPE.lastIndex = 0;
  while (i < line.length && seen < visibleLength) {
    if (line[i] === "\x1b") {
      ESCAPE.lastIndex = i;
      const m = ESCAPE.exec(line);
      if (m && m.index === i) { i += m[0].length; continue; }
    }
    i++;
    seen++;
  }
  return line.slice(i);
}
