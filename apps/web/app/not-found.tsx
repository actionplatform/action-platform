import Link from "next/link";

export default function NotFound() {
  return (
    <div className="text-sm">
      <div className="font-medium">Not found</div>
      <Link href="/projects" className="underline text-muted-foreground">Back to projects</Link>
    </div>
  );
}
