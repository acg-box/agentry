"""Deterministic and scale checks for the packaged portfolio analyzer."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import random
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).parents[4]
SCRIPT = (
    REPO_ROOT
    / "plugins"
    / "automation"
    / "scripts"
    / "audit_portfolio.py"
)
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("automation_portfolio_analyzer", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load test module: {SCRIPT}")
analyzer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analyzer)


def dependency(
    producer_id: str,
    *,
    external: bool = False,
    evidence: str = "declared",
) -> dict[str, object]:
    value: dict[str, object] = {
        "producerId": producer_id,
        "external": external,
        "evidence": evidence,
    }
    if evidence == "inferred":
        value.update({"reason": "same committed output", "confidence": 0.75})
    return value


def occurrence(
    start: int,
    end: int | None,
    *,
    group: str = "local",
    units: int = 1,
    evidence: str = "declared",
) -> dict[str, object]:
    return {
        "capacityGroup": group,
        "startEpochSeconds": start,
        "endEpochSeconds": end,
        "units": units,
        "evidence": evidence,
    }


def task(
    task_id: str,
    *,
    status: str = "active",
    dependencies: list[dict[str, object]] | None = None,
    writes: list[str] | None = None,
    occurrences: list[dict[str, object]] | None = None,
    arrival_policy: str | None = "coalesce",
    unknown_fields: set[str] | None = None,
) -> dict[str, object]:
    unknown_fields = unknown_fields or set()
    normalized_writes = (
        None
        if writes is None
        else [{"resource": resource, "evidence": "declared"} for resource in writes]
    )
    values: dict[str, object] = {
        "id": task_id,
        "status": status,
        "dependencies": dependencies,
        "writes": normalized_writes,
        "occurrences": occurrences,
        "arrivalPolicy": arrival_policy,
        "evidence": {
            "identity": "observed",
            "status": "unknown" if status == "unknown" else "observed",
            "dependencies": "declared",
            "writes": "declared",
            "occurrences": "declared",
            "arrivalPolicy": "declared",
        },
    }
    evidence = values["evidence"]
    assert isinstance(evidence, dict)
    for field in unknown_fields:
        evidence[field] = "unknown"
    return values


def snapshot(
    tasks: list[dict[str, object]],
    *,
    coverage: str = "scoped",
    capacity_groups: list[dict[str, object]] | None = None,
    resource_policies: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema": analyzer.INPUT_SCHEMA,
        "coverage": {
            "kind": coverage,
            "observedAt": "2026-07-22T12:00:00Z",
            "sources": ["fixture inventory"],
            "excludedSurfaces": [] if coverage == "complete" else ["offline device"],
            "completeListContract": (
                "fixture declares the complete list" if coverage == "complete" else None
            ),
        },
        "capacityGroups": (
            capacity_groups
            if capacity_groups is not None
            else [{"id": "local", "limit": 2, "evidence": "declared"}]
        ),
        "resourcePolicies": resource_policies or [],
        "tasks": tasks,
    }


def cycle_oracle(task_values: list[dict[str, object]]) -> set[tuple[str, ...]]:
    task_ids = [str(value["id"]) for value in task_values]
    index = {task_id: position for position, task_id in enumerate(task_ids)}
    reachable = [[False] * len(task_ids) for _ in task_ids]
    self_edges: set[str] = set()
    for value in task_values:
        consumer = str(value["id"])
        for edge in value["dependencies"] or []:
            producer = str(edge["producerId"])
            if not edge["external"] and producer in index:
                reachable[index[consumer]][index[producer]] = True
                if consumer == producer:
                    self_edges.add(consumer)
    for middle in range(len(task_ids)):
        for source in range(len(task_ids)):
            if not reachable[source][middle]:
                continue
            for target in range(len(task_ids)):
                reachable[source][target] = (
                    reachable[source][target]
                    or reachable[middle][target]
                )
    remaining = set(task_ids)
    result: set[tuple[str, ...]] = set()
    while remaining:
        first = min(remaining)
        component = {
            candidate
            for candidate in remaining
            if reachable[index[first]][index[candidate]]
            and reachable[index[candidate]][index[first]]
        }
        if not component:
            component = {first}
        remaining -= component
        if len(component) > 1 or first in self_edges:
            result.add(tuple(sorted(component)))
    return result


class AutomationPortfolioAnalyzerTests(unittest.TestCase):
    def test_reports_exact_cycles_and_scope_aware_missing_producers(self) -> None:
        values = [
            task("a", dependencies=[dependency("b")], writes=[], occurrences=[]),
            task("b", dependencies=[dependency("a")], writes=[], occurrences=[]),
            task("c", dependencies=[dependency("missing")], writes=[], occurrences=[]),
            task(
                "d",
                dependencies=[dependency("external-service", external=True)],
                writes=[],
                occurrences=[],
            ),
        ]
        scoped = analyzer.analyze(snapshot(values))
        complete = analyzer.analyze(snapshot(values, coverage="complete"))

        self.assertEqual(
            ["a", "b"],
            scoped["findings"]["dependencyCycles"][0]["memberTaskIds"]["sample"],
        )
        self.assertEqual(
            "producerNotObservedInScope",
            scoped["findings"]["dependencyEdgesOutsideSnapshot"][0][
                "classification"
            ],
        )
        self.assertEqual(
            "producerMissingFromCompleteInventory",
            complete["findings"]["dependencyEdgesOutsideSnapshot"][0][
                "classification"
            ],
        )
        self.assertEqual(
            "missing",
            complete["findings"]["dependencyEdgesOutsideSnapshot"][0]["producerId"],
        )

    def test_groups_paused_producers_and_uncontrolled_shared_writers(self) -> None:
        values = [
            task("producer", status="paused", dependencies=[], writes=[], occurrences=[]),
            task(
                "consumer",
                dependencies=[dependency("producer")],
                writes=["unsafe", "safe"],
                occurrences=[],
            ),
            task(
                "peer",
                dependencies=[],
                writes=["unsafe", "safe"],
                occurrences=[],
            ),
        ]
        policies = [
            {
                "resource": "safe",
                "idempotencyBoundary": True,
                "enforceableOwnership": True,
                "evidence": "observed",
            }
        ]

        result = analyzer.analyze(snapshot(values, resource_policies=policies))

        self.assertEqual(
            ["consumer"],
            result["findings"]["pausedProducerEdges"][0]["consumerTaskIds"]["sample"],
        )
        self.assertEqual(
            ["unsafe"],
            [finding["resource"] for finding in result["findings"]["sharedWriterRisks"]],
        )
        self.assertEqual(
            {"declared": 2},
            result["findings"]["sharedWriterRisks"][0]["writeEvidenceCounts"],
        )
        self.assertEqual(
            "missing", result["findings"]["sharedWriterRisks"][0]["policyState"]
        )

        inferred_policies = copy.deepcopy(policies)
        inferred_policies[0]["evidence"] = "inferred"
        inferred_result = analyzer.analyze(
            snapshot(values, resource_policies=inferred_policies)
        )
        inferred_risks = {
            finding["resource"]: finding["policyState"]
            for finding in inferred_result["findings"]["sharedWriterRisks"]
        }
        self.assertEqual({"safe": "unknown", "unsafe": "missing"}, inferred_risks)

    def test_uses_half_open_windows_and_marks_clusters_as_possible(self) -> None:
        values = [
            task("a", dependencies=[], writes=[], occurrences=[occurrence(0, 10)]),
            task("b", dependencies=[], writes=[], occurrences=[occurrence(10, 20)]),
            task("c", dependencies=[], writes=[], occurrences=[occurrence(30, 40)]),
            task("d", dependencies=[], writes=[], occurrences=[occurrence(30, 40)]),
        ]
        groups = [{"id": "local", "limit": 1, "evidence": "declared"}]

        result = analyzer.analyze(snapshot(values, capacity_groups=groups))

        self.assertEqual(1, len(result["findings"]["startClusters"]))
        self.assertEqual(
            "possibleCapacityWindow",
            result["findings"]["startClusters"][0]["classification"],
        )
        self.assertEqual(1, len(result["findings"]["capacityRisks"]))
        risk = result["findings"]["capacityRisks"][0]
        self.assertEqual(2, risk["peakScheduledUnits"])
        self.assertEqual(30, risk["firstPeakStartEpochSeconds"])
        self.assertEqual(40, risk["firstPeakEndEpochSeconds"])

    def test_contiguous_over_limit_segments_form_one_span(self) -> None:
        values = [
            task("a", dependencies=[], writes=[], occurrences=[occurrence(0, 10)]),
            task("b", dependencies=[], writes=[], occurrences=[occurrence(0, 5)]),
            task("c", dependencies=[], writes=[], occurrences=[occurrence(5, 10)]),
        ]
        groups = [{"id": "local", "limit": 1, "evidence": "declared"}]

        result = analyzer.analyze(snapshot(values, capacity_groups=groups))

        risk = result["findings"]["capacityRisks"][0]
        self.assertEqual(1, risk["overLimitSpanCount"])
        self.assertEqual(0, risk["firstPeakStartEpochSeconds"])
        self.assertEqual(10, risk["firstPeakEndEpochSeconds"])

    def test_preserves_unknown_values_as_grouped_evidence_gaps(self) -> None:
        unknown = task(
            "unknown",
            status="unknown",
            dependencies=None,
            writes=None,
            occurrences=None,
            arrival_policy=None,
            unknown_fields={"dependencies", "writes", "occurrences", "arrivalPolicy"},
        )
        runtime_unknown = task(
            "runtime-unknown",
            dependencies=[],
            writes=[],
            occurrences=[occurrence(0, None, evidence="unknown")],
        )
        groups = [{"id": "local", "limit": None, "evidence": "unknown"}]

        result = analyzer.analyze(
            snapshot([unknown, runtime_unknown], capacity_groups=groups)
        )
        gaps = {
            (gap["subject"], gap["field"]): gap["subjectIds"]["count"]
            for gap in result["findings"]["evidenceGaps"]
        }

        self.assertEqual(1, gaps[("task", "dependencies")])
        self.assertEqual(1, gaps[("task", "arrivalPolicy")])
        self.assertEqual(1, gaps[("occurrence", "endEpochSeconds")])
        self.assertEqual(1, gaps[("capacityGroup", "limit")])
        self.assertFalse(result["claimBoundary"]["globalConflictFreeClaimAllowed"])

    def test_rejects_ambiguous_or_malformed_normalized_input(self) -> None:
        duplicate = snapshot(
            [
                task("same", dependencies=[], writes=[], occurrences=[]),
                task("same", dependencies=[], writes=[], occurrences=[]),
            ]
        )
        with self.assertRaisesRegex(analyzer.ContractError, "duplicate task ID"):
            analyzer.analyze(duplicate)

        inferred = snapshot(
            [
                task(
                    "a",
                    dependencies=[
                        {
                            "producerId": "b",
                            "external": False,
                            "evidence": "inferred",
                        }
                    ],
                    writes=[],
                    occurrences=[],
                )
            ]
        )
        with self.assertRaisesRegex(analyzer.ContractError, "requires reason and confidence"):
            analyzer.analyze(inferred)

        inferred_write = snapshot(
            [task("a", dependencies=[], writes=["resource"], occurrences=[])]
        )
        inferred_write["tasks"][0]["writes"][0]["evidence"] = "inferred"
        with self.assertRaisesRegex(analyzer.ContractError, "requires reason and confidence"):
            analyzer.analyze(inferred_write)

        unknown_field = snapshot(
            [task("a", dependencies=[], writes=[], occurrences=[])]
        )
        unknown_field["tasks"][0]["guess"] = True
        with self.assertRaisesRegex(analyzer.ContractError, "unknown fields: guess"):
            analyzer.analyze(unknown_field)

        external_in_snapshot = snapshot(
            [
                task(
                    "a",
                    dependencies=[dependency("b", external=True)],
                    writes=[],
                    occurrences=[],
                ),
                task("b", dependencies=[], writes=[], occurrences=[]),
            ]
        )
        with self.assertRaisesRegex(analyzer.ContractError, "in-snapshot producer b"):
            analyzer.analyze(external_in_snapshot)

        ambiguous_dependency = snapshot(
            [
                task(
                    "a",
                    dependencies=[dependency("b"), dependency("b", external=True)],
                    writes=[],
                    occurrences=[],
                )
            ]
        )
        with self.assertRaisesRegex(analyzer.ContractError, "duplicate dependency"):
            analyzer.analyze(ambiguous_dependency)

    def test_fixed_seed_differential_oracles_match_small_portfolios(self) -> None:
        generator = random.Random(41873)
        for repetition in range(80):
            size = generator.randint(2, 8)
            task_ids = [f"t{index}" for index in range(size)]
            policies: list[dict[str, object]] = []
            policy_safe: dict[str, bool] = {}
            for resource in ("r0", "r1", "r2"):
                safe = generator.choice([True, False])
                policy_safe[resource] = safe
                policies.append(
                    {
                        "resource": resource,
                        "idempotencyBoundary": safe,
                        "enforceableOwnership": safe,
                        "evidence": "declared",
                    }
                )
            values: list[dict[str, object]] = []
            expected_writers: dict[str, set[str]] = {resource: set() for resource in policy_safe}
            brute_peak = 0
            for task_id in task_ids:
                edges = [
                    dependency(producer)
                    for producer in task_ids
                    if generator.random() < 0.18
                ]
                writes = [
                    resource
                    for resource in policy_safe
                    if generator.random() < 0.35
                ]
                for resource in writes:
                    expected_writers[resource].add(task_id)
                start = generator.randint(0, 8)
                end = start + generator.randint(1, 5)
                units = generator.randint(1, 2)
                values.append(
                    task(
                        task_id,
                        dependencies=edges,
                        writes=writes,
                        occurrences=[occurrence(start, end, units=units)],
                    )
                )
            for second in range(14):
                units = 0
                for value in values:
                    for item in value["occurrences"]:
                        if item["startEpochSeconds"] <= second < item["endEpochSeconds"]:
                            units += item["units"]
                brute_peak = max(brute_peak, units)
            limit = generator.randint(1, 5)

            result = analyzer.analyze(
                snapshot(
                    values,
                    capacity_groups=[
                        {"id": "local", "limit": limit, "evidence": "declared"}
                    ],
                    resource_policies=policies,
                )
            )
            actual_cycles = {
                tuple(item["memberTaskIds"]["sample"])
                for item in result["findings"]["dependencyCycles"]
            }
            expected_unsafe = {
                resource
                for resource, writers in expected_writers.items()
                if len(writers) >= 2 and not policy_safe[resource]
            }
            actual_unsafe = {
                item["resource"]
                for item in result["findings"]["sharedWriterRisks"]
            }
            actual_peak = (
                result["findings"]["capacityRisks"][0]["peakScheduledUnits"]
                if result["findings"]["capacityRisks"]
                else brute_peak
            )
            with self.subTest(repetition=repetition):
                self.assertEqual(cycle_oracle(values), actual_cycles)
                self.assertEqual(expected_unsafe, actual_unsafe)
                self.assertEqual(brute_peak > limit, bool(result["findings"]["capacityRisks"]))
                self.assertEqual(brute_peak, actual_peak)

    def test_input_order_does_not_change_output(self) -> None:
        value = snapshot(
            [
                task(
                    "a",
                    dependencies=[dependency("b"), dependency("c")],
                    writes=["r1", "r2"],
                    occurrences=[occurrence(10, 20), occurrence(0, 5)],
                ),
                task("b", dependencies=[dependency("a")], writes=["r1"], occurrences=[]),
                task("c", dependencies=[], writes=[], occurrences=[]),
            ],
            resource_policies=[
                {
                    "resource": "r1",
                    "idempotencyBoundary": False,
                    "enforceableOwnership": False,
                    "evidence": "declared",
                },
                {
                    "resource": "r2",
                    "idempotencyBoundary": True,
                    "enforceableOwnership": True,
                    "evidence": "declared",
                },
            ],
        )
        shuffled = copy.deepcopy(value)
        generator = random.Random(7)
        generator.shuffle(shuffled["tasks"])
        generator.shuffle(shuffled["resourcePolicies"])
        for item in shuffled["tasks"]:
            for field in ("dependencies", "writes", "occurrences"):
                generator.shuffle(item[field])

        self.assertEqual(analyzer.analyze(value), analyzer.analyze(shuffled))

    def test_unrelated_task_does_not_change_existing_risk_groups(self) -> None:
        base = snapshot(
            [
                task("a", dependencies=[dependency("b")], writes=["shared"], occurrences=[]),
                task("b", dependencies=[dependency("a")], writes=["shared"], occurrences=[]),
            ]
        )
        extended = copy.deepcopy(base)
        extended["tasks"].append(
            task("independent", dependencies=[], writes=["isolated"], occurrences=[])
        )

        first = analyzer.analyze(base)["findings"]
        second = analyzer.analyze(extended)["findings"]
        for field in (
            "dependencyCycles",
            "dependencyEdgesOutsideSnapshot",
            "pausedProducerEdges",
            "sharedWriterRisks",
            "capacityRisks",
        ):
            self.assertEqual(first[field], second[field])

    def test_ten_thousand_task_path_is_grouped_and_non_recursive(self) -> None:
        count = 10_000
        values = [
            task(
                f"task-{index:05d}",
                dependencies=[dependency(f"task-{(index + 1) % count:05d}")],
                writes=["hotspot"],
                occurrences=[occurrence(100, 200)],
            )
            for index in range(count)
        ]
        result = analyzer.analyze(
            snapshot(
                values,
                capacity_groups=[
                    {"id": "local", "limit": 100, "evidence": "declared"}
                ],
            ),
            max_members=12,
        )

        self.assertEqual(
            {
                "tasks": count,
                "dependencyEdges": count,
                "internalDependencyEdges": count,
                "resourceWriteReferences": count,
                "occurrences": count,
                "knownRuntimeOccurrences": count,
                "scheduleEvents": count * 2,
            },
            result["work"],
        )
        cycle = result["findings"]["dependencyCycles"]
        writers = result["findings"]["sharedWriterRisks"]
        clusters = result["findings"]["startClusters"]
        capacity = result["findings"]["capacityRisks"]
        self.assertEqual(1, len(cycle))
        self.assertEqual(count, cycle[0]["memberTaskIds"]["count"])
        self.assertEqual(12, len(cycle[0]["memberTaskIds"]["sample"]))
        self.assertTrue(cycle[0]["memberTaskIds"]["sampleTruncated"])
        self.assertEqual(1, len(writers))
        self.assertEqual(count, writers[0]["writerTaskIds"]["count"])
        self.assertEqual(1, len(clusters))
        self.assertEqual(count, clusters[0]["occurrenceCount"])
        self.assertEqual(1, len(capacity))
        self.assertEqual(count, capacity[0]["peakScheduledUnits"])

    def test_cli_reads_stdin_and_emits_the_same_result(self) -> None:
        value = snapshot(
            [task("a", dependencies=[], writes=[], occurrences=[])]
        )
        expected = analyzer.analyze(value)
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "-"],
            input=json.dumps(value),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            env=environment,
        )

        self.assertEqual("", completed.stderr)
        self.assertEqual(expected, json.loads(completed.stdout))

    def test_cli_rejects_duplicate_json_object_keys(self) -> None:
        value = snapshot(
            [task("a", dependencies=[], writes=[], occurrences=[])]
        )
        payload = json.dumps(value)
        needle = f'"schema": "{analyzer.INPUT_SCHEMA}"'
        payload = payload.replace(needle, f"{needle}, {needle}", 1)
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "-"],
            input=payload,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=environment,
        )

        self.assertEqual(2, completed.returncode)
        self.assertEqual("", completed.stdout)
        self.assertIn("duplicate JSON object key: schema", completed.stderr)


if __name__ == "__main__":
    unittest.main()
