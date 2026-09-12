"use client";

import { Trash2 } from "lucide-react";
import { useTransition } from "react";
import { Button } from "@/components/ui/button";
import { removeProject } from "./actions";

export function RemoveButton({ id }: { id: string }) {
  const [pending, start] = useTransition();

  return (
    <Button
      variant="ghost"
      size="icon"
      disabled={pending}
      title="Unregister (does not touch the files)"
      onClick={() => {
        if (confirm("Unregister this project? Files are not touched.")) start(() => removeProject(id));
      }}
    >
      <Trash2 className="size-4" />
    </Button>
  );
}
