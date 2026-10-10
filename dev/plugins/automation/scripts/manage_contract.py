#!/usr/bin/env python3
"""Deterministic management-contract harness for Automation tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any


CREATE_FIELDS = {
    "name",
    "prompt",
    "project",
    "schedule",
    "notification",
    "metadata",
}
TASK_FIELDS = CREATE_FIELDS | {"stable_id", "status", "revision"}
TERMINAL_RUN_STATES = {"succeeded", "failed", "cancelled"}


class ContractViolation(ValueError):
    """Report a lifecycle operation that fails the management contract."""


class Quiescence(str, Enum):
    """Represent only the run-state conclusions that evidence can support."""

    QUIESCENT = "known_quiescent"
    ACTIVE = "known_active"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MutationAuthority:
    """Authorize exact actions and exact targets in one synthetic project."""

    project: str
    actions: frozenset[str]
    create_names: frozenset[str] = frozenset()
    task_ids: frozenset[str] = frozenset()

    def require(self, action: str, project: str, target: str) -> None:
        if project != self.project or action not in self.actions:
            raise ContractViolation("missing explicit mutation authority")
        allowed_targets = self.create_names if action == "create" else self.task_ids
        if target not in allowed_targets:
            raise ContractViolation("mutation authority does not match the exact target")


class InMemoryAutomationControlPlane:
    """Model the public lifecycle contract without calling a real scheduler."""

    def __init__(self, *, run_state_supported: bool = True) -> None:
        self.run_state_supported = run_state_supported
        self._tasks: dict[str, dict[str, Any]] = {}
        self._runs: dict[str, dict[str, Any]] = {}
        self._next_task = 1
        self._next_run = 1

    @staticmethod
    def _require_authority(
        authority: MutationAuthority | None,
        action: str,
        project: str,
        target: str,
    ) -> None:
        if authority is None:
            raise ContractViolation("missing explicit mutation authority")
        authority.require(action, project, target)

    @staticmethod
    def _require_exact_fields(value: dict[str, Any], expected: set[str]) -> None:
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ContractViolation(
                f"full definition required; missing={missing}; extra={extra}"
            )

    def create_paused(
        self,
        definition: dict[str, Any],
        *,
        authority: MutationAuthority | None,
    ) -> dict[str, Any]:
        """Create one exact synthetic task in the paused state."""

        self._require_exact_fields(definition, CREATE_FIELDS)
        project = definition["project"]
        name = definition["name"]
        if not isinstance(project, str) or not project:
            raise ContractViolation("project must be a non-empty string")
        if not isinstance(name, str) or not name:
            raise ContractViolation("name must be a non-empty string")
        self._require_authority(authority, "create", project, name)
        if any(
            task["project"] == project and task["name"] == name
            for task in self._tasks.values()
        ):
            raise ContractViolation("duplicate automation")

        stable_id = f"task-{self._next_task:04d}"
        self._next_task += 1
        task = deepcopy(definition)
        task.update({"stable_id": stable_id, "status": "paused", "revision": 1})
        self._tasks[stable_id] = task
        return deepcopy(task)

    def view(self, stable_id: str) -> dict[str, Any]:
        """Return a full readback for one stable ID."""

        task = self._tasks.get(stable_id)
        if task is None:
            raise ContractViolation("unknown stable task ID")
        return deepcopy(task)

    def update_full(
        self,
        definition: dict[str, Any],
        *,
        authority: MutationAuthority | None,
        requested_changes: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply only the requested changes through one full-definition update."""

        self._require_exact_fields(definition, TASK_FIELDS)
        stable_id = definition["stable_id"]
        current = self._tasks.get(stable_id)
        if current is None:
            raise ContractViolation("unknown stable task ID")
        self._require_authority(
            authority, "update", current["project"], current["stable_id"]
        )
        if definition["revision"] != current["revision"]:
            raise ContractViolation("stale task revision")
        if definition["project"] != current["project"]:
            raise ContractViolation("project cannot change during update")
        if definition["status"] != current["status"]:
            raise ContractViolation("use the lifecycle action to change status")
        if not isinstance(requested_changes, dict) or not requested_changes:
            raise ContractViolation("exact requested changes are required")
        immutable = {"stable_id", "project", "status", "revision"}
        if set(requested_changes) - (TASK_FIELDS - immutable):
            raise ContractViolation("requested change targets an immutable or unknown field")
        for field in TASK_FIELDS - immutable:
            if field in requested_changes:
                if definition[field] != requested_changes[field]:
                    raise ContractViolation("full definition differs from the requested change")
            elif definition[field] != current[field]:
                raise ContractViolation("full update lost an unchanged field")
        if not isinstance(definition["name"], str) or not definition["name"]:
            raise ContractViolation("name must be a non-empty string")
        if any(
            task_id != stable_id
            and task["project"] == current["project"]
            and task["name"] == definition["name"]
            for task_id, task in self._tasks.items()
        ):
            raise ContractViolation("duplicate automation")

        updated = deepcopy(definition)
        updated["revision"] = current["revision"] + 1
        self._tasks[stable_id] = updated
        return deepcopy(updated)

    def activate_once(
        self,
        stable_id: str,
        *,
        authority: MutationAuthority | None,
    ) -> dict[str, Any]:
        """Activate one task and return one deterministic running receipt."""

        task = self._tasks.get(stable_id)
        if task is None:
            raise ContractViolation("unknown stable task ID")
        self._require_authority(authority, "activate", task["project"], stable_id)
        if task["status"] != "paused":
            raise ContractViolation("task must be paused before activation")

        task["status"] = "active"
        task["revision"] += 1
        run_id = f"run-{self._next_run:04d}"
        self._next_run += 1
        receipt = {
            "run_id": run_id,
            "task_id": stable_id,
            "task_revision": task["revision"],
            "state": "running",
            "sequence": self._next_run - 1,
        }
        self._runs[run_id] = receipt
        return deepcopy(receipt)

    def pause(
        self,
        stable_id: str,
        *,
        authority: MutationAuthority | None,
    ) -> dict[str, Any]:
        """Pause future activation without changing an active run."""

        task = self._tasks.get(stable_id)
        if task is None:
            raise ContractViolation("unknown stable task ID")
        self._require_authority(authority, "pause", task["project"], stable_id)
        task["status"] = "paused"
        task["revision"] += 1
        return deepcopy(task)

    def complete_run(self, run_id: str, outcome: str) -> dict[str, Any]:
        """Inject a terminal synthetic scheduler observation for a test."""

        if outcome not in TERMINAL_RUN_STATES:
            raise ContractViolation("run outcome must be terminal")
        receipt = self._runs.get(run_id)
        if receipt is None:
            raise ContractViolation("unknown run ID")
        receipt["state"] = outcome
        return deepcopy(receipt)

    def quiescence(self, stable_id: str) -> Quiescence:
        """Classify quiescence from the configured synthetic run surface."""

        if stable_id not in self._tasks:
            raise ContractViolation("unknown stable task ID")
        if not self.run_state_supported:
            return Quiescence.UNKNOWN
        states = [
            run["state"] for run in self._runs.values() if run["task_id"] == stable_id
        ]
        if any(state not in TERMINAL_RUN_STATES for state in states):
            return Quiescence.ACTIVE
        return Quiescence.QUIESCENT

    def delete(
        self,
        stable_id: str,
        *,
        authority: MutationAuthority | None,
        retention_complete: bool,
        consumers_clear: bool,
    ) -> dict[str, str]:
        """Delete an exact paused ID only after a known quiescence gate."""

        task = self._tasks.get(stable_id)
        if task is None:
            raise ContractViolation("unknown stable task ID")
        self._require_authority(authority, "delete", task["project"], stable_id)
        if task["status"] != "paused":
            raise ContractViolation("task must be paused before deletion")
        state = self.quiescence(stable_id)
        if state is not Quiescence.QUIESCENT:
            raise ContractViolation(f"cannot delete while quiescence is {state.value}")
        if retention_complete is not True:
            raise ContractViolation("retention decision is incomplete")
        if consumers_clear is not True:
            raise ContractViolation("consumer dependency check is incomplete")
        del self._tasks[stable_id]
        return {"stable_id": stable_id, "result": "deleted"}


class FencedEffectTarget:
    """Model one atomic, durable target transaction in memory.

    A production target must persist the fencing watermark and idempotency
    record together. The first token stored with an effect is audit data; it is
    not part of the logical idempotency identity.
    """

    def __init__(self) -> None:
        self._last_fence: dict[str, int] = {}
        self._effects: dict[tuple[str, str], tuple[int, str]] = {}

    def write(
        self,
        resource: str,
        *,
        idempotency_key: str,
        fencing_token: int | None,
        value: str,
    ) -> dict[str, Any]:
        if not isinstance(fencing_token, int) or isinstance(fencing_token, bool):
            raise ContractViolation("target rejected an unfenced writer")
        if fencing_token < 0:
            raise ContractViolation("target rejected an invalid fencing token")
        last = self._last_fence.get(resource, -1)
        if fencing_token < last:
            raise ContractViolation("target rejected a stale fencing token")
        if fencing_token > last:
            # Observing a valid newer holder fences every older holder, even if
            # this request later returns an idempotency conflict.
            self._last_fence[resource] = fencing_token
        effect_key = (resource, idempotency_key)
        prior = self._effects.get(effect_key)
        if prior is not None:
            _, prior_value = prior
            if prior_value != value:
                raise ContractViolation("idempotency key conflicts with prior effect")
            return {
                "resource": resource,
                "idempotency_key": idempotency_key,
                "fencing_token": fencing_token,
                "result": "replayed",
            }
        self._effects[effect_key] = (fencing_token, value)
        return {
            "resource": resource,
            "idempotency_key": idempotency_key,
            "fencing_token": fencing_token,
            "result": "committed",
        }
