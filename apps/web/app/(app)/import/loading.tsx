import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Import" description="Bring a GitHub organization, GitLab group or Bitbucket workspace into the platform." variant="cards" label="Loading import" />;
}
