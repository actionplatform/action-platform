import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Plugins" description="Extensions for the CLI and the MCP server: deploy targets, overlays, tools, release strategies." variant="cards" label="Loading plugins" />;
}
