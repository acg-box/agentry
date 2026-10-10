#!/usr/bin/env python3
"""Analyze a normalized automation portfolio without changing external state."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


INPUT_SCHEMA = "helixbox/automation-portfolio-snapshot/1"
RESULT_SCHEMA = "helixbox/automation-portfolio-analysis/1"
EVIDENCE_LABELS = {"observed", "declared", "inferred", "unknown"}
STATUSES = {"active", "paused", "unknown"}
ARRIVAL_POLICIES = {
    "skip",
    "coalesce",
    "queue",
    "replace",
    "parallel",
    "not-applicable",
}
TASK_EVIDENCE_FIELDS = {
    "identity",
    "status",
    "dependencies",
    "writes",
    "occurrences",
    "arrivalPolicy",
}
MAX_INPUT_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_MEMBERS = 25
MAX_MEMBER_LIMIT = 1000


class ContractError(ValueError):
    """Report invalid normalized input."""


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{path} must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{path} must be an array")
    return value


def _exact_keys(
    value: dict[str, Any],
    path: str,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        raise ContractError(f"{path} is missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ContractError(f"{path} has unknown fields: {', '.join(sorted(unknown))}")


def _text(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise ContractError(f"{path} must be a non-empty string without outer whitespace")
    return value


def _string_list(value: Any, path: str, *, allow_empty: bool = True) -> list[str]:
    items = _list(value, path)
    if not items and not allow_empty:
        raise ContractError(f"{path} must not be empty")
    result = [_text(item, f"{path}[{index}]") for index, item in enumerate(items)]
    if len(result) != len(set(result)):
        raise ContractError(f"{path} must not contain duplicates")
    return sorted(result)


def _evidence(value: Any, path: str) -> str:
    if value not in EVIDENCE_LABELS:
        raise ContractError(
            f"{path} must be one of: {', '.join(sorted(EVIDENCE_LABELS))}"
        )
    return str(value)


def _optional_bool(value: Any, path: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ContractError(f"{path} must be true, false, or null")


def _positive_int(value: Any, path: str, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ContractError(f"{path} must be a positive integer")
    return value


def _epoch(value: Any, path: str, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{path} must be an integer epoch second")
    return value


def _sample(values: Iterable[str], maximum: int) -> dict[str, Any]:
    ordered = sorted(set(values))
    return {
        "count": len(ordered),
        "sample": ordered[:maximum],
        "sampleTruncated": len(ordered) > maximum,
    }


def _evidence_counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    return {label: counts[label] for label in sorted(counts)}


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _normalize(snapshot: Any) -> dict[str, Any]:
    root = _object(snapshot, "snapshot")
    _exact_keys(
        root,
        "snapshot",
        {"schema", "coverage", "capacityGroups", "resourcePolicies", "tasks"},
    )
    if root["schema"] != INPUT_SCHEMA:
        raise ContractError(f"snapshot.schema must be {INPUT_SCHEMA}")

    coverage = _object(root["coverage"], "snapshot.coverage")
    _exact_keys(
        coverage,
        "snapshot.coverage",
        {
            "kind",
            "observedAt",
            "sources",
            "excludedSurfaces",
            "completeListContract",
        },
    )
    kind = coverage["kind"]
    if kind not in {"complete", "scoped"}:
        raise ContractError("snapshot.coverage.kind must be complete or scoped")
    observed_at = _text(coverage["observedAt"], "snapshot.coverage.observedAt")
    sources = _string_list(
        coverage["sources"], "snapshot.coverage.sources", allow_empty=False
    )
    excluded = _string_list(
        coverage["excludedSurfaces"], "snapshot.coverage.excludedSurfaces"
    )
    complete_contract = _text(
        coverage["completeListContract"],
        "snapshot.coverage.completeListContract",
        nullable=True,
    )
    if kind == "complete" and complete_contract is None:
        raise ContractError(
            "complete coverage requires snapshot.coverage.completeListContract"
        )

    capacity_groups: dict[str, dict[str, Any]] = {}
    for index, raw_group in enumerate(
        _list(root["capacityGroups"], "snapshot.capacityGroups")
    ):
        path = f"snapshot.capacityGroups[{index}]"
        group = _object(raw_group, path)
        _exact_keys(group, path, {"id", "limit", "evidence"})
        group_id = _text(group["id"], f"{path}.id")
        if group_id in capacity_groups:
            raise ContractError(f"duplicate capacity group: {group_id}")
        capacity_groups[group_id] = {
            "id": group_id,
            "limit": _positive_int(group["limit"], f"{path}.limit", nullable=True),
            "evidence": _evidence(group["evidence"], f"{path}.evidence"),
        }

    resource_policies: dict[str, dict[str, Any]] = {}
    for index, raw_policy in enumerate(
        _list(root["resourcePolicies"], "snapshot.resourcePolicies")
    ):
        path = f"snapshot.resourcePolicies[{index}]"
        policy = _object(raw_policy, path)
        _exact_keys(
            policy,
            path,
            {
                "resource",
                "idempotencyBoundary",
                "enforceableOwnership",
                "evidence",
            },
        )
        resource = _text(policy["resource"], f"{path}.resource")
        if resource in resource_policies:
            raise ContractError(f"duplicate resource policy: {resource}")
        resource_policies[resource] = {
            "resource": resource,
            "idempotencyBoundary": _optional_bool(
                policy["idempotencyBoundary"], f"{path}.idempotencyBoundary"
            ),
            "enforceableOwnership": _optional_bool(
                policy["enforceableOwnership"], f"{path}.enforceableOwnership"
            ),
            "evidence": _evidence(policy["evidence"], f"{path}.evidence"),
        }

    tasks: list[dict[str, Any]] = []
    task_ids: set[str] = set()
    for index, raw_task in enumerate(_list(root["tasks"], "snapshot.tasks")):
        path = f"snapshot.tasks[{index}]"
        task = _object(raw_task, path)
        _exact_keys(
            task,
            path,
            {
                "id",
                "status",
                "dependencies",
                "writes",
                "occurrences",
                "arrivalPolicy",
                "evidence",
            },
        )
        task_id = _text(task["id"], f"{path}.id")
        if task_id in task_ids:
            raise ContractError(f"duplicate task ID: {task_id}")
        task_ids.add(task_id)

        status = task["status"]
        if status not in STATUSES:
            raise ContractError(
                f"{path}.status must be one of: {', '.join(sorted(STATUSES))}"
            )
        arrival_policy = task["arrivalPolicy"]
        if arrival_policy is not None and arrival_policy not in ARRIVAL_POLICIES:
            raise ContractError(
                f"{path}.arrivalPolicy must be null or one of: "
                f"{', '.join(sorted(ARRIVAL_POLICIES))}"
            )

        raw_evidence = _object(task["evidence"], f"{path}.evidence")
        _exact_keys(raw_evidence, f"{path}.evidence", TASK_EVIDENCE_FIELDS)
        task_evidence = {
            field: _evidence(raw_evidence[field], f"{path}.evidence.{field}")
            for field in sorted(TASK_EVIDENCE_FIELDS)
        }

        dependencies: list[dict[str, Any]] | None = None
        if task["dependencies"] is not None:
            dependencies = []
            dependency_ids: set[str] = set()
            for dependency_index, raw_dependency in enumerate(
                _list(task["dependencies"], f"{path}.dependencies")
            ):
                dependency_path = f"{path}.dependencies[{dependency_index}]"
                dependency = _object(raw_dependency, dependency_path)
                _exact_keys(
                    dependency,
                    dependency_path,
                    {"producerId", "external", "evidence"},
                    {"reason", "confidence"},
                )
                producer_id = _text(
                    dependency["producerId"], f"{dependency_path}.producerId"
                )
                external = dependency["external"]
                if not isinstance(external, bool):
                    raise ContractError(f"{dependency_path}.external must be boolean")
                if producer_id in dependency_ids:
                    raise ContractError(
                        f"duplicate dependency for {task_id}: {producer_id}"
                    )
                dependency_ids.add(producer_id)
                evidence = _evidence(
                    dependency["evidence"], f"{dependency_path}.evidence"
                )
                reason = _text(
                    dependency.get("reason"),
                    f"{dependency_path}.reason",
                    nullable=True,
                )
                confidence = dependency.get("confidence")
                if confidence is not None and (
                    isinstance(confidence, bool)
                    or not isinstance(confidence, (int, float))
                    or not 0 <= confidence <= 1
                ):
                    raise ContractError(
                        f"{dependency_path}.confidence must be a number from 0 to 1"
                    )
                if evidence == "inferred" and (reason is None or confidence is None):
                    raise ContractError(
                        f"{dependency_path} inferred evidence requires reason and confidence"
                    )
                dependencies.append(
                    {
                        "producerId": producer_id,
                        "external": external,
                        "evidence": evidence,
                        "reason": reason,
                        "confidence": confidence,
                    }
                )
            dependencies.sort(key=lambda item: (item["producerId"], item["external"]))

        writes: list[dict[str, Any]] | None = None
        if task["writes"] is not None:
            writes = []
            resources: set[str] = set()
            for write_index, raw_write in enumerate(
                _list(task["writes"], f"{path}.writes")
            ):
                write_path = f"{path}.writes[{write_index}]"
                write = _object(raw_write, write_path)
                _exact_keys(
                    write,
                    write_path,
                    {"resource", "evidence"},
                    {"reason", "confidence"},
                )
                resource = _text(write["resource"], f"{write_path}.resource")
                if resource in resources:
                    raise ContractError(f"duplicate write for {task_id}: {resource}")
                resources.add(resource)
                evidence = _evidence(
                    write["evidence"], f"{write_path}.evidence"
                )
                reason = _text(
                    write.get("reason"), f"{write_path}.reason", nullable=True
                )
                confidence = write.get("confidence")
                if confidence is not None and (
                    isinstance(confidence, bool)
                    or not isinstance(confidence, (int, float))
                    or not 0 <= confidence <= 1
                ):
                    raise ContractError(
                        f"{write_path}.confidence must be a number from 0 to 1"
                    )
                if evidence == "inferred" and (reason is None or confidence is None):
                    raise ContractError(
                        f"{write_path} inferred evidence requires reason and confidence"
                    )
                writes.append(
                    {
                        "resource": resource,
                        "evidence": evidence,
                        "reason": reason,
                        "confidence": confidence,
                    }
                )
            writes.sort(key=lambda item: item["resource"])

        occurrences: list[dict[str, Any]] | None = None
        if task["occurrences"] is not None:
            occurrences = []
            for occurrence_index, raw_occurrence in enumerate(
                _list(task["occurrences"], f"{path}.occurrences")
            ):
                occurrence_path = f"{path}.occurrences[{occurrence_index}]"
                occurrence = _object(raw_occurrence, occurrence_path)
                _exact_keys(
                    occurrence,
                    occurrence_path,
                    {
                        "capacityGroup",
                        "startEpochSeconds",
                        "endEpochSeconds",
                        "units",
                        "evidence",
                    },
                )
                start = _epoch(
                    occurrence["startEpochSeconds"],
                    f"{occurrence_path}.startEpochSeconds",
                )
                end = _epoch(
                    occurrence["endEpochSeconds"],
                    f"{occurrence_path}.endEpochSeconds",
                    nullable=True,
                )
                if end is not None and end <= start:
                    raise ContractError(
                        f"{occurrence_path}.endEpochSeconds must be greater than its start"
                    )
                occurrences.append(
                    {
                        "capacityGroup": _text(
                            occurrence["capacityGroup"],
                            f"{occurrence_path}.capacityGroup",
                        ),
                        "startEpochSeconds": start,
                        "endEpochSeconds": end,
                        "units": _positive_int(
                            occurrence["units"], f"{occurrence_path}.units"
                        ),
                        "evidence": _evidence(
                            occurrence["evidence"], f"{occurrence_path}.evidence"
                        ),
                    }
                )
            occurrences.sort(
                key=lambda item: (
                    item["capacityGroup"],
                    item["startEpochSeconds"],
                    item["endEpochSeconds"] is None,
                    item["endEpochSeconds"] or 0,
                    item["units"],
                    item["evidence"],
                )
            )

        if status == "unknown" and task_evidence["status"] != "unknown":
            raise ContractError(f"{path}.status unknown requires unknown status evidence")
        for field, value in (
            ("dependencies", dependencies),
            ("writes", writes),
            ("occurrences", occurrences),
            ("arrivalPolicy", arrival_policy),
        ):
            if value is None and task_evidence[field] != "unknown":
                raise ContractError(
                    f"{path}.{field} null requires unknown {field} evidence"
                )

        tasks.append(
            {
                "id": task_id,
                "status": status,
                "dependencies": dependencies,
                "writes": writes,
                "occurrences": occurrences,
                "arrivalPolicy": arrival_policy,
                "evidence": task_evidence,
            }
        )

    tasks.sort(key=lambda item: item["id"])
    for task in tasks:
        for dependency in task["dependencies"] or []:
            if dependency["external"] and dependency["producerId"] in task_ids:
                raise ContractError(
                    f"dependency for {task['id']} marks in-snapshot producer "
                    f"{dependency['producerId']} as external"
                )
    return {
        "schema": INPUT_SCHEMA,
        "coverage": {
            "kind": kind,
            "observedAt": observed_at,
            "sources": sources,
            "excludedSurfaces": excluded,
            "completeListContract": complete_contract,
        },
        "capacityGroups": capacity_groups,
        "resourcePolicies": resource_policies,
        "tasks": tasks,
    }


def _cyclic_components(
    nodes: list[str], adjacency: dict[str, tuple[str, ...]]
) -> list[list[str]]:
    """Return exact cyclic strongly connected components without recursion."""

    visited: set[str] = set()
    finish: list[str] = []
    for start in nodes:
        if start in visited:
            continue
        visited.add(start)
        stack: list[tuple[str, int]] = [(start, 0)]
        while stack:
            node, index = stack[-1]
            neighbors = adjacency[node]
            if index < len(neighbors):
                neighbor = neighbors[index]
                stack[-1] = (node, index + 1)
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append((neighbor, 0))
                continue
            finish.append(node)
            stack.pop()

    reverse: dict[str, list[str]] = {node: [] for node in nodes}
    for node in nodes:
        for neighbor in adjacency[node]:
            reverse[neighbor].append(node)
    reverse_sorted = {node: tuple(sorted(values)) for node, values in reverse.items()}

    assigned: set[str] = set()
    cyclic: list[list[str]] = []
    for start in reversed(finish):
        if start in assigned:
            continue
        assigned.add(start)
        component: list[str] = []
        stack = [start]
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in reversed(reverse_sorted[node]):
                if neighbor not in assigned:
                    assigned.add(neighbor)
                    stack.append(neighbor)
        component.sort()
        if len(component) > 1 or component[0] in adjacency[component[0]]:
            cyclic.append(component)
    return sorted(cyclic, key=lambda component: tuple(component))


def _capacity_peak(
    events: list[tuple[int, int]], limit: int
) -> tuple[int, int | None, int | None, int]:
    """Return peak, first peak span, and over-limit span count for half-open windows."""

    deltas: dict[int, int] = defaultdict(int)
    for timestamp, delta in events:
        deltas[timestamp] += delta
    times = sorted(deltas)
    current = 0
    peak = 0
    first_peak_start: int | None = None
    first_peak_end: int | None = None
    over_limit_spans = 0
    over_limit_active = False
    for index, timestamp in enumerate(times[:-1]):
        current += deltas[timestamp]
        next_timestamp = times[index + 1]
        if next_timestamp <= timestamp:
            continue
        if current > peak:
            peak = current
            first_peak_start = timestamp
            first_peak_end = next_timestamp
        elif current == peak and peak > 0 and first_peak_end == timestamp:
            first_peak_end = next_timestamp
        if current > limit and not over_limit_active:
            over_limit_spans += 1
        over_limit_active = current > limit
    return peak, first_peak_start, first_peak_end, over_limit_spans


def analyze(snapshot: Any, *, max_members: int = DEFAULT_MAX_MEMBERS) -> dict[str, Any]:
    """Return a deterministic analysis of one normalized snapshot."""

    if not 1 <= max_members <= MAX_MEMBER_LIMIT:
        raise ContractError(
            f"max_members must be between 1 and {MAX_MEMBER_LIMIT}"
        )
    normalized = _normalize(snapshot)
    tasks = normalized["tasks"]
    by_id = {task["id"]: task for task in tasks}
    nodes = sorted(by_id)

    adjacency_lists: dict[str, set[str]] = {task_id: set() for task_id in nodes}
    outside_edges: dict[tuple[str, str], set[str]] = defaultdict(set)
    outside_edge_evidence: dict[tuple[str, str], list[str]] = defaultdict(list)
    paused_edges: dict[str, set[str]] = defaultdict(set)
    paused_edge_evidence: dict[str, list[str]] = defaultdict(list)
    dependency_edges = 0
    internal_dependency_edges = 0
    for task in tasks:
        for dependency in task["dependencies"] or []:
            dependency_edges += 1
            producer_id = dependency["producerId"]
            if dependency["external"]:
                continue
            producer = by_id.get(producer_id)
            if producer is None:
                classification = (
                    "producerMissingFromCompleteInventory"
                    if normalized["coverage"]["kind"] == "complete"
                    else "producerNotObservedInScope"
                )
                outside_key = (classification, producer_id)
                outside_edges[outside_key].add(task["id"])
                outside_edge_evidence[outside_key].append(dependency["evidence"])
                continue
            adjacency_lists[task["id"]].add(producer_id)
            internal_dependency_edges += 1
            if task["status"] == "active" and producer["status"] == "paused":
                paused_edges[producer_id].add(task["id"])
                paused_edge_evidence[producer_id].append(dependency["evidence"])

    adjacency = {
        task_id: tuple(sorted(dependencies))
        for task_id, dependencies in adjacency_lists.items()
    }
    cycles: list[dict[str, Any]] = []
    for component in _cyclic_components(nodes, adjacency):
        component_ids = set(component)
        edge_evidence = [
            dependency["evidence"]
            for consumer_id in component
            for dependency in (by_id[consumer_id]["dependencies"] or [])
            if not dependency["external"]
            and dependency["producerId"] in component_ids
        ]
        cycles.append(
            {
                "memberTaskIds": _sample(component, max_members),
                "edgeEvidenceCounts": _evidence_counts(edge_evidence),
                "requiresBoundedFeedbackEvidence": True,
            }
        )
    unobserved_producers = [
        {
            "classification": classification,
            "producerId": producer_id,
            "consumerTaskIds": _sample(consumers, max_members),
            "edgeEvidenceCounts": _evidence_counts(
                outside_edge_evidence[(classification, producer_id)]
            ),
        }
        for (classification, producer_id), consumers in sorted(outside_edges.items())
    ]
    paused_producers = [
        {
            "producerId": producer_id,
            "consumerTaskIds": _sample(consumers, max_members),
            "edgeEvidenceCounts": _evidence_counts(
                paused_edge_evidence[producer_id]
            ),
            "requiresFreshnessEvidence": True,
        }
        for producer_id, consumers in sorted(paused_edges.items())
    ]

    writers: dict[str, set[str]] = defaultdict(set)
    writer_evidence: dict[str, list[str]] = defaultdict(list)
    resource_write_refs = 0
    for task in tasks:
        for write in task["writes"] or []:
            resource_write_refs += 1
            if task["status"] == "active":
                writers[write["resource"]].add(task["id"])
                writer_evidence[write["resource"]].append(write["evidence"])
    shared_writer_risks: list[dict[str, Any]] = []
    for resource, task_ids in sorted(writers.items()):
        if len(task_ids) < 2:
            continue
        policy = normalized["resourcePolicies"].get(resource)
        controlled = bool(
            policy
            and policy["idempotencyBoundary"] is True
            and policy["enforceableOwnership"] is True
            and policy["evidence"] in {"observed", "declared"}
        )
        if controlled:
            continue
        if policy is None:
            policy_state = "missing"
            policy_evidence = "unknown"
        elif (
            policy["idempotencyBoundary"] is None
            or policy["enforceableOwnership"] is None
            or policy["evidence"] in {"inferred", "unknown"}
        ):
            policy_state = "unknown"
            policy_evidence = policy["evidence"]
        else:
            policy_state = "uncontrolled"
            policy_evidence = policy["evidence"]
        shared_writer_risks.append(
            {
                "resource": resource,
                "writerTaskIds": _sample(task_ids, max_members),
                "writeEvidenceCounts": _evidence_counts(
                    writer_evidence[resource]
                ),
                "policyState": policy_state,
                "policyEvidence": policy_evidence,
            }
        )

    occurrences = 0
    known_runtime_occurrences = 0
    start_groups: dict[tuple[str, int], list[tuple[str, int, str]]] = defaultdict(list)
    capacity_events: dict[str, list[tuple[int, int]]] = defaultdict(list)
    capacity_event_evidence: dict[str, list[str]] = defaultdict(list)
    undefined_capacity_groups: dict[str, set[str]] = defaultdict(set)
    evidence_groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    for task in tasks:
        task_values = {
            "identity": task["id"],
            "status": task["status"],
            "dependencies": task["dependencies"],
            "writes": task["writes"],
            "occurrences": task["occurrences"],
            "arrivalPolicy": task["arrivalPolicy"],
        }
        for field, evidence in task["evidence"].items():
            value = task_values[field]
            if evidence == "unknown" or value is None:
                evidence_groups[("task", field)].add(task["id"])
        for dependency_index, dependency in enumerate(task["dependencies"] or []):
            if dependency["evidence"] == "unknown":
                evidence_groups[("dependency", "evidence")].add(
                    f"{task['id']}#{dependency_index}"
                )
        for write_index, write in enumerate(task["writes"] or []):
            if write["evidence"] == "unknown":
                evidence_groups[("write", "evidence")].add(
                    f"{task['id']}#{write_index}"
                )
        for occurrence_index, occurrence in enumerate(task["occurrences"] or []):
            occurrences += 1
            occurrence_id = f"{task['id']}#{occurrence_index}"
            if occurrence["evidence"] == "unknown":
                evidence_groups[("occurrence", "evidence")].add(occurrence_id)
            if occurrence["capacityGroup"] not in normalized["capacityGroups"]:
                undefined_capacity_groups[occurrence["capacityGroup"]].add(task["id"])
            if occurrence["endEpochSeconds"] is None:
                evidence_groups[("occurrence", "endEpochSeconds")].add(occurrence_id)
            else:
                known_runtime_occurrences += 1
            if task["status"] != "active":
                continue
            start_groups[
                (occurrence["capacityGroup"], occurrence["startEpochSeconds"])
            ].append((task["id"], occurrence["units"], occurrence["evidence"]))
            if occurrence["endEpochSeconds"] is not None:
                capacity_events[occurrence["capacityGroup"]].extend(
                    [
                        (occurrence["startEpochSeconds"], occurrence["units"]),
                        (occurrence["endEpochSeconds"], -occurrence["units"]),
                    ]
                )
                capacity_event_evidence[occurrence["capacityGroup"]].append(
                    occurrence["evidence"]
                )

    start_clusters: list[dict[str, Any]] = []
    for (group_id, start), members in sorted(start_groups.items()):
        if len(members) < 2:
            continue
        task_ids = [task_id for task_id, _units, _evidence in members]
        start_clusters.append(
            {
                "capacityGroup": group_id,
                "startEpochSeconds": start,
                "occurrenceCount": len(members),
                "scheduledUnits": sum(
                    units for _task_id, units, _evidence in members
                ),
                "taskIds": _sample(task_ids, max_members),
                "occurrenceEvidenceCounts": _evidence_counts(
                    evidence for _task_id, _units, evidence in members
                ),
                "classification": "possibleCapacityWindow",
            }
        )

    capacity_risks: list[dict[str, Any]] = []
    schedule_events = 0
    for group_id, events in sorted(capacity_events.items()):
        schedule_events += len(events)
        group = normalized["capacityGroups"].get(group_id)
        if group is None or group["limit"] is None:
            continue
        peak, first_start, first_end, over_limit_spans = _capacity_peak(
            events, group["limit"]
        )
        if peak <= group["limit"]:
            continue
        capacity_risks.append(
            {
                "capacityGroup": group_id,
                "limit": group["limit"],
                "limitEvidence": group["evidence"],
                "peakScheduledUnits": peak,
                "firstPeakStartEpochSeconds": first_start,
                "firstPeakEndEpochSeconds": first_end,
                "overLimitSpanCount": over_limit_spans,
                "occurrenceEvidenceCounts": _evidence_counts(
                    capacity_event_evidence[group_id]
                ),
                "classification": "normalizedWindowCapacityExceeded",
            }
        )

    for group_id, group in sorted(normalized["capacityGroups"].items()):
        if group["limit"] is None or group["evidence"] == "unknown":
            evidence_groups[("capacityGroup", "limit")].add(group_id)
    for resource, policy in sorted(normalized["resourcePolicies"].items()):
        if (
            policy["idempotencyBoundary"] is None
            or policy["enforceableOwnership"] is None
            or policy["evidence"] == "unknown"
        ):
            evidence_groups[("resourcePolicy", "control")].add(resource)
    for group_id, task_ids in sorted(undefined_capacity_groups.items()):
        evidence_groups[("occurrence", "capacityGroupDefinition")].update(
            f"{group_id}:{task_id}" for task_id in task_ids
        )

    evidence_gaps = [
        {
            "subject": subject,
            "field": field,
            "subjectIds": _sample(subject_ids, max_members),
        }
        for (subject, field), subject_ids in sorted(evidence_groups.items())
    ]

    finding_count = sum(
        len(items)
        for items in (
            cycles,
            unobserved_producers,
            paused_producers,
            shared_writer_risks,
            start_clusters,
            capacity_risks,
            evidence_gaps,
        )
    )
    return {
        "schema": RESULT_SCHEMA,
        "coverage": normalized["coverage"],
        "claimBoundary": {
            "label": "normalizedSnapshotAnalysisOnly",
            "globalConflictFreeClaimAllowed": False,
            "schedulerSemanticsVerified": False,
            "liveMutationVerified": False,
        },
        "summary": {
            "tasks": len(tasks),
            "activeTasks": sum(task["status"] == "active" for task in tasks),
            "findingGroups": finding_count,
        },
        "findings": {
            "dependencyCycles": cycles,
            "dependencyEdgesOutsideSnapshot": unobserved_producers,
            "pausedProducerEdges": paused_producers,
            "sharedWriterRisks": shared_writer_risks,
            "startClusters": start_clusters,
            "capacityRisks": capacity_risks,
            "evidenceGaps": evidence_gaps,
        },
        "work": {
            "tasks": len(tasks),
            "dependencyEdges": dependency_edges,
            "internalDependencyEdges": internal_dependency_edges,
            "resourceWriteReferences": resource_write_refs,
            "occurrences": occurrences,
            "knownRuntimeOccurrences": known_runtime_occurrences,
            "scheduleEvents": schedule_events,
        },
    }


def _read_input(path: str) -> Any:
    if path == "-":
        payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        candidate = Path(path)
        if candidate.is_symlink():
            raise ContractError("input path must not be a symlink")
        if not candidate.is_file():
            raise ContractError("input path must be a regular file")
        if candidate.stat().st_size > MAX_INPUT_BYTES:
            raise ContractError(f"input exceeds {MAX_INPUT_BYTES} bytes")
        payload = candidate.read_bytes()
    if len(payload) > MAX_INPUT_BYTES:
        raise ContractError(f"input exceeds {MAX_INPUT_BYTES} bytes")
    try:
        return json.loads(payload, object_pairs_hook=_unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"input is not valid UTF-8 JSON: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a normalized Codex automation portfolio read-only."
    )
    parser.add_argument("input", nargs="?", default="-", help="JSON file or - for stdin")
    parser.add_argument(
        "--max-members",
        type=int,
        default=DEFAULT_MAX_MEMBERS,
        help=f"maximum sampled members per grouped finding (1-{MAX_MEMBER_LIMIT})",
    )
    args = parser.parse_args(argv)
    try:
        result = analyze(_read_input(args.input), max_members=args.max_members)
    except (ContractError, OSError) as error:
        print(f"audit_portfolio: {error}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
