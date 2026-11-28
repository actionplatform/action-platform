export function TrafficBar({ weight, label = "New version" }: { weight: number; label?: string }) {
  const value = Math.min(100, Math.max(0, Math.round(weight)));
  return (
    <section aria-label="Traffic split">
      <div className="mb-1.5 flex items-center justify-between text-xs text-secondary">
        <span>Traffic</span>
        <span className="font-mono">{label} {value}% · Current {100 - value}%</span>
      </div>
      <div role="progressbar" aria-label={`${label} receives ${value}% of traffic`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value} className="flex h-2 overflow-hidden rounded-full border border-border bg-background">
        <div className="bg-foreground transition-[width]" style={{ width: `${value}%` }} />
      </div>
    </section>
  );
}
