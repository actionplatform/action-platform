"use client";

import { KeyRound, LogOut } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signOut } from "@/lib/auth-actions";

export function UserMenu({ name, email }: { name: string; email: string }) {
  const router = useRouter();
  return (
    <div className="flex items-center gap-3 border-t border-border px-5 py-4">
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{name}</div>
        <div className="truncate text-[13px] text-secondary">{email}</div>
      </div>
      <Link href="/organization/sessions" title="Connected apps" aria-label="Connected apps" className="flex size-10 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
        <KeyRound className="size-[18px]" strokeWidth={1.75} />
      </Link>
      <button
        type="button"
        title="Sign out"
        aria-label="Sign out"
        className="flex size-10 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"
        onClick={async () => { await signOut(); router.push("/login"); router.refresh(); }}
      >
        <LogOut className="size-[18px]" strokeWidth={1.75} />
      </button>
    </div>
  );
}
