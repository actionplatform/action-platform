"""A deployment run step by step: the plan stored when it starts, one `deploy_step` job per step that runs it and queues the next, and the controls — promote, pause, resume, abort — a person applies between steps."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Callable, Optional

from action_platform.core.exception import ActionPlatformError
from action_platform.core.rollout import (
    OperationContext,
    OperationResult,
    StepSpec,
    operations_of,
    plan_for,
    strategy as strategy_of,
    validate_safety,
)
from app.core.db.database import Database
from app.core.db.models import Deployment, DeploymentStep
from app.core.errors import Conflict, Invalid, NotFound
from app.core.shared.clock import now
from app.repositories.deployments import RolloutStore, dumps, loads

KIND = "deploy_step"
POLL = timedelta(seconds=15)
ADVANCING = ("running", "rolling_back")
FINISHED = ("success", "failure", "verified", "rolled_back", "aborted")
DEPLOYED = ("deploy_new", "shift", "replace", "mirror", "native")


@dataclass
class StepCall:
    """What the runner needs to call one operation of one step on the target."""

    deployment_id: str
    target: str
    stage: str
    version: str
    strategy: str
    config: dict[str, Any]
    operation: str
    kind: str
    params: dict[str, Any]
    position: int
    external_ref: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)


Runner = Callable[[StepCall], OperationResult]


def stepped(strategy: Optional[str], safety: Optional[dict]) -> bool:
    """Whether a deploy runs step by step: any strategy but recreate, or recreate with an approval or a bake to wait for."""
    found = validate_safety(safety)

    return (strategy or "recreate") != "recreate" or bool(
        found["manual_approval"] or found["bake_seconds"]
    )


def perform(
    tool: Any, target: Any, call: StepCall, ctx: OperationContext
) -> OperationResult:
    """One operation on the target: `recreate` ships through the target's own deploy, every other step through the operations the target offers."""
    ops = operations_of(target)
    offered = set(ops.supports()) if ops is not None else set()

    try:
        if call.strategy == "recreate" and call.operation == "deploy_new":
            return _deploy(tool, target, call)

        if (
            call.strategy == "recreate"
            and call.operation == "retire_old"
            and "retire_old" not in offered
        ):
            return OperationResult(
                True,
                "recreate replaced the old version in place",
                data={"skipped": True},
            )

        if ops is None:
            return OperationResult(False, f"{target.name} offers no operations")

        if call.operation == "native":
            return ops.run_native(
                ctx,
                str(call.params.get("strategy")),
                dict(call.params.get("config") or {}),
            )

        return getattr(ops, call.operation)(ctx)
    except ActionPlatformError as e:
        return OperationResult(False, str(e))


def _deploy(tool: Any, target: Any, call: StepCall) -> OperationResult:
    results = tool.deploy(target=target.name, stage=call.stage, version=call.version)
    url = next((r.url for r in results if r.url), None)
    errors = "; ".join(r.error for r in results if r.error)

    return OperationResult(
        bool(results) and all(r.ok for r in results),
        errors or f"{call.version} deployed",
        data={"url": url} if url else {},
    )


def live_of(steps: list[DeploymentStep]) -> str:
    """What is live after the steps that succeeded, in words."""
    weight: Optional[int] = None
    upto: Optional[int] = None
    mirrored = False
    deployed = False

    for step in steps:
        if step.status != "succeeded":
            continue

        params = loads(step.params, {})

        if step.kind == "deploy_new":
            deployed = True
            weight = int(params.get("weight", 0))
        elif step.kind == "shift":
            weight = int(params.get("weight", 0))
        elif step.kind == "replace":
            upto = int(params.get("upto", 0))
        elif step.kind == "mirror":
            mirrored = bool(params.get("on"))
        elif step.kind == "native":
            deployed = True

    if upto is not None:
        return f"{upto}% of the instances run the new version"

    if mirrored:
        return "traffic is mirrored to the new version; the old version serves it"

    if weight is not None and weight >= 100:
        return "the new version serves all traffic"

    if weight:
        return f"the new version serves {weight}% of traffic, the old version the rest"

    if deployed:
        return "the new version is deployed beside the old one and serves no traffic"

    return "nothing changed: the old version serves all traffic"


class Rollout:
    def __init__(
        self, database: Database, queue: Any, runner: Optional[Runner] = None
    ) -> None:
        self.database = database
        self.queue = queue
        self.runner = runner

    def schedule(
        self, deployment_id: str, payload: dict[str, Any], at: Any = None
    ) -> None:
        self.queue.ensure(
            KIND,
            {
                **{k: v for k, v in payload.items() if k not in ("job_id", "attempt")},
                "deployment_id": deployment_id,
            },
            dedupe_key=f"{KIND}:{deployment_id}",
            organization_id=payload.get("organization_id"),
            app_id=payload.get("app_id"),
            run_after=at,
        )

    def start(
        self,
        deployment_id: str,
        strategy: str,
        config: dict[str, Any],
        safety: dict[str, Any],
        operations: list[str],
        steps: list[StepSpec],
        payload: dict[str, Any],
        actor: Optional[str] = None,
    ) -> None:
        """The plan stored on the deployment, then its first step queued."""
        with self.database.session() as db:
            store = RolloutStore(db)
            row = store.deployment(deployment_id)

            if row is None:
                raise NotFound(f"no deployment {deployment_id}")

            row.strategy = strategy
            row.strategy_config = dumps(config)
            row.safety = dumps(safety)
            row.operations = dumps(sorted(operations))
            row.status = "running"
            store.plan(row, [s.as_dict() for s in steps])
            store.event(
                row,
                "started",
                f"{strategy} of {row.version} to {row.stage} started",
                f"{len(steps)} steps",
                actor,
            )

        self.schedule(deployment_id, payload)

    def advance(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run the deployment's current step once: a wait reschedules itself, an operation is called (or, when a worker died mid-call, asked for its status first), and the next step is queued."""
        id = str(payload["deployment_id"])

        with self.database.session() as db:
            store = RolloutStore(db)
            row = store.deployment(id)

            if row is None:
                return {"deployment": id, "status": "gone"}

            if row.status not in ADVANCING:
                return {"deployment": id, "status": row.status}

            step = store.current(id)

            if step is None:
                self._finish(store, row)

                return {"deployment": id, "status": row.status}

            if step.kind == "approval":
                return self._approval(store, row, step)

            if step.kind == "pause":
                due = self._pause(store, row, step)

                if due is not None:
                    self.schedule(id, payload, due)

                    return {"deployment": id, "status": row.status, "waits_until": due}

                self.schedule(id, payload)

                return {"deployment": id, "status": row.status}

            resumed = step.status == "running"

            if not resumed:
                step.status = "running"
                step.started_at = now()
                step.attempts += 1

            call = self._call(store, row, step)

        if self.runner is None:
            raise ActionPlatformError("no runner for deployment steps")

        outcome: Optional[OperationResult] = None

        if resumed:
            asked = self.runner(_as(call, "status"))
            state = asked.state if asked.ok else None

            if state == "running":
                self.schedule(id, payload, now() + POLL)

                return {"deployment": id, "status": "running", "step": call.position}

            if state in ("succeeded", "failed"):
                outcome = asked
            else:
                self._attempt(call)

        if outcome is None:
            outcome = self.runner(call)

        return self._record(call, outcome, payload)

    def _call(
        self, store: RolloutStore, row: Deployment, step: DeploymentStep
    ) -> StepCall:
        data: dict[str, Any] = {}
        ref: Optional[str] = None

        for done in store.steps(row.id):
            if done.position >= step.position or done.status != "succeeded":
                continue

            found = OperationResult.of(loads(done.result))

            if found is None:
                continue

            data.update(
                {k: v for k, v in found.data.items() if k not in ("state", "skipped")}
            )
            ref = found.external_ref or ref

        return StepCall(
            deployment_id=row.id,
            target=row.target,
            stage=row.stage or "",
            version=row.version,
            strategy=row.strategy or "recreate",
            config=loads(row.strategy_config, {}),
            operation=step.kind,
            kind=step.kind,
            params=loads(step.params, {}),
            position=step.position,
            external_ref=ref,
            data=data,
        )

    def _attempt(self, call: StepCall) -> None:
        with self.database.session() as db:
            step = self._step(db, call)

            if step is not None:
                step.attempts += 1

    @staticmethod
    def _step(db: Any, call: StepCall) -> Optional[DeploymentStep]:
        return next(
            (
                s
                for s in RolloutStore(db).steps(call.deployment_id)
                if s.position == call.position
            ),
            None,
        )

    def _record(
        self, call: StepCall, outcome: OperationResult, payload: dict[str, Any]
    ) -> dict[str, Any]:
        again: Any = False

        with self.database.session() as db:
            store = RolloutStore(db)
            row = store.deployment(call.deployment_id)
            step = self._step(db, call)

            if row is None or step is None:
                return {"deployment": call.deployment_id, "status": "gone"}

            step.result = dumps(outcome.as_dict())

            if outcome.ok and outcome.state == "running":
                again = now() + POLL
            elif outcome.ok and outcome.state != "failed":
                step.status = "skipped" if outcome.data.get("skipped") else "succeeded"
                step.finished_at = now()

                if outcome.data.get("url") and not row.url:
                    row.url = str(outcome.data["url"])

                again = row.status in ADVANCING
            else:
                again = self._failed(store, row, step, outcome)

            status = row.status

        if again is True:
            self.schedule(call.deployment_id, payload)
        elif again:
            self.schedule(call.deployment_id, payload, again)

        return {
            "deployment": call.deployment_id,
            "status": status,
            "step": call.position,
            "kind": call.kind,
            "ok": outcome.ok,
            "detail": outcome.detail,
        }

    def _failed(
        self,
        store: RolloutStore,
        row: Deployment,
        step: DeploymentStep,
        outcome: OperationResult,
    ) -> bool:
        step.status = "failed"
        step.finished_at = now()
        detail = outcome.detail or f"{step.kind} failed"

        if row.status not in ADVANCING:
            return False

        if step.kind == "rollback":
            self._end(store, row, "failure", f"rollback failed: {detail}")

            return False

        if row.status == "rolling_back":
            return True

        safety = validate_safety(loads(row.safety, {}))

        if (
            step.kind == "health"
            and safety["auto_rollback"]
            and "rollback" in loads(row.operations, [])
        ):
            self._rollback(store, row, "health", f"health failed: {detail}")

            return True

        self._end(store, row, "failure", f"{step.kind} failed: {detail}")

        return False

    def _approval(
        self, store: RolloutStore, row: Deployment, step: DeploymentStep
    ) -> dict[str, Any]:
        if step.status != "waiting":
            step.status = "waiting"
            step.started_at = now()

        if row.status != "awaiting_approval":
            row.status = "awaiting_approval"
            store.event(
                row,
                "awaiting_approval",
                f"{row.version} to {row.stage} waits for approval",
            )

        return {"deployment": row.id, "status": row.status, "step": step.position}

    def _pause(self, store: RolloutStore, row: Deployment, step: DeploymentStep) -> Any:
        moment = now()
        seconds = int(loads(step.params, {}).get("seconds") or 0)

        if step.status == "pending":
            step.status = "waiting"
            step.started_at = moment
            step.not_before = moment + timedelta(seconds=seconds)

        if step.not_before is not None and moment < step.not_before:
            return step.not_before

        step.status = "succeeded"
        step.finished_at = moment
        step.result = dumps(OperationResult(True, f"waited {seconds}s").as_dict())

        return None

    def _rollback(
        self,
        store: RolloutStore,
        row: Deployment,
        reason: str,
        detail: str,
        actor: Optional[str] = None,
    ) -> None:
        store.cancel_pending(row.id)
        store.append(row.id, "rollback", {"reason": reason})
        row.status = "rolling_back"
        row.error = detail
        store.event(
            row,
            "rolling_back",
            f"{row.version} to {row.stage} rolls back",
            detail,
            actor,
        )

    def _end(
        self,
        store: RolloutStore,
        row: Deployment,
        status: str,
        error: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> None:
        store.cancel_pending(row.id)
        row.status = status
        row.finished_at = now()

        if error:
            row.error = error[:4000]

        store.event(
            row,
            status,
            f"{row.version} to {row.stage}: {status.replace('_', ' ')}",
            error,
            actor,
        )

    def _finish(self, store: RolloutStore, row: Deployment) -> None:
        if row.status == "rolling_back":
            reason = next(
                (
                    loads(s.params, {}).get("reason")
                    for s in reversed(store.steps(row.id))
                    if s.kind == "rollback"
                ),
                None,
            )
            self._end(store, row, "aborted" if reason == "abort" else "rolled_back")

            return

        row.error = None
        self._end(store, row, "success")

    def state(
        self, app_id: str, deployment_id: str
    ) -> tuple[Deployment, list[DeploymentStep]]:
        with self.database.session() as db:
            store = RolloutStore(db)
            row = store.deployment(deployment_id, app_id)

            if row is None:
                raise NotFound("no deployment with that id")

            steps = store.steps(deployment_id)
            db.expunge_all()

            return row, steps

    def events(self, app_id: str, deployment_id: str) -> list[Any]:
        with self.database.session() as db:
            store = RolloutStore(db)

            if store.deployment(deployment_id, app_id) is None:
                raise NotFound("no deployment with that id")

            found = store.events(deployment_id)
            db.expunge_all()

            return found

    def control(
        self,
        app: Any,
        organization_id: str,
        deployment_id: str,
        action: str,
        user_id: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> dict[str, Any]:
        """promote, pause, resume or abort; the answer says whether a job was queued and, after an abort, what is live."""
        queued = False
        live: Optional[str] = None

        with self.database.session() as db:
            store = RolloutStore(db)
            row = store.deployment(deployment_id, app.id)

            if row is None or not store.steps(deployment_id):
                raise NotFound("no deployment run step by step with that id")

            payload = {
                "path": f"apps/{app.registry_id}/deploy",
                "method": "POST",
                "body": {
                    "stage": row.stage,
                    "version": row.version,
                    "dry_run": False,
                    "strategy": row.strategy,
                },
                "registry_id": app.registry_id,
                "organization_id": organization_id,
                "app_id": app.id,
                "user_id": user_id,
            }

            if row.status in FINISHED:
                raise Conflict(f"the deployment is {row.status.replace('_', ' ')}")

            step = store.current(deployment_id)

            if action == "promote":
                queued = self._promote(store, row, step, actor)
            elif action == "pause":
                if row.status not in ("running", "awaiting_approval"):
                    raise Conflict(f"the deployment is {row.status.replace('_', ' ')}")

                row.status = "paused"
                store.event(
                    row, "paused", f"{row.version} to {row.stage} paused", None, actor
                )
            elif action == "resume":
                if row.status != "paused":
                    raise Conflict("the deployment is not paused")

                row.status = "running"
                store.event(
                    row, "resumed", f"{row.version} to {row.stage} resumed", None, actor
                )
                queued = True
            elif action == "abort":
                if row.status == "rolling_back":
                    raise Conflict("the deployment is already rolling back")

                steps = store.steps(deployment_id)
                touched = any(
                    s.kind in DEPLOYED and s.status in ("succeeded", "running")
                    for s in steps
                )

                if touched and "rollback" in loads(row.operations, []):
                    self._rollback(store, row, "abort", "aborted", actor)
                    queued = True
                else:
                    live = live_of(steps)
                    self._end(store, row, "aborted", f"aborted; {live}", actor)
            else:
                raise Invalid(f"no action {action!r}")

            status = row.status

        if queued:
            self.schedule(deployment_id, payload)

        return {"status": status, "queued": queued, "live": live}

    def _promote(
        self,
        store: RolloutStore,
        row: Deployment,
        step: Optional[DeploymentStep],
        actor: Optional[str],
    ) -> bool:
        if row.status == "paused":
            raise Conflict("the deployment is paused; resume it first")

        if step is None or step.status != "waiting":
            raise Conflict(
                "nothing to promote: the current step is "
                + (f"{step.kind} ({step.status})" if step else "none")
            )

        moment = now()
        step.finished_at = moment

        if step.kind == "approval":
            step.status = "succeeded"
            step.result = dumps(
                OperationResult(True, f"approved by {actor or 'someone'}").as_dict()
            )
            row.status = "running"
            store.event(
                row, "approved", f"{row.version} to {row.stage} approved", None, actor
            )
        else:
            step.status = "skipped"
            step.result = dumps(
                OperationResult(True, f"skipped by {actor or 'someone'}").as_dict()
            )
            store.event(
                row,
                "promoted",
                f"{row.version} to {row.stage}: wait skipped",
                None,
                actor,
            )

        return True


def _as(call: StepCall, operation: str) -> StepCall:
    return StepCall(**{**call.__dict__, "operation": operation})


def plan_of(
    target: Any, strategy: str, config: Optional[dict], safety: Optional[dict]
) -> tuple[list[StepSpec], list[str]]:
    """The steps a target runs for `strategy` and the operations it offers, refused when it cannot."""
    ops = operations_of(target)

    return plan_for(target, strategy_of(strategy).id, config, safety), sorted(
        set(ops.supports()) if ops is not None else set()
    )
