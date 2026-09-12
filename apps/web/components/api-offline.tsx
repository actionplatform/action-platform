import { API_BASE } from "@/lib/api";

export function ApiOffline({ error }: { error: unknown }) {
  return (
    <div className="rounded-lg border border-foreground bg-surface p-4 text-sm">
      <div className="font-medium text-foreground">API unreachable at {API_BASE}</div>
      <div className="text-muted-foreground mt-1">
        Start it with <code className="font-mono">action-platform api</code>. {String((error as Error)?.message ?? error)}
      </div>
    </div>
  );
}
