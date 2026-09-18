"use client";

import { useEffect, useState, useTransition } from "react";
import { call } from "./call";
import type { Result } from "./result";

export type Step = "idle" | "previewing" | "previewed" | "confirming" | "running" | "polling" | "done" | "failed";

type Poll<R> = (handle: string) => Promise<Result<{ status: string; outcome: R | null; error: string | null }>>;

type Options<P, R> = {
  preview?: () => Promise<Result<P>>;
  run: () => Promise<Result<R | { job: string }>>;
  poll?: Poll<R>;
  whileAway?: string;
  onDone?: (result: R) => void;
};

export function useAction<P, R>({ preview, run, poll, whileAway, onDone }: Options<P, R>) {
  const [step, setStep] = useState<Step>("idle");
  const [previewed, setPreviewed] = useState<P | null>(null);
  const [result, setResult] = useState<R | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<string | null>(null);
  const [lastJob, setLastJob] = useState<string | null>(null);
  const [, start] = useTransition();

  useEffect(() => {
    if (!job || !poll) return;
    const timer = setInterval(async () => {
      const r = await poll(job);
      if (!r.ok) { setError(r.error); setStep("failed"); setJob(null); return; }
      if (r.data.status === "done") { setResult(r.data.outcome); setStep("done"); setJob(null); if (r.data.outcome) onDone?.(r.data.outcome); }
      if (r.data.status === "failed") { setError(r.data.error ?? "failed"); setStep("failed"); setJob(null); }
    }, 2000);
    return () => clearInterval(timer);
  }, [job, poll, onDone]);

  const busy = step === "previewing" || step === "running" || step === "polling";

  const doPreview = () => {
    if (!preview || busy) return;
    start(async () => {
      setError(null);
      setStep("previewing");
      const r = await preview();
      if (r.ok) { setPreviewed(r.data); setStep("previewed"); } else { setError(r.error); setStep("failed"); }
    });
  };

  const execute = () => {
    if (busy) return;
    start(async () => {
      setError(null);
      setResult(null);
      setStep("running");
      const r = await call(run, (e) => ({ ok: false as const, error: e }), whileAway);
      if (!r.ok) { setError(r.error); setStep("failed"); return; }
      if (poll && r.data && typeof r.data === "object" && "job" in r.data) { const id = (r.data as { job: string }).job; setJob(id); setLastJob(id); setStep("polling"); return; }
      setResult(r.data as R);
      setStep("done");
      onDone?.(r.data as R);
    });
  };

  const reset = () => { setStep("idle"); setPreviewed(null); setResult(null); setError(null); setJob(null); setLastJob(null); };

  return { step, busy, previewed, result, error, job: lastJob, preview: doPreview, confirm: () => setStep("confirming"), cancel: () => setStep(previewed ? "previewed" : "idle"), execute, reset, clearOutcome: () => { setResult(null); setError(null); setLastJob(null); if (step === "done" || step === "failed") setStep("idle"); } };
}
