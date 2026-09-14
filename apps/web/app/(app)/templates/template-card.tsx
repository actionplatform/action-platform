"use client";

import { ArrowRight, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Dialog } from "@/components/ui/dialog";
import { setCloudTarget } from "@/app/(app)/projects/[project]/apps/actions";
import { Badge } from "@/components/ui/badge";
import { BrandIcon } from "@/components/ui/brand-icon";
import { typeIcon } from "@/lib/catalog";
import { cn } from "@/lib/utils";
import type { TemplateItem } from "./template-item";

export function TemplateLogo({ item, className }: { item: TemplateItem; className?: string }) {
  const Fallback = typeIcon(item.plain ? "repos" : item.type);
  return (
    <div className={cn("flex size-[42px] shrink-0 items-center justify-center rounded-lg border border-[#292929] bg-[#0e0e0e]", className)}>
      {item.icon ? <BrandIcon src={item.icon} title={item.name} className="size-6" /> : <Fallback className="size-[22px] text-secondary" strokeWidth={1.5} />}
    </div>
  );
}

export function TemplateMeta({ item, className }: { item: TemplateItem; className?: string }) {
  const TypeIcon = typeIcon(item.plain ? "repos" : item.type);
  return (
    <div className={cn("flex min-w-0 items-center gap-2.5 text-[13px] text-secondary", className)}>
      <span className="flex items-center gap-1.5"><TypeIcon className="size-4" strokeWidth={1.75} />{item.categoryLabel}</span>
      {item.language && (
        <>
          <span aria-hidden className="text-muted-foreground">·</span>
          <span className="flex items-center gap-1.5">
            {item.stackIcon && <BrandIcon src={item.stackIcon} className="size-3.5" />}
            {item.language}
          </span>
        </>
      )}
    </div>
  );
}

export type OverlayTarget = { id: string; projectId: string; registryId: string; name: string; project: string };

function ApplyOverlayDialog({ item, targets, open, onClose }: { item: TemplateItem; targets: OverlayTarget[]; open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [target, setTarget] = useState(targets[0]?.id ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const chosen = targets.find((t) => t.id === target);

  return (
    <Dialog
      open={open}
      onClose={() => !pending && onClose()}
      title={`Apply ${item.name}`}
      description="Adds the overlay files as pending changes on the app and sets its deploy target. Commit the result from the app's Configuration page."
      footer={<><Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button><Button disabled={pending || !chosen} onClick={() => { if (!chosen) return; start(async () => { setError(null); const r = await setCloudTarget(chosen.projectId, chosen.registryId, item.name, item.source); if (r.ok) { onClose(); router.push(`/projects/${chosen.projectId}/apps/${chosen.id}/configuration`); } else setError(r.error); }); }}>{pending ? "Applying…" : "Apply overlay"}</Button></>}
    >
      {targets.length === 0 ? (
        <p className="text-sm text-secondary">No apps in this organization yet. Create one from a project first.</p>
      ) : (
        <div className="space-y-3">
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">App</span>
            <Select autoFocus value={target} onChange={setTarget} options={targets.map((t) => ({ value: t.id, label: `${t.project} / ${t.name}` }))} />
          </label>
          {item.language && <p className="text-xs text-muted-foreground">Supports {item.language}. Other apps are refused.</p>}
          {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
        </div>
      )}
    </Dialog>
  );
}

export function TemplateCard({ item, targets }: { item: TemplateItem; targets: OverlayTarget[] }) {
  const [open, setOpen] = useState(false);
  const body = (
    <>
      <div className="flex items-start gap-3">
        <TemplateLogo item={item} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-mono text-base font-semibold leading-6">{item.name}</h3>
            {item.isDefault && <Badge tone="inverse" className="h-6 px-[9px]">Default</Badge>}
            {item.source !== "official" && <Badge className="h-6 px-[9px] font-mono">{item.source}</Badge>}
          </div>
          <p className="mt-1 line-clamp-2 text-sm leading-5 text-secondary">{item.description}</p>
        </div>
        <ArrowUpRight className="size-[17px] shrink-0 text-muted-foreground transition-[color,transform] duration-150 group-hover:-translate-y-px group-hover:translate-x-px group-hover:text-foreground group-focus-visible:text-foreground" strokeWidth={1.75} />
      </div>
      <div className="mt-auto flex items-center gap-2.5 border-t border-[#242424] pt-3.5">
        <TemplateMeta item={item} />
        {(item.href || (item.type === "cloud" && targets.length > 0)) && (
          <span className="ml-auto flex h-[34px] items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-semibold text-primary-foreground opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 [@media(hover:none)]:opacity-100">
            {item.href ? "Use template" : "Apply to app"} <ArrowRight className="size-3.5" strokeWidth={2} />
          </span>
        )}
      </div>
    </>
  );

  const className = "group flex min-h-[164px] flex-col rounded-[9px] border border-border bg-surface p-4 transition-[background-color,border-color,transform] duration-150 ease-out hover:-translate-y-px hover:border-border-hover hover:bg-[#141414] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white/[0.18]";

  if (item.href) return <Link href={item.href} aria-label={`Use the ${item.name} template`} className={className}>{body}</Link>;
  if (item.type !== "cloud" || targets.length === 0) return <article aria-label={item.name} className={className}>{body}</article>;
  return (
    <>
      <button type="button" aria-label={`Apply the ${item.name} overlay`} onClick={() => setOpen(true)} className={cn(className, "text-left")}>{body}</button>
      <ApplyOverlayDialog item={item} targets={targets} open={open} onClose={() => setOpen(false)} />
    </>
  );
}

export function TemplateListItem({ item, targets }: { item: TemplateItem; targets: OverlayTarget[] }) {
  const [open, setOpen] = useState(false);
  const body = (
    <>
      <TemplateLogo item={item} className="size-10" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate font-mono text-[15px] font-semibold">{item.name}</span>
          {item.isDefault && <Badge tone="inverse" className="h-5 px-2 md:hidden">Default</Badge>}
          {item.source !== "official" && <Badge className="h-5 px-2 font-mono">{item.source}</Badge>}
        </div>
        <p className="truncate text-[13px] text-secondary">{item.description}</p>
      </div>
      <div className="hidden w-40 shrink-0 text-[13px] text-secondary md:block">{item.categoryLabel}</div>
      <div className="hidden w-32 shrink-0 items-center gap-1.5 text-[13px] text-secondary md:flex">
        {item.stackIcon && <BrandIcon src={item.stackIcon} className="size-3.5" />}
        {item.language ?? "—"}
      </div>
      <div className="hidden w-20 shrink-0 md:block">{item.isDefault && <Badge tone="inverse" className="h-5 px-2">Default</Badge>}</div>
      <ArrowUpRight className="size-[17px] shrink-0 text-muted-foreground transition-colors group-hover:text-foreground" strokeWidth={1.75} />
    </>
  );
  const className = "group flex h-[72px] items-center gap-4 px-4 transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:bg-surface-hover";
  if (item.href) return <Link href={item.href} aria-label={`Use the ${item.name} template`} className={className}>{body}</Link>;
  if (item.type !== "cloud" || targets.length === 0) return <div className={className}>{body}</div>;
  return (
    <>
      <button type="button" aria-label={`Apply the ${item.name} overlay`} onClick={() => setOpen(true)} className={cn(className, "w-full text-left")}>{body}</button>
      <ApplyOverlayDialog item={item} targets={targets} open={open} onClose={() => setOpen(false)} />
    </>
  );
}
