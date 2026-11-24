import { describe, expect, it } from "vitest";
import type { InstanceHealthRow } from "@/lib/v1";
import { ageText, problems } from "./health";

const healthy = (over: Partial<InstanceHealthRow> = {}): InstanceHealthRow => ({
  status: "ok",
  database: true,
  migrations: true,
  workers: { light: true, deploy: true },
  version: "1.0.0",
  api: "1.0.0",
  workers_seen: [],
  queue: [],
  integrations: { smtp: { configured: false }, google: { configured: false, redirect_uri: "https://x/api/sign-in/google/callback" }, sentry_api: false, oauth_apps: [] },
  ...over,
});

describe("ageText", () => {
  it("scales from seconds to days", () => {
    expect([null, 5, 120, 3700, 90000].map(ageText)).toEqual(["—", "5s", "2m", "1h 1m", "1d"]);
  });
});

describe("problems", () => {
  it("is empty when everything works", () => {
    expect(problems(healthy())).toEqual([]);
  });

  it("names a group without workers", () => {
    expect(problems(healthy({ status: "unavailable", workers: { light: true, deploy: false } }))).toEqual(["No worker is running for deploy jobs."]);
  });

  it("reports the database before anything else", () => {
    expect(problems(healthy({ database: false, migrations: false, workers: { light: false, deploy: false } }))).toEqual(["The database does not answer."]);
    expect(problems(healthy({ migrations: false, workers: { light: false, deploy: false } }))).toEqual(["The database is behind the API: run the migrations."]);
  });

  it("flags queued jobs of a kind nobody takes", () => {
    const queue = [{ kind: "install", group: "light", queued: 2, running: 0, oldest_queued_seconds: 400, worker_running: false }];
    expect(problems(healthy({ queue }))).toEqual(["2 install jobs waiting and no worker takes install jobs."]);
  });
});
