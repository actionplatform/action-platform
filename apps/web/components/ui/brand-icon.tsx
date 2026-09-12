import type { SimpleIcon } from "simple-icons";
import { cn } from "@/lib/utils";

// Simple Icons path in the brand's own color. Marks that would vanish on the
// black ground (Rust, GitHub…) fall back to the foreground color.
export function BrandIcon({ icon, className, title, mono }: { icon: SimpleIcon; className?: string; title?: string; mono?: boolean }) {
  const fill = mono || !readable(icon.hex) ? "currentColor" : `#${icon.hex}`;

  return (
    <svg viewBox="0 0 24 24" role="img" aria-label={title ?? icon.title} className={cn("size-5 shrink-0", className)} style={{ fill }}>
      <path d={icon.path} />
    </svg>
  );
}

// Relative luminance above a small threshold: enough contrast against #080808.
function readable(hex: string): boolean {
  const n = parseInt(hex, 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.08;
}
