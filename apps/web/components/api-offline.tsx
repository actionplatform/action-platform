import { API_BASE } from "@/lib/api";

export function ApiOffline({ error }: { error: unknown }) {
  return (
    <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm">
      <div className="font-medium text-destructive">API unreachable at {API_BASE}</div>
      <div className="text-muted-foreground mt-1">
        Start it with <code className="font-mono">action-platform api</code>. {String((error as Error)?.message ?? error)}
      </div>
    </div>
  );
}
