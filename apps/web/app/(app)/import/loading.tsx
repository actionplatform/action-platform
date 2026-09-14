import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Import" description="Bring a GitHub organization into the platform." variant="cards" label="Loading import" />;
}
