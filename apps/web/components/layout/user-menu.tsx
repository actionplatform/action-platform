"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { authClient } from "@/lib/auth-client";

export function UserMenu({ name, email }: { name: string; email: string }) {
  const router = useRouter();
  return (
    <div className="flex items-center justify-between gap-2 px-4 py-3 border-t border-border text-xs">
      <div className="min-w-0">
        <div className="font-medium truncate">{name}</div>
        <div className="text-muted-foreground truncate">{email}</div>
      </div>
      <button
        title="Sign out"
        className="text-secondary hover:text-foreground"
        onClick={async () => { await authClient.signOut(); router.push("/login"); router.refresh(); }}
      >
        <LogOut className="size-4" />
      </button>
    </div>
  );
}
