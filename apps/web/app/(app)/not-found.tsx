import Link from "next/link";
import { PageHeader } from "@/components/layout/page";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <>
      <PageHeader title="Not found" description="This project, app or team no longer exists here, or you cannot see it." />
      <Link href="/projects"><Button>Back to projects</Button></Link>
    </>
  );
}
