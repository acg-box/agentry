#!/usr/bin/env python3
"""Verify an Automation evaluation receipt against its raw run."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import re
import shlex
import sys
from pathlib import Path
from typing import Any


RECEIPT_SCHEMAS = {
    "helixbox/automation-evaluation-receipt/1",
    "helixbox/automation-evaluation-receipt/2",
}
RUN_SCHEMAS = {
    "helixbox/automation-paired-run/1",
    "helixbox/automation-paired-run/2",
}
ARMS = ("candidate-skills", "no-skill")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
PAIR_PATTERN = re.compile(r"(?P<scenario>.+)-r(?P<repetition>[0-9]{2,})")
JQ_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9_.-])jq(?![A-Za-z0-9_.-])")
CONFIRMATION_REPETITIONS = 10
CURRENT_PROTOCOL_VERSION = 5
BOOTSTRAP_SAMPLES = 5000
CONFIDENCE_LEVEL = 0.95
MINIMUM_CANDIDATE_ACCURACY = 0.9
MINIMUM_ABSOLUTE_UPLIFT = 0.1
MAXIMUM_OVERCONTROL_ERROR_RATE = 0.05
CONTROL_CEILING = 0.95
QUALIFICATION_DIGEST_KEYS = {
    "runner",
    "config",
    "oracle",
    "coverage",
    "workspace",
    "candidate",
    "candidate_treatment",
}
REPO_ROOT = Path(__file__).parents[4]
BENCHMARK_RUNNER_PATH = (
    REPO_ROOT
    / "dev"
    / "plugins"
    / "automation"
    / "scripts"
    / "run_behavior_benchmark.py"
)
CONFIG_PATH = REPO_ROOT / "dev" / "plugins" / "automation" / "benchmark.json"
ORACLE_PATH = (
    REPO_ROOT
    / "dev"
    / "plugins"
    / "automation"
    / "benchmarks"
    / "oracle.json"
)
COVERAGE_PATH = (
    REPO_ROOT
    / "dev"
    / "plugins"
    / "automation"
    / "benchmarks"
    / "coverage.json"
)
WORKSPACE_ROOT = (
    REPO_ROOT / "dev" / "plugins" / "automation" / "benchmark-workspace"
)
CANDIDATE_ROOT = REPO_ROOT / "plugins" / "automation"
V4_RECEIPT_KEYS = {
    "schema",
    "runId",
    "phase",
    "protocolVersion",
    "result",
    "processExitCode",
    "model",
    "reasoningEffort",
    "seed",
    "scenarioCount",
    "repetitions",
    "expectedPairs",
    "completePairs",
    "cells",
    "sourceStableDuringRun",
    "codexIdentity",
    "candidate",
    "control",
    "pairedAccuracyUplift",
    "artifacts",
    "claimBoundary",
}
V4_RECEIPT_CANDIDATE_KEYS = {
    "cells",
    "accuracy",
    "validOutputs",
    "behavioralFailures",
    "hardFailures",
    "integrityFailures",
    "criticalViolations",
    "case04PositiveRoutingFailures",
    "case11NegativeRoutingFailures",
}
V4_RECEIPT_CONTROL_KEYS = {
    "cells",
    "accuracy",
    "validOutputs",
    "behavioralFailures",
    "hardFailures",
    "integrityFailures",
    "criticalViolations",
}
V4_RECEIPT_CODEX_IDENTITY_KEYS = {"version", "entrySha256"}
V4_RECEIPT_INTERVAL_KEYS = {"estimate", "lower95", "upper95"}
V4_RECEIPT_ARTIFACT_KEYS = {
    "ephemeralRoot",
    "metadataSha256",
    "recordsSha256",
    "unblindingMapSha256",
    "candidatePluginSha256",
    "candidateTreatmentSha256",
    "runnerSha256",
    "configSha256",
    "oracleSha256",
    "coverageSha256",
    "workspaceSha256",
}


class VerificationError(ValueError):
    """The receipt or its raw evidence failed closed verification."""


def _fail(message: str) -> None:
    raise VerificationError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{context} must be a JSON object")
    return value


def _array(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{context} must be a JSON array")
    return value


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{context} must be a non-empty string")
    return value


def _integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        _fail(f"{context} must be an integer greater than or equal to {minimum}")
    return value


def _boolean(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{context} must be a boolean")
    return value


def _number(value: Any, context: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        _fail(f"{context} must be a number")
    number = float(value)
    if not math.isfinite(number):
        _fail(f"{context} must be finite")
    return number


def _sha256(value: Any, context: str) -> str:
    digest = _string(value, context)
    if SHA256_PATTERN.fullmatch(digest) is None:
        _fail(f"{context} must be a lowercase SHA-256 digest")
    return digest


def _load_json(path: Path, expected: type, context: str) -> Any:
    _require(path.is_file() and not path.is_symlink(), f"missing or unsafe {context}: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"malformed {context}: {path}: {error}")
    if not isinstance(value, expected):
        _fail(f"{context} has the wrong JSON type: {path}")
    return value


def _file_digest(path: Path) -> str:
    _require(path.is_file() and not path.is_symlink(), f"missing or unsafe artifact: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_benchmark_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "automation_benchmark_for_receipt_verification",
        BENCHMARK_RUNNER_PATH,
    )
    _require(
        spec is not None and spec.loader is not None,
        "cannot load the benchmark semantic verifier",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _equal(actual: Any, expected: Any, context: str) -> None:
    if isinstance(actual, bool) or isinstance(expected, bool):
        if type(actual) is type(expected) and actual == expected:
            return
        _fail(f"{context} mismatch: expected {expected!r}, found {actual!r}")
    if isinstance(actual, (int, float)) and not isinstance(actual, bool):
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            if abs(float(actual) - float(expected)) <= 1e-9:
                return
    if actual != expected:
        _fail(f"{context} mismatch: expected {expected!r}, found {actual!r}")


def _check_root(root: Path) -> Path:
    _require(root.exists() and root.is_dir(), f"raw run root is unavailable: {root}")
    _require(not root.is_symlink(), f"raw run root must not be a symlink: {root}")
    resolved = root.resolve(strict=True)
    for path in resolved.rglob("*"):
        _require(not path.is_symlink(), f"raw run contains a symlink: {path}")
    return resolved


def _reasoning_effort(metadata: dict[str, Any]) -> str:
    direct = metadata.get("reasoning_effort")
    if direct is not None:
        return _string(direct, "metadata.reasoning_effort")
    arguments = _array(metadata.get("reasoning_configuration"), "metadata.reasoning_configuration")
    values: list[str] = []
    for index, argument in enumerate(arguments):
        if argument != "--config" or index + 1 >= len(arguments):
            continue
        setting = arguments[index + 1]
        if not isinstance(setting, str):
            _fail("metadata.reasoning_configuration contains a non-string setting")
        match = re.fullmatch(r'model_reasoning_effort=["\']([^"\']+)["\']', setting)
        if match:
            values.append(match.group(1))
    _require(len(values) == 1, "metadata must identify exactly one reasoning effort")
    return values[0]


def _command_uses_jq(command: str) -> bool:
    """Return true for direct or shell-wrapped jq use.

    The text check is intentionally stricter than an option check. Evaluation
    evidence must not depend on jq filters, modules, include directives, or
    import directives.
    """

    if JQ_TOKEN_PATTERN.search(command):
        return True
    try:
        tokens = shlex.split(command)
    except ValueError:
        _fail("event command is not valid shell syntax")
    if any(Path(token).name == "jq" for token in tokens):
        return True
    if (
        len(tokens) == 3
        and Path(tokens[0]).name in {"bash", "sh", "zsh"}
        and tokens[1] in {"-c", "-lc"}
    ):
        try:
            inner = shlex.split(tokens[2])
        except ValueError:
            _fail("shell-wrapped event command is not valid shell syntax")
        return any(Path(token).name == "jq" for token in inner)
    return False


def _scan_events(path: Path) -> None:
    _require(path.is_file() and not path.is_symlink(), f"missing event log: {path}")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        _fail(f"cannot read event log {path}: {error}")
    _require(bool(lines), f"event log is empty: {path}")
    for line_number, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            _fail(f"malformed event JSON at {path}:{line_number}: {error}")
        event = _object(event, f"event at {path}:{line_number}")
        item = event.get("item")
        if item is None:
            continue
        item = _object(item, f"event item at {path}:{line_number}")
        if item.get("type") != "command_execution":
            continue
        command = _string(item.get("command"), f"event command at {path}:{line_number}")
        if _command_uses_jq(command):
            _fail(f"jq use is forbidden in evaluation evidence: {path}:{line_number}")


def _validate_record(
    record: dict[str, Any],
    metadata_model: str,
    *,
    strict_schema2: bool,
) -> None:
    pair_id = _string(record.get("pair_id"), "record.pair_id")
    scenario = _string(record.get("scenario"), f"{pair_id}.scenario")
    repetition = _integer(record.get("repetition"), f"{pair_id}.repetition", minimum=1)
    pair_match = PAIR_PATTERN.fullmatch(pair_id)
    _require(pair_match is not None, f"invalid pair ID: {pair_id}")
    _equal(pair_match.group("scenario"), scenario, f"{pair_id}.scenario")
    _equal(int(pair_match.group("repetition")), repetition, f"{pair_id}.repetition")
    arm = _string(record.get("arm"), f"{pair_id}.arm")
    _require(arm in ARMS, f"invalid arm for {pair_id}: {arm}")
    _integer(record.get("pair_index"), f"{pair_id}.{arm}.pair_index")
    arm_position = _integer(record.get("arm_position"), f"{pair_id}.{arm}.arm_position")
    _require(arm_position in {0, 1}, f"{pair_id}.{arm}.arm_position must be 0 or 1")
    _equal(_string(record.get("model"), f"{pair_id}.{arm}.model"), metadata_model, f"{pair_id}.{arm}.model")
    _equal(_string(record.get("sandbox"), f"{pair_id}.{arm}.sandbox"), "read-only", f"{pair_id}.{arm}.sandbox")

    codex_exit = _integer(record.get("codex_exit_code"), f"{pair_id}.{arm}.codex_exit_code")
    workspace_changes = _integer(
        record.get("workspace_change_count"), f"{pair_id}.{arm}.workspace_change_count"
    )
    forbidden_events = _array(record.get("forbidden_events"), f"{pair_id}.{arm}.forbidden_events")
    _require(
        all(isinstance(item, str) and item for item in forbidden_events),
        f"{pair_id}.{arm}.forbidden_events must contain strings",
    )
    parse_error = record.get("parse_error")
    _require(
        parse_error is None or isinstance(parse_error, str),
        f"{pair_id}.{arm}.parse_error must be null or a string",
    )
    audit_loaded = _boolean(
        record.get("audit_skill_load_observed"), f"{pair_id}.{arm}.audit_skill_load_observed"
    )
    manage_loaded = _boolean(
        record.get("manage_skill_load_observed"), f"{pair_id}.{arm}.manage_skill_load_observed"
    )
    if strict_schema2:
        audit_access = _boolean(
            record.get("audit_skill_access_observed"),
            f"{pair_id}.{arm}.audit_skill_access_observed",
        )
        manage_access = _boolean(
            record.get("manage_skill_access_observed"),
            f"{pair_id}.{arm}.manage_skill_access_observed",
        )
        reference_access = _boolean(
            record.get("reference_access_observed"),
            f"{pair_id}.{arm}.reference_access_observed",
        )
        treatment_access = _boolean(
            record.get("candidate_treatment_access_observed"),
            f"{pair_id}.{arm}.candidate_treatment_access_observed",
        )
        _equal(
            treatment_access,
            audit_access or manage_access or reference_access,
            f"{pair_id}.{arm}.candidate_treatment_access_observed",
        )
        _require(not audit_loaded or audit_access, f"{pair_id}.{arm} loaded audit without access")
        _require(not manage_loaded or manage_access, f"{pair_id}.{arm} loaded manage without access")
    else:
        audit_access = audit_loaded
        manage_access = manage_loaded
        reference_access = False
        treatment_access = audit_access or manage_access
    routing_observed = _boolean(record.get("routing_observed"), f"{pair_id}.{arm}.routing_observed")

    if scenario == "case-04" and arm == "candidate-skills":
        _equal(routing_observed, audit_loaded and not manage_access, f"{pair_id}.{arm}.positive routing")
    if scenario == "case-11":
        _equal(routing_observed, not treatment_access, f"{pair_id}.{arm}.negative routing")
    if arm == "no-skill":
        _require(not treatment_access, f"{pair_id}.{arm} accessed candidate treatment")

    score = _object(record.get("score"), f"{pair_id}.{arm}.score")
    valid = _boolean(score.get("valid"), f"{pair_id}.{arm}.score.valid")
    correct = _integer(score.get("correct"), f"{pair_id}.{arm}.score.correct")
    total = _integer(score.get("total"), f"{pair_id}.{arm}.score.total", minimum=1)
    _require(correct <= total, f"{pair_id}.{arm}.score.correct exceeds total")
    _equal(
        _number(score.get("accuracy"), f"{pair_id}.{arm}.score.accuracy"),
        round(correct / total, 6),
        f"{pair_id}.{arm}.score.accuracy",
    )
    critical = _array(score.get("critical_violations"), f"{pair_id}.{arm}.score.critical_violations")
    overcontrol = _array(score.get("overcontrol_errors"), f"{pair_id}.{arm}.score.overcontrol_errors")
    _require(all(isinstance(item, str) for item in critical), f"{pair_id}.{arm} has malformed critical violations")
    _require(all(isinstance(item, str) for item in overcontrol), f"{pair_id}.{arm} has malformed overcontrol errors")
    overcontrol_total = _integer(
        score.get("overcontrol_total"), f"{pair_id}.{arm}.score.overcontrol_total"
    )
    _require(len(overcontrol) <= overcontrol_total, f"{pair_id}.{arm} overcontrol count exceeds total")

    integrity = _boolean(record.get("integrity_failure"), f"{pair_id}.{arm}.integrity_failure")
    behavioral = _boolean(record.get("behavioral_failure"), f"{pair_id}.{arm}.behavioral_failure")
    hard = _boolean(record.get("hard_failure"), f"{pair_id}.{arm}.hard_failure")
    expected_integrity = bool(
        codex_exit != 0
        or workspace_changes
        or forbidden_events
        or (arm == "no-skill" and not routing_observed)
    )
    expected_behavioral = bool(
        parse_error
        or not valid
        or critical
        or (arm == "candidate-skills" and not routing_observed)
    )
    expected_hard = bool(expected_integrity or (arm == "candidate-skills" and expected_behavioral))
    _equal(integrity, expected_integrity, f"{pair_id}.{arm}.integrity_failure")
    _equal(behavioral, expected_behavioral, f"{pair_id}.{arm}.behavioral_failure")
    _equal(hard, expected_hard, f"{pair_id}.{arm}.hard_failure")


def _arm_summary(records: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    selected = [record for record in records if record["arm"] == arm]
    correct = sum(
        int(record["score"]["correct"]) if record["score"]["valid"] else 0
        for record in selected
    )
    total = sum(int(record["score"]["total"]) for record in selected)
    scenario_accuracy: dict[str, float] = {}
    for scenario in sorted({str(record["scenario"]) for record in selected}):
        scenario_records = [record for record in selected if record["scenario"] == scenario]
        scenario_correct = sum(
            int(record["score"]["correct"]) if record["score"]["valid"] else 0
            for record in scenario_records
        )
        scenario_total = sum(int(record["score"]["total"]) for record in scenario_records)
        scenario_accuracy[scenario] = round(scenario_correct / scenario_total, 6)
    overcontrol_errors = sum(len(record["score"]["overcontrol_errors"]) for record in selected)
    overcontrol_total = sum(int(record["score"]["overcontrol_total"]) for record in selected)
    return {
        "arm": arm,
        "cells": len(selected),
        "valid_outputs": sum(bool(record["score"]["valid"]) for record in selected),
        "integrity_failures": sum(bool(record["integrity_failure"]) for record in selected),
        "behavioral_failures": sum(bool(record["behavioral_failure"]) for record in selected),
        "hard_failures": sum(bool(record["hard_failure"]) for record in selected),
        "critical_violations": sum(len(record["score"]["critical_violations"]) for record in selected),
        "overcontrol_errors": overcontrol_errors,
        "overcontrol_total": overcontrol_total,
        "overcontrol_error_rate": round(overcontrol_errors / overcontrol_total, 6) if overcontrol_total else 0.0,
        "accuracy": round(correct / total, 6) if total else None,
        "scenario_accuracy": scenario_accuracy,
    }


def _paired_accuracy_interval(
    records: list[dict[str, Any]], seed: int
) -> dict[str, Any]:
    """Independently reproduce the preregistered paired bootstrap."""

    by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        by_pair.setdefault(record["pair_id"], {})[record["arm"]] = record
    by_scenario: dict[str, list[tuple[int, int, int, int]]] = {}
    for pair_id, arms in by_pair.items():
        _equal(set(arms), set(ARMS), f"paired interval arms for {pair_id}")
        candidate = arms["candidate-skills"]
        control = arms["no-skill"]
        _equal(candidate["scenario"], control["scenario"], f"paired interval scenario for {pair_id}")
        by_scenario.setdefault(candidate["scenario"], []).append(
            (
                candidate["score"]["correct"] if candidate["score"]["valid"] else 0,
                candidate["score"]["total"],
                control["score"]["correct"] if control["score"]["valid"] else 0,
                control["score"]["total"],
            )
        )
    _require(bool(by_scenario), "paired interval has no scenarios")
    pairs = [pair for values in by_scenario.values() for pair in values]

    def uplift(values: list[tuple[int, int, int, int]]) -> float:
        candidate_correct = sum(value[0] for value in values)
        candidate_total = sum(value[1] for value in values)
        control_correct = sum(value[2] for value in values)
        control_total = sum(value[3] for value in values)
        return candidate_correct / candidate_total - control_correct / control_total

    estimate = uplift(pairs)
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sampled: list[tuple[int, int, int, int]] = []
        for scenario in sorted(by_scenario):
            values = by_scenario[scenario]
            sampled.extend(rng.choice(values) for _ in range(len(values)))
        draws.append(uplift(sampled))
    draws.sort()

    def percentile(probability: float) -> float:
        position = probability * (len(draws) - 1)
        lower = int(position)
        upper = min(lower + 1, len(draws) - 1)
        fraction = position - lower
        return draws[lower] * (1 - fraction) + draws[upper] * fraction

    alpha = (1 - CONFIDENCE_LEVEL) / 2
    return {
        "method": "scenario_stratified_paired_bootstrap",
        "confidence": CONFIDENCE_LEVEL,
        "samples": BOOTSTRAP_SAMPLES,
        "seed": seed,
        "weighting": "proposition_weighted",
        "pairs": len(pairs),
        "estimate": round(estimate, 6),
        "lower": round(percentile(alpha), 6),
        "upper": round(percentile(1 - alpha), 6),
    }


def _expected_schedule(
    scenario_ids: list[str], repetitions: int, seed: int
) -> list[dict[str, Any]]:
    pairs = [
        (scenario, repetition)
        for scenario in scenario_ids
        for repetition in range(1, repetitions + 1)
    ]
    rng = random.Random(seed)
    rng.shuffle(pairs)
    starts = {scenario: rng.randrange(2) for scenario in scenario_ids}
    schedule: list[dict[str, Any]] = []
    for pair_index, (scenario, repetition) in enumerate(pairs):
        first = (repetition - 1 + starts[scenario]) % 2
        order = ("no-skill", "candidate-skills")
        ordered_arms = (order[first], order[1 - first])
        pair_id = f"{scenario}-r{repetition:02d}"
        for arm_position, arm in enumerate(ordered_arms):
            schedule.append(
                {
                    "pair_id": pair_id,
                    "pair_index": pair_index,
                    "scenario": scenario,
                    "repetition": repetition,
                    "arm": arm,
                    "arm_position": arm_position,
                }
            )
    return schedule


def _validate_v4_identity(
    metadata: dict[str, Any],
    *,
    protocol_version: int,
    model: str,
    seed: int,
    scenario_ids: list[str],
) -> None:
    input_digests = _object(
        metadata.get("input_snapshot_sha256"), "metadata.input_snapshot_sha256"
    )
    _equal(set(input_digests), QUALIFICATION_DIGEST_KEYS, "metadata.input_snapshot_sha256 keys")
    for name, digest in input_digests.items():
        _sha256(digest, f"metadata.input_snapshot_sha256.{name}")
    source_aliases = {
        "runner_sha256": "runner",
        "config_sha256": "config",
        "oracle_sha256": "oracle",
        "coverage_sha256": "coverage",
        "workspace_sha256": "workspace",
        "candidate_plugin_sha256": "candidate",
        "candidate_treatment_sha256": "candidate_treatment",
    }
    for alias, snapshot_key in source_aliases.items():
        _equal(
            _sha256(metadata.get(alias), f"metadata.{alias}"),
            input_digests[snapshot_key],
            f"metadata.{alias} input snapshot binding",
        )
    reasoning_configuration = _array(
        metadata.get("reasoning_configuration"), "metadata.reasoning_configuration"
    )
    _require(
        all(isinstance(argument, str) for argument in reasoning_configuration),
        "metadata.reasoning_configuration must contain strings",
    )
    skill_read_policy = _string(metadata.get("skill_read_policy"), "metadata.skill_read_policy")
    codex_identity = _object(
        metadata.get("codex_identity_before_schedule"),
        "metadata.codex_identity_before_schedule",
    )
    expected_identity = {
        "protocol_version": protocol_version,
        "codex_identity": {
            key: codex_identity[key]
            for key in ("resolved_path", "version", "entry_sha256")
        },
        "input_snapshot_sha256": {
            key: input_digests[key] for key in sorted(QUALIFICATION_DIGEST_KEYS)
        },
        "model": model,
        "reasoning_configuration": reasoning_configuration,
        "skill_read_policy": skill_read_policy,
        "seed": seed,
        "scenario_ids": scenario_ids,
    }
    declared_identity = _object(
        metadata.get("qualification_identity"), "metadata.qualification_identity"
    )
    _equal(declared_identity, expected_identity, "metadata.qualification_identity")
    identity_digest = _canonical_json_digest(expected_identity)
    _equal(
        _sha256(
            metadata.get("qualification_identity_sha256"),
            "metadata.qualification_identity_sha256",
        ),
        identity_digest,
        "metadata.qualification_identity_sha256",
    )


def _synthetic_receipt_for_qualified_prior(metadata_path: Path) -> dict[str, Any]:
    """Build a receipt-shaped adapter for recursively checking a bound raw phase."""

    root = metadata_path.parent
    metadata = _load_json(metadata_path, dict, "qualified prior metadata")
    records = _load_json(root / "records.json", list, "qualified prior records")
    candidate = _object(metadata.get("candidate"), "qualified prior candidate")
    control = _object(metadata.get("control"), "qualified prior control")
    candidate_records = [
        _object(record, "qualified prior record")
        for record in records
        if isinstance(record, dict) and record.get("arm") == "candidate-skills"
    ]
    positive_failures = sum(
        record.get("scenario") == "case-04"
        and not (
            record.get("audit_skill_load_observed") is True
            and record.get("manage_skill_access_observed") is False
        )
        for record in candidate_records
    )
    negative_failures = sum(
        record.get("scenario") == "case-11"
        and record.get("candidate_treatment_access_observed") is True
        for record in candidate_records
    )

    def receipt_summary(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "cells": summary.get("cells"),
            "accuracy": summary.get("accuracy"),
            "validOutputs": summary.get("valid_outputs"),
            "behavioralFailures": summary.get("behavioral_failures"),
            "hardFailures": summary.get("hard_failures"),
            "integrityFailures": summary.get("integrity_failures"),
            "criticalViolations": summary.get("critical_violations"),
        }

    phase = _string(metadata.get("phase"), "qualified prior phase")
    exit_code = _integer(
        metadata.get("runner_exit_code"),
        "qualified prior runner exit code",
    )
    if phase == "smoke":
        result = (
            "harness_smoke_passed"
            if exit_code == 0
            else "harness_smoke_failed_integrity"
        )
    elif phase == "pilot":
        result = (
            "paired_pilot_passed"
            if exit_code == 0
            else "paired_pilot_failed_integrity"
        )
    else:
        result = _string(metadata.get("claim_label"), "qualified prior claim label")
    interval = _object(
        metadata.get("paired_accuracy_uplift_interval"),
        "qualified prior paired interval",
    )
    artifacts = {
        "ephemeralRoot": str(root),
        "metadataSha256": _file_digest(metadata_path),
        "recordsSha256": _file_digest(root / "records.json"),
        "unblindingMapSha256": _file_digest(root / "unblinding-map.json"),
        "candidatePluginSha256": metadata.get("candidate_plugin_sha256"),
        "candidateTreatmentSha256": metadata.get("candidate_treatment_sha256"),
        "runnerSha256": metadata.get("runner_sha256"),
        "configSha256": metadata.get("config_sha256"),
        "oracleSha256": metadata.get("oracle_sha256"),
        "coverageSha256": metadata.get("coverage_sha256"),
        "workspaceSha256": metadata.get("workspace_sha256"),
    }
    candidate_receipt = receipt_summary(candidate)
    candidate_receipt.update(
        {
            "case04PositiveRoutingFailures": positive_failures,
            "case11NegativeRoutingFailures": negative_failures,
        }
    )
    return {
        "schema": "helixbox/automation-evaluation-receipt/2",
        "runId": metadata.get("run_id"),
        "phase": phase,
        "protocolVersion": metadata.get("protocol_version"),
        "result": result,
        "processExitCode": metadata.get("runner_exit_code"),
        "model": metadata.get("model"),
        "reasoningEffort": _reasoning_effort(metadata),
        "seed": metadata.get("seed"),
        "scenarioCount": metadata.get("scenario_count"),
        "repetitions": metadata.get("repetitions"),
        "expectedPairs": metadata.get("expected_pairs"),
        "completePairs": metadata.get("complete_pairs"),
        "cells": len(records),
        "sourceStableDuringRun": metadata.get("source_stable_during_run"),
        "codexIdentity": {
            "version": metadata.get("codex_version"),
            "entrySha256": metadata.get("codex_entry_sha256"),
        },
        "candidate": candidate_receipt,
        "control": receipt_summary(control),
        "pairedAccuracyUplift": {
            "estimate": interval.get("estimate"),
            "lower95": interval.get("lower"),
            "upper95": interval.get("upper"),
        },
        "artifacts": artifacts,
        "claimBoundary": {
            "scope": metadata.get("claim_boundary"),
            "rawClaimLabel": metadata.get("claim_label"),
            "manageSkillRoutingVerified": False,
            "realAutomationMutationVerified": False,
        },
    }


def _validate_v4_qualification(
    metadata: dict[str, Any],
    *,
    root: Path,
    oracle_path: Path,
    candidate_root: Path,
    visited: set[Path],
) -> None:
    phase = _string(metadata.get("phase"), "metadata.phase")
    qualification = metadata.get("qualification")
    if phase == "smoke":
        _require(qualification is None, "schema-2 smoke must not contain qualification provenance")
        return
    _require(phase in {"pilot", "confirm"}, f"unsupported schema-2 qualification phase: {phase}")
    provenance = _object(qualification, "metadata.qualification")
    required_keys = {
        "required_prior_phase",
        "prior_run_id",
        "prior_metadata_path",
        "prior_metadata_sha256",
        "qualification_identity_sha256",
        "validated",
    }
    _equal(set(provenance), required_keys, "metadata.qualification fields")
    _require(provenance.get("validated") is True, "metadata.qualification was not validated")
    prior_phase = "smoke" if phase == "pilot" else "pilot"
    _equal(
        _string(provenance.get("required_prior_phase"), "qualification prior phase"),
        prior_phase,
        "metadata.qualification.required_prior_phase",
    )
    current_identity_digest = _sha256(
        metadata.get("qualification_identity_sha256"),
        "metadata.qualification_identity_sha256",
    )
    _equal(
        _sha256(
            provenance.get("qualification_identity_sha256"),
            "metadata.qualification.qualification_identity_sha256",
        ),
        current_identity_digest,
        "metadata.qualification.qualification_identity_sha256",
    )
    prior_path = Path(
        _string(
            provenance.get("prior_metadata_path"),
            "metadata.qualification.prior_metadata_path",
        )
    ).expanduser()
    _require(
        prior_path.is_file() and not prior_path.is_symlink(),
        f"qualified prior metadata is unavailable: {prior_path}",
    )
    prior_path = prior_path.resolve(strict=True)
    _require(prior_path.name == "metadata.json", "qualified prior path must name metadata.json")
    _equal(
        _file_digest(prior_path),
        _sha256(
            provenance.get("prior_metadata_sha256"),
            "metadata.qualification.prior_metadata_sha256",
        ),
        "metadata.qualification.prior_metadata_sha256",
    )
    prior_metadata = _load_json(prior_path, dict, "qualified prior metadata")
    _equal(prior_metadata.get("phase"), prior_phase, "qualified prior phase")
    _equal(
        prior_metadata.get("run_id"),
        _string(provenance.get("prior_run_id"), "metadata.qualification.prior_run_id"),
        "metadata.qualification.prior_run_id",
    )
    _equal(
        prior_metadata.get("qualification_identity_sha256"),
        current_identity_digest,
        "qualified prior identity digest",
    )
    prior_receipt = _synthetic_receipt_for_qualified_prior(prior_path)
    verify_receipt(
        prior_path,
        prior_path.parent,
        oracle_path=oracle_path,
        candidate_root=candidate_root,
        _receipt=prior_receipt,
        _visited=visited,
    )


def _v4_semantic_sources(
    metadata: dict[str, Any],
    *,
    oracle_path: Path,
    candidate_root: Path,
) -> tuple[Any, dict[str, Any], str, str, dict[str, str]]:
    """Load the exact schema-2 sources named by the frozen input digests."""

    benchmark = _load_benchmark_module()
    input_digests = _object(
        metadata.get("input_snapshot_sha256"), "metadata.input_snapshot_sha256"
    )
    source_paths = {
        "runner": BENCHMARK_RUNNER_PATH,
        "config": CONFIG_PATH,
        "oracle": oracle_path,
        "coverage": COVERAGE_PATH,
    }
    observed = {name: _file_digest(path) for name, path in source_paths.items()}
    observed.update(
        {
            "workspace": benchmark.workspace_digest(WORKSPACE_ROOT),
            "candidate": benchmark.workspace_digest(candidate_root),
            "candidate_treatment": benchmark.treatment_digest(candidate_root),
        }
    )
    for name, digest in observed.items():
        _equal(digest, input_digests[name], f"schema-2 semantic source digest {name}")

    config = _load_json(CONFIG_PATH, dict, "benchmark config")
    _equal(
        config.get("version"),
        metadata.get("protocol_version"),
        "benchmark config protocol version",
    )
    runner = _object(config.get("runner"), "benchmark config runner")
    _equal(
        metadata.get("model"),
        runner.get("model"),
        "metadata.model versus benchmark config",
    )
    _equal(
        metadata.get("reasoning_configuration"),
        runner.get("extraArgs"),
        "metadata.reasoning_configuration versus benchmark config",
    )
    _equal(
        metadata.get("skill_read_policy"),
        runner.get("skillReadPolicy"),
        "metadata.skill_read_policy versus benchmark config",
    )
    measurement = _object(config.get("measurement"), "benchmark config measurement")
    expected_measurement = {
        "confirmationRepetitions": CONFIRMATION_REPETITIONS,
        "bootstrapSamples": BOOTSTRAP_SAMPLES,
        "confidenceLevel": CONFIDENCE_LEVEL,
        "minimumCandidateAccuracy": MINIMUM_CANDIDATE_ACCURACY,
        "minimumAbsoluteUplift": MINIMUM_ABSOLUTE_UPLIFT,
        "maximumOvercontrolErrorRate": MAXIMUM_OVERCONTROL_ERROR_RATE,
        "controlCeiling": CONTROL_CEILING,
    }
    for field, expected in expected_measurement.items():
        _equal(measurement.get(field), expected, f"benchmark config measurement.{field}")
    configured_scenarios = _array(config.get("scenarios"), "benchmark config scenarios")
    configured_ids = [
        _string(item.get("id"), "benchmark config scenario ID")
        for item in configured_scenarios
        if isinstance(item, dict)
    ]
    _equal(len(configured_ids), len(configured_scenarios), "benchmark config scenario IDs")
    metadata_ids = _array(metadata.get("scenario_ids"), "metadata.scenario_ids")
    if metadata.get("phase") in {"pilot", "confirm"}:
        _equal(metadata_ids, configured_ids, "qualified schema-2 scenario set")
    else:
        _require(
            set(metadata_ids).issubset(configured_ids),
            "schema-2 smoke scenario set is outside the benchmark config",
        )
    oracle = _load_json(oracle_path, dict, "benchmark oracle")
    audit_text = (
        candidate_root / "skills" / "audit" / "SKILL.md"
    ).read_text(encoding="utf-8")
    manage_text = (
        candidate_root / "skills" / "manage" / "SKILL.md"
    ).read_text(encoding="utf-8")
    return benchmark, oracle, audit_text, manage_text, observed


def _validate_v4_record_semantics(
    root: Path,
    records: list[dict[str, Any]],
    metadata: dict[str, Any],
    *,
    oracle_path: Path,
    candidate_root: Path,
) -> None:
    benchmark, oracle, audit_text, manage_text, source_digests = _v4_semantic_sources(
        metadata,
        oracle_path=oracle_path,
        candidate_root=candidate_root,
    )
    oracle_scenarios = _object(oracle.get("scenarios"), "benchmark oracle scenarios")
    for index, record in enumerate(records):
        pair_id = str(record["pair_id"])
        arm = str(record["arm"])
        cell_root = root / "raw" / pair_id / arm
        guard_context = _object(
            record.get("guard_context"), f"{pair_id}.{arm}.guard_context"
        )
        workspace_value = _string(
            guard_context.get("workspace_root"),
            f"{pair_id}.{arm}.guard_context.workspace_root",
        )
        readable_values = _array(
            guard_context.get("readable_roots"),
            f"{pair_id}.{arm}.guard_context.readable_roots",
        )
        _require(
            len(readable_values) == 2
            and all(isinstance(value, str) and value for value in readable_values),
            f"{pair_id}.{arm}.guard_context.readable_roots is invalid",
        )
        workspace = Path(workspace_value)
        codex_home = workspace.parent / "task-home" / ".codex"
        expected_roots = [
            str(codex_home / "skills"),
            str(codex_home / "references"),
        ]
        _require(
            workspace.name == "workspace"
            and workspace.parent.name.startswith("automation-benchmark-")
            and readable_values == expected_roots,
            f"{pair_id}.{arm}.guard_context root shape is invalid",
        )
        events_path = cell_root / "codex-events.jsonl"
        final_path = cell_root / "final-message.txt"
        try:
            final_text = final_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            _fail(f"cannot read final output for {pair_id}/{arm}: {error}")
        output, parse_error = benchmark.parse_final_message(final_text)
        expected_oracle = _object(
            oracle_scenarios.get(record["scenario"]),
            f"benchmark oracle {record['scenario']}",
        )
        score = benchmark.score_output(output, expected_oracle, record["scenario"])
        forbidden_events = benchmark.scan_forbidden_events(
            events_path,
            workspace_root=workspace,
            readable_roots=tuple(Path(value) for value in readable_values),
            workspace_validation_root=WORKSPACE_ROOT,
        )
        treatment_reads = benchmark.observed_treatment_reads(
            events_path,
            workspace_root=workspace,
            codex_home=codex_home,
            audit_skill_text=audit_text,
            manage_skill_text=manage_text,
        )
        audit_loaded = treatment_reads["audit_loaded"]
        manage_loaded = treatment_reads["manage_loaded"]
        expected_routing = expected_oracle.get("routing")
        _require(
            expected_routing in {"none", "audit", "manage"},
            f"benchmark oracle routing is invalid for {record['scenario']}",
        )
        routing_observed = (
            not treatment_reads["treatment_access"]
            if arm == "no-skill" or expected_routing == "none"
            else audit_loaded and not treatment_reads["manage_access"]
            if expected_routing == "audit"
            else manage_loaded
        )
        before_digest = _sha256(
            record.get("workspace_digest_before"),
            f"{pair_id}.{arm}.workspace_digest_before",
        )
        after_digest = _sha256(
            record.get("workspace_digest_after"),
            f"{pair_id}.{arm}.workspace_digest_after",
        )
        workspace_changes = int(before_digest != after_digest)
        integrity_failure, behavioral_failure, hard_failure = benchmark.classify_failures(
            arm=arm,
            exit_code=record["codex_exit_code"],
            parse_error=parse_error,
            score=score,
            workspace_changes=workspace_changes,
            forbidden_events=forbidden_events,
            routing_observed=routing_observed,
        )
        semantic_fields = {
            "parse_error": parse_error,
            "workspace_change_count": workspace_changes,
            "forbidden_events": forbidden_events,
            "audit_skill_access_observed": treatment_reads["audit_access"],
            "audit_skill_load_observed": audit_loaded,
            "manage_skill_access_observed": treatment_reads["manage_access"],
            "manage_skill_load_observed": manage_loaded,
            "reference_access_observed": treatment_reads["reference_access"],
            "candidate_treatment_access_observed": treatment_reads[
                "treatment_access"
            ],
            "routing_observed": routing_observed,
            "integrity_failure": integrity_failure,
            "behavioral_failure": behavioral_failure,
            "hard_failure": hard_failure,
            "score": score,
        }
        for field, derived in semantic_fields.items():
            _equal(record.get(field), derived, f"schema-2 semantic record {index}.{field}")

    benchmark_after = _load_benchmark_module()
    observed_after = {
        "runner": _file_digest(BENCHMARK_RUNNER_PATH),
        "config": _file_digest(CONFIG_PATH),
        "oracle": _file_digest(oracle_path),
        "coverage": _file_digest(COVERAGE_PATH),
        "workspace": benchmark_after.workspace_digest(WORKSPACE_ROOT),
        "candidate": benchmark_after.workspace_digest(candidate_root),
        "candidate_treatment": benchmark_after.treatment_digest(candidate_root),
    }
    _equal(observed_after, source_digests, "schema-2 semantic sources changed during verification")


def _v4_run_integrity(
    metadata: dict[str, Any], source_stable: bool
) -> tuple[bool, int]:
    """Recompute schema-2 CLI stability, integrity, and runner exit state."""

    before = _object(
        metadata.get("codex_identity_before_schedule"),
        "metadata.codex_identity_before_schedule",
    )
    after = _object(
        metadata.get("codex_identity_after_schedule"),
        "metadata.codex_identity_after_schedule",
    )
    for field in ("resolved_path", "version", "entry_sha256"):
        _string(before.get(field), f"metadata.codex_identity_before_schedule.{field}")
    _sha256(before.get("entry_sha256"), "metadata.codex_identity_before_schedule.entry_sha256")

    if "capture_error" in after:
        capture_error = _string(
            after.get("capture_error"),
            "metadata.codex_identity_after_schedule.capture_error",
        )
        expected_cli_changes: dict[str, Any] = {
            "capture_error": {"before": None, "after": capture_error}
        }
    else:
        for field in ("resolved_path", "version", "entry_sha256"):
            _string(after.get(field), f"metadata.codex_identity_after_schedule.{field}")
        _sha256(after.get("entry_sha256"), "metadata.codex_identity_after_schedule.entry_sha256")
        expected_cli_changes = {
            field: {"before": before[field], "after": after[field]}
            for field in ("resolved_path", "version", "entry_sha256")
            if before[field] != after[field]
        }
    declared_changes = _object(
        metadata.get("codex_identity_changes_during_run"),
        "metadata.codex_identity_changes_during_run",
    )
    _equal(declared_changes, expected_cli_changes, "metadata.codex_identity_changes_during_run")
    cli_stable = not expected_cli_changes
    _equal(
        _boolean(
            metadata.get("codex_identity_stable_during_run"),
            "metadata.codex_identity_stable_during_run",
        ),
        cli_stable,
        "metadata.codex_identity_stable_during_run",
    )
    _equal(metadata.get("codex_version"), before["version"], "metadata.codex_version")
    _equal(
        _sha256(metadata.get("codex_entry_sha256"), "metadata.codex_entry_sha256"),
        before["entry_sha256"],
        "metadata.codex_entry_sha256",
    )

    expected_failures: list[str] = []
    if not source_stable:
        expected_failures.append("benchmark_sources_changed_during_run")
    if not cli_stable:
        expected_failures.append("codex_identity_changed_during_run")
    declared_failures = _array(
        metadata.get("run_integrity_failures"), "metadata.run_integrity_failures"
    )
    _equal(declared_failures, expected_failures, "metadata.run_integrity_failures")
    run_integrity_failure = bool(expected_failures)
    _equal(
        _boolean(metadata.get("run_integrity_failure"), "metadata.run_integrity_failure"),
        run_integrity_failure,
        "metadata.run_integrity_failure",
    )
    runner_exit_code = _integer(metadata.get("runner_exit_code"), "metadata.runner_exit_code")
    _require(runner_exit_code in {0, 1}, "metadata.runner_exit_code must be 0 or 1")
    return run_integrity_failure, runner_exit_code


def _benchmark_conclusion(
    *,
    raw_phase: str,
    raw_schema: str,
    repetitions: int,
    candidate: dict[str, Any],
    control: dict[str, Any],
    complete_pairs: int,
    expected_pairs: int,
    paired_interval: dict[str, Any],
    source_stable: bool,
    run_integrity_failure: bool,
) -> str:
    phase_ready = bool(
        source_stable
        and not run_integrity_failure
        and complete_pairs == expected_pairs
        and candidate["cells"] == expected_pairs
        and control["cells"] == expected_pairs
        and candidate["valid_outputs"] == candidate["cells"]
        and not candidate["hard_failures"]
        and not control["hard_failures"]
    )
    if raw_phase == "smoke":
        if raw_schema.endswith("/1"):
            return "harness_smoke_only"
        return "harness_smoke_only" if phase_ready else "harness_smoke_failed"
    if raw_phase == "pilot":
        if raw_schema.endswith("/1"):
            return "pilot_no_effect_claim"
        return "pilot_no_effect_claim" if phase_ready else "pilot_failed_no_effect_claim"
    _require(raw_phase == "confirm", f"unsupported raw phase: {raw_phase}")
    if repetitions != CONFIRMATION_REPETITIONS:
        return "benchmark_local_effect_not_demonstrated"
    if not phase_ready:
        return "benchmark_local_effect_not_demonstrated"
    if control["accuracy"] is not None and control["accuracy"] >= CONTROL_CEILING:
        return "benchmark_control_ceiling_no_improvement_claim"
    uplift = round(candidate["accuracy"] - control["accuracy"], 6)
    no_scenario_regression = all(
        candidate["scenario_accuracy"][scenario]
        >= control["scenario_accuracy"][scenario]
        for scenario in candidate["scenario_accuracy"]
    )
    if (
        candidate["accuracy"] >= MINIMUM_CANDIDATE_ACCURACY
        and uplift >= MINIMUM_ABSOLUTE_UPLIFT
        and candidate["overcontrol_error_rate"] <= MAXIMUM_OVERCONTROL_ERROR_RATE
        and no_scenario_regression
        and paired_interval["estimate"] == uplift
        and paired_interval["lower"] > 0
    ):
        return "benchmark_local_effect_observed"
    return "benchmark_local_effect_not_demonstrated"


def _compare_metadata_summary(metadata: dict[str, Any], expected: dict[str, Any], arm: str) -> None:
    actual = _object(metadata.get(arm), f"metadata.{arm}")
    for key, value in expected.items():
        context = f"metadata.{arm}.{key}"
        if key in {
            "cells",
            "valid_outputs",
            "integrity_failures",
            "behavioral_failures",
            "hard_failures",
            "critical_violations",
            "overcontrol_errors",
            "overcontrol_total",
        }:
            _equal(_integer(actual.get(key), context), value, context)
        elif key in {"accuracy", "overcontrol_error_rate"}:
            _equal(_number(actual.get(key), context), value, context)
        else:
            _equal(actual.get(key), value, context)


def _compare_receipt_summary(
    receipt: dict[str, Any],
    expected: dict[str, Any],
    arm: str,
    *,
    strict_v4: bool,
) -> None:
    actual = _object(receipt.get(arm), f"receipt.{arm}")
    mapping = {
        "cells": "cells",
        "accuracy": "accuracy",
        "validOutputs": "valid_outputs",
        "behavioralFailures": "behavioral_failures",
        "hardFailures": "hard_failures",
        "integrityFailures": "integrity_failures",
        "criticalViolations": "critical_violations",
    }
    legacy_optional = {"validOutputs", "criticalViolations"}
    for receipt_key, summary_key in mapping.items():
        if not strict_v4 and receipt_key in legacy_optional and receipt_key not in actual:
            continue
        context = f"receipt.{arm}.{receipt_key}"
        if receipt_key == "accuracy":
            _equal(_number(actual.get(receipt_key), context), expected[summary_key], context)
        else:
            _equal(_integer(actual.get(receipt_key), context), expected[summary_key], context)


def _validate_artifacts(root: Path, records: list[dict[str, Any]]) -> None:
    raw_root = root / "raw"
    _require(raw_root.is_dir() and not raw_root.is_symlink(), f"missing raw cell root: {raw_root}")
    expected_pairs = {str(record["pair_id"]) for record in records}
    actual_pairs = {path.name for path in raw_root.iterdir() if path.is_dir() and not path.is_symlink()}
    _equal(actual_pairs, expected_pairs, "raw pair directories")
    _require(
        all(path.is_dir() and not path.is_symlink() for path in raw_root.iterdir()),
        "raw cell root contains a non-directory entry",
    )

    by_cell = {(str(record["pair_id"]), str(record["arm"])): record for record in records}
    for pair_id in sorted(expected_pairs):
        pair_root = raw_root / pair_id
        actual_arms = {path.name for path in pair_root.iterdir() if path.is_dir() and not path.is_symlink()}
        expected_arms = {arm for current_pair, arm in by_cell if current_pair == pair_id}
        _equal(actual_arms, expected_arms, f"raw arms for {pair_id}")
        _require(
            all(path.is_dir() and not path.is_symlink() for path in pair_root.iterdir()),
            f"raw pair directory contains a non-directory entry: {pair_id}",
        )
        for arm in sorted(expected_arms):
            cell_root = pair_root / arm
            record = by_cell[(pair_id, arm)]
            raw_record = _load_json(cell_root / "record.json", dict, f"raw record {pair_id}/{arm}")
            _equal(raw_record, record, f"raw record {pair_id}/{arm}")
            artifacts = _object(record.get("artifacts"), f"{pair_id}.{arm}.artifacts")
            _require(
                {"codex-events.jsonl", "final-message.txt"}.issubset(artifacts),
                f"{pair_id}.{arm} is missing required artifact digests",
            )
            actual_files = {
                path.name
                for path in cell_root.iterdir()
                if path.is_file() and not path.is_symlink() and path.name != "record.json"
            }
            _equal(actual_files, set(artifacts), f"artifact manifest for {pair_id}/{arm}")
            _require(
                all(path.is_file() and not path.is_symlink() for path in cell_root.iterdir()),
                f"cell directory contains an unsafe entry: {pair_id}/{arm}",
            )
            for name, expected_digest in artifacts.items():
                _require(
                    isinstance(name, str)
                    and Path(name).name == name
                    and name not in {".", "..", "record.json"},
                    f"unsafe artifact name for {pair_id}/{arm}: {name!r}",
                )
                expected_digest = _sha256(expected_digest, f"{pair_id}.{arm}.artifacts.{name}")
                _equal(_file_digest(cell_root / name), expected_digest, f"artifact digest {pair_id}/{arm}/{name}")
            _scan_events(cell_root / "codex-events.jsonl")


def _validate_unblinding(root: Path, records: list[dict[str, Any]], run_id: str) -> None:
    mapping = _load_json(root / "unblinding-map.json", list, "unblinding map")
    _equal(len(mapping), len(records), "unblinding map entry count")
    blind_root = root / "blind"
    _require(blind_root.is_dir() and not blind_root.is_symlink(), f"missing blind artifact root: {blind_root}")
    seen: set[tuple[str, str]] = set()
    expected_blind_files: set[str] = set()
    by_cell = {(str(record["pair_id"]), str(record["arm"])): record for record in records}
    for index, raw_entry in enumerate(mapping):
        entry = _object(raw_entry, f"unblinding map entry {index}")
        pair_id = _string(entry.get("pair_id"), f"unblinding map entry {index}.pair_id")
        arm = _string(entry.get("arm"), f"unblinding map entry {index}.arm")
        key = (pair_id, arm)
        _require(key in by_cell, f"unblinding map references an unknown cell: {key}")
        _require(key not in seen, f"duplicate unblinding map cell: {key}")
        seen.add(key)
        record = by_cell[key]
        _equal(
            _string(entry.get("scenario"), f"unblinding scenario for {key}"),
            record["scenario"],
            f"unblinding scenario for {key}",
        )
        _equal(
            _integer(entry.get("repetition"), f"unblinding repetition for {key}", minimum=1),
            record["repetition"],
            f"unblinding repetition for {key}",
        )
        opaque = hashlib.sha256(f"{run_id}:{pair_id}:{arm}".encode("utf-8")).hexdigest()[:20]
        _equal(entry.get("opaque_output_id"), opaque, f"unblinding opaque ID for {key}")
        source = root / "raw" / pair_id / arm / "final-message.txt"
        blind_name = f"{opaque}.json"
        blind = blind_root / blind_name
        expected_blind_files.add(blind_name)
        _equal(
            _sha256(entry.get("source_sha256"), f"unblinding source digest for {key}"),
            _file_digest(source),
            f"unblinding source digest for {key}",
        )
        _equal(
            _sha256(entry.get("blind_sha256"), f"unblinding blind digest for {key}"),
            _file_digest(blind),
            f"unblinding blind digest for {key}",
        )
    _equal(seen, set(by_cell), "unblinding map cells")
    actual_blind_files = {
        path.name for path in blind_root.iterdir() if path.is_file() and not path.is_symlink()
    }
    _equal(actual_blind_files, expected_blind_files, "blind artifact files")
    _require(
        all(path.is_file() and not path.is_symlink() for path in blind_root.iterdir()),
        "blind artifact root contains an unsafe entry",
    )


def _validate_result(
    receipt: dict[str, Any],
    *,
    receipt_phase: str,
    raw_phase: str,
    expected_exit: int,
    derived_conclusion: str,
    integrity_failures: int,
    positive_routing_failures: int,
    negative_routing_failures: int,
) -> None:
    process_exit = _integer(receipt.get("processExitCode"), "receipt.processExitCode")
    _require(process_exit in {0, 1}, "receipt.processExitCode must be 0 or 1")
    _equal(process_exit, expected_exit, "receipt.processExitCode")
    result = _string(receipt.get("result"), "receipt.result")

    if receipt_phase == "smoke-routing-probe":
        expected_result = (
            "opposed_routing_probe_passed"
            if expected_exit == 0
            else "opposed_routing_probe_failed"
        )
        _equal(result, expected_result, "receipt.result")
        return
    if raw_phase == "smoke":
        if expected_exit == 0:
            _equal(result, "harness_smoke_passed", "receipt.result")
        elif positive_routing_failures and not negative_routing_failures and not integrity_failures:
            _equal(result, "harness_smoke_failed_positive_routing", "receipt.result")
        elif negative_routing_failures and not positive_routing_failures and not integrity_failures:
            _equal(result, "harness_smoke_failed_negative_routing", "receipt.result")
        else:
            _require(result.startswith("harness_smoke_failed"), "failed smoke receipt has a success result")
        return
    if raw_phase == "pilot":
        if expected_exit == 0:
            _require(result.startswith("paired_pilot_") and "failed" not in result, "successful pilot receipt has an invalid result")
        else:
            _require(result.startswith("paired_pilot_failed_"), "failed pilot receipt has a success result")
        return
    if raw_phase == "confirm":
        _equal(result, derived_conclusion, "receipt.result")
        return
    _fail(f"unsupported raw phase: {raw_phase}")


def verify_receipt(
    receipt_path: Path,
    raw_root: Path | None = None,
    *,
    oracle_path: Path = ORACLE_PATH,
    candidate_root: Path = CANDIDATE_ROOT,
    _receipt: dict[str, Any] | None = None,
    _visited: set[Path] | None = None,
) -> dict[str, Any]:
    """Verify one receipt and return a compact evidence summary."""

    receipt = (
        _load_json(receipt_path.resolve(strict=True), dict, "evaluation receipt")
        if _receipt is None
        else _object(_receipt, "internal qualification receipt")
    )
    schema = _string(receipt.get("schema"), "receipt.schema")
    _require(schema in RECEIPT_SCHEMAS, f"unsupported receipt schema: {schema}")
    artifacts = _object(receipt.get("artifacts"), "receipt.artifacts")
    if raw_root is None:
        raw_root = Path(_string(artifacts.get("ephemeralRoot"), "receipt.artifacts.ephemeralRoot"))
    root = _check_root(raw_root)

    metadata_path = root / "metadata.json"
    visited = set() if _visited is None else _visited
    resolved_metadata_path = metadata_path.resolve(strict=True)
    _require(
        resolved_metadata_path not in visited,
        f"qualification chain contains a cycle: {resolved_metadata_path}",
    )
    visited.add(resolved_metadata_path)
    records_path = root / "records.json"
    map_path = root / "unblinding-map.json"
    top_level_digests = {
        "metadataSha256": metadata_path,
        "recordsSha256": records_path,
        "unblindingMapSha256": map_path,
    }
    for key, path in top_level_digests.items():
        _equal(_file_digest(path), _sha256(artifacts.get(key), f"receipt.artifacts.{key}"), f"receipt.artifacts.{key}")

    metadata = _load_json(metadata_path, dict, "run metadata")
    records = _load_json(records_path, list, "aggregate records")
    run_schema = _string(metadata.get("schema"), "metadata.schema")
    _require(run_schema in RUN_SCHEMAS, f"unsupported raw run schema: {run_schema}")
    expected_receipt_schema = (
        "helixbox/automation-evaluation-receipt/2"
        if run_schema.endswith("/2")
        else "helixbox/automation-evaluation-receipt/1"
    )
    _equal(schema, expected_receipt_schema, "receipt/raw schema pairing")
    if run_schema.endswith("/2"):
        _equal(set(receipt), V4_RECEIPT_KEYS, "schema-2 receipt top-level fields")
        _equal(
            set(_object(receipt.get("candidate"), "receipt.candidate")),
            V4_RECEIPT_CANDIDATE_KEYS,
            "schema-2 receipt candidate fields",
        )
        _equal(
            set(_object(receipt.get("control"), "receipt.control")),
            V4_RECEIPT_CONTROL_KEYS,
            "schema-2 receipt control fields",
        )
        _equal(
            set(_object(receipt.get("codexIdentity"), "receipt.codexIdentity")),
            V4_RECEIPT_CODEX_IDENTITY_KEYS,
            "schema-2 receipt codexIdentity fields",
        )
        _equal(
            set(
                _object(
                    receipt.get("pairedAccuracyUplift"),
                    "receipt.pairedAccuracyUplift",
                )
            ),
            V4_RECEIPT_INTERVAL_KEYS,
            "schema-2 receipt pairedAccuracyUplift fields",
        )
        _equal(
            set(_object(receipt.get("artifacts"), "receipt.artifacts")),
            V4_RECEIPT_ARTIFACT_KEYS,
            "schema-2 receipt artifact fields",
        )
        canonical_claim_boundary = {
            "scope": _string(metadata.get("claim_boundary"), "metadata.claim_boundary"),
            "rawClaimLabel": _string(metadata.get("claim_label"), "metadata.claim_label"),
            "manageSkillRoutingVerified": False,
            "realAutomationMutationVerified": False,
        }
        _equal(
            _object(receipt.get("claimBoundary"), "receipt.claimBoundary"),
            canonical_claim_boundary,
            "receipt.claimBoundary",
        )
    if run_schema.endswith("/2"):
        _equal(
            _sha256(metadata.get("records_sha256"), "metadata.records_sha256"),
            _file_digest(records_path),
            "metadata.records_sha256",
        )
        _equal(
            _sha256(
                metadata.get("unblinding_map_sha256"),
                "metadata.unblinding_map_sha256",
            ),
            _file_digest(map_path),
            "metadata.unblinding_map_sha256",
        )
    run_id = _string(metadata.get("run_id"), "metadata.run_id")
    _equal(_string(receipt.get("runId"), "receipt.runId"), run_id, "receipt.runId")
    raw_phase = _string(metadata.get("phase"), "metadata.phase")
    receipt_phase = _string(receipt.get("phase"), "receipt.phase")
    if receipt_phase == "smoke-routing-probe":
        _equal(raw_phase, "smoke", "routing-probe raw phase")
    else:
        _equal(receipt_phase, raw_phase, "receipt.phase")
    protocol_version = _integer(receipt.get("protocolVersion"), "receipt.protocolVersion", minimum=1)
    if run_schema.endswith("/2"):
        _require("protocol_version" in metadata, "protocol-v2 raw metadata is missing protocol_version")
        _equal(
            protocol_version,
            CURRENT_PROTOCOL_VERSION,
            "supported protocol version for raw schema 2",
        )
    else:
        _require(
            protocol_version in {1, 2, 3},
            "raw schema 1 supports only historical protocol versions 1 through 3",
        )
    if "protocol_version" in metadata:
        _equal(
            _integer(metadata["protocol_version"], "metadata.protocol_version", minimum=1),
            protocol_version,
            "receipt.protocolVersion",
        )

    model = _string(metadata.get("model"), "metadata.model")
    _equal(_string(receipt.get("model"), "receipt.model"), model, "receipt.model")
    _equal(
        _string(receipt.get("reasoningEffort"), "receipt.reasoningEffort"),
        _reasoning_effort(metadata),
        "receipt.reasoningEffort",
    )
    seed = _integer(metadata.get("seed"), "metadata.seed")
    repetitions = _integer(metadata.get("repetitions"), "metadata.repetitions", minimum=1)
    _equal(_integer(receipt.get("seed"), "receipt.seed"), seed, "receipt.seed")
    _equal(
        _integer(receipt.get("repetitions"), "receipt.repetitions", minimum=1),
        repetitions,
        "receipt.repetitions",
    )
    if run_schema.endswith("/2"):
        expected_repetitions = {"smoke": 1, "pilot": 3, "confirm": 10}.get(raw_phase)
        _require(expected_repetitions is not None, f"unsupported schema-2 phase: {raw_phase}")
        _equal(repetitions, expected_repetitions, "schema-2 phase repetitions")
        if raw_phase in {"pilot", "confirm"}:
            _equal(seed, 94271, "schema-2 qualified phase seed")

    scenario_count = _integer(metadata.get("scenario_count"), "metadata.scenario_count", minimum=1)
    if "scenarioCount" in receipt:
        _equal(
            _integer(receipt["scenarioCount"], "receipt.scenarioCount", minimum=1),
            scenario_count,
            "receipt.scenarioCount",
        )
    else:
        _require(
            receipt_phase == "smoke-routing-probe" and run_schema.endswith("/1"),
            "receipt.scenarioCount is required",
        )
    expected_pairs = _integer(metadata.get("expected_pairs"), "metadata.expected_pairs", minimum=1)
    complete_pairs_metadata = _integer(metadata.get("complete_pairs"), "metadata.complete_pairs")
    _equal(
        _integer(receipt.get("expectedPairs"), "receipt.expectedPairs", minimum=1),
        expected_pairs,
        "receipt.expectedPairs",
    )
    _equal(
        _integer(receipt.get("completePairs"), "receipt.completePairs"),
        complete_pairs_metadata,
        "receipt.completePairs",
    )
    _equal(expected_pairs, scenario_count * repetitions, "metadata.expected_pairs")
    _equal(_integer(receipt.get("cells"), "receipt.cells"), len(records), "receipt.cells")

    typed_records: list[dict[str, Any]] = []
    cells: set[tuple[str, str]] = set()
    scenarios: set[str] = set()
    by_pair: dict[str, set[str]] = {}
    for index, raw_record in enumerate(records):
        record = _object(raw_record, f"aggregate record {index}")
        _validate_record(
            record,
            model,
            strict_schema2=run_schema.endswith("/2"),
        )
        key = (str(record["pair_id"]), str(record["arm"]))
        _require(key not in cells, f"duplicate aggregate record: {key}")
        cells.add(key)
        scenarios.add(str(record["scenario"]))
        by_pair.setdefault(str(record["pair_id"]), set()).add(str(record["arm"]))
        typed_records.append(record)
    _equal(len(scenarios), scenario_count, "raw scenario count")
    scenario_ids: list[str] | None = None
    if run_schema.endswith("/2"):
        scenario_ids = _array(metadata.get("scenario_ids"), "metadata.scenario_ids")
        _require(
            all(isinstance(item, str) and item for item in scenario_ids),
            "metadata.scenario_ids must contain non-empty strings",
        )
        _equal(len(scenario_ids), len(set(scenario_ids)), "metadata.scenario_ids uniqueness")
        _equal(set(scenario_ids), scenarios, "metadata.scenario_ids")
        expected_schedule = _expected_schedule(scenario_ids, repetitions, seed)
        _equal(len(typed_records), len(expected_schedule), "schema-2 schedule length")
        for index, (record, expected) in enumerate(zip(typed_records, expected_schedule)):
            for field, expected_value in expected.items():
                _equal(record.get(field), expected_value, f"schema-2 schedule {index}.{field}")
    if receipt_phase == "smoke-routing-probe":
        _equal(scenarios, {"case-04", "case-11"}, "routing-probe scenarios")
    complete_pairs = sum(arms == set(ARMS) for arms in by_pair.values())
    records_complete = (
        len(by_pair) == expected_pairs
        and complete_pairs == expected_pairs
        and len(typed_records) == expected_pairs * len(ARMS)
    )
    _require(records_complete, "raw record or pair count is incomplete")
    _equal(complete_pairs_metadata, complete_pairs, "metadata.complete_pairs")

    candidate = _arm_summary(typed_records, "candidate-skills")
    control = _arm_summary(typed_records, "no-skill")
    _compare_metadata_summary(metadata, candidate, "candidate")
    _compare_metadata_summary(metadata, control, "control")
    _compare_receipt_summary(
        receipt, candidate, "candidate", strict_v4=run_schema.endswith("/2")
    )
    _compare_receipt_summary(
        receipt, control, "control", strict_v4=run_schema.endswith("/2")
    )
    absolute_uplift = round(candidate["accuracy"] - control["accuracy"], 6)
    _equal(
        _number(metadata.get("absolute_accuracy_uplift"), "metadata.absolute_accuracy_uplift"),
        absolute_uplift,
        "metadata.absolute_accuracy_uplift",
    )
    paired_interval = _paired_accuracy_interval(typed_records, seed)
    _equal(
        _object(
            metadata.get("paired_accuracy_uplift_interval"),
            "metadata.paired_accuracy_uplift_interval",
        ),
        paired_interval,
        "metadata.paired_accuracy_uplift_interval",
    )
    receipt_interval = receipt.get("pairedAccuracyUplift")
    if run_schema.endswith("/2"):
        _require(receipt_interval is not None, "schema-2 receipt.pairedAccuracyUplift is required")
    if receipt_interval is not None:
        receipt_interval = _object(receipt_interval, "receipt.pairedAccuracyUplift")
        _equal(
            _number(receipt_interval.get("estimate"), "receipt.pairedAccuracyUplift.estimate"),
            paired_interval["estimate"],
            "receipt.pairedAccuracyUplift.estimate",
        )
        _equal(
            _number(receipt_interval.get("lower95"), "receipt.pairedAccuracyUplift.lower95"),
            paired_interval["lower"],
            "receipt.pairedAccuracyUplift.lower95",
        )
        _equal(
            _number(receipt_interval.get("upper95"), "receipt.pairedAccuracyUplift.upper95"),
            paired_interval["upper"],
            "receipt.pairedAccuracyUplift.upper95",
        )

    positive_routing_failures = sum(
        record["scenario"] == "case-04"
        and record["arm"] == "candidate-skills"
        and not (
            record["audit_skill_load_observed"]
            and not record["manage_skill_access_observed"]
        )
        for record in typed_records
    )
    negative_routing_failures = sum(
        record["scenario"] == "case-11"
        and record["arm"] == "candidate-skills"
        and record["candidate_treatment_access_observed"]
        for record in typed_records
    )
    receipt_candidate = _object(receipt.get("candidate"), "receipt.candidate")
    if "case04PositiveRoutingFailures" in receipt_candidate:
        _equal(
            _integer(
                receipt_candidate["case04PositiveRoutingFailures"],
                "receipt.candidate.case04PositiveRoutingFailures",
            ),
            positive_routing_failures,
            "receipt.candidate.case04PositiveRoutingFailures",
        )
    if "case11NegativeRoutingFailures" in receipt_candidate:
        _equal(
            _integer(
                receipt_candidate["case11NegativeRoutingFailures"],
                "receipt.candidate.case11NegativeRoutingFailures",
            ),
            negative_routing_failures,
            "receipt.candidate.case11NegativeRoutingFailures",
        )
    if run_schema.endswith("/2"):
        _require(
            "case04PositiveRoutingFailures" in receipt_candidate
            and "case11NegativeRoutingFailures" in receipt_candidate,
            "schema-2 receipt candidate routing failure counts are required",
        )

    source_stable = _boolean(metadata.get("source_stable_during_run"), "metadata.source_stable_during_run")
    _equal(
        _boolean(receipt.get("sourceStableDuringRun"), "receipt.sourceStableDuringRun"),
        source_stable,
        "receipt.sourceStableDuringRun",
    )
    source_changes = _object(metadata.get("source_changes_during_run"), "metadata.source_changes_during_run")
    _equal(source_stable, not source_changes, "metadata source stability")
    _require(
        metadata.get("inputs_frozen_before_first_cell") is True,
        "metadata does not prove that inputs were frozen before the first cell",
    )
    if run_schema.endswith("/2"):
        _require(
            metadata.get("auth_snapshot_frozen_before_first_cell") is True,
            "metadata does not prove that authentication was frozen before the first cell",
        )
        run_integrity_failure, declared_runner_exit = _v4_run_integrity(
            metadata, source_stable
        )
        assert scenario_ids is not None
        _validate_v4_identity(
            metadata,
            protocol_version=protocol_version,
            model=model,
            seed=seed,
            scenario_ids=scenario_ids,
        )
        _validate_v4_qualification(
            metadata,
            root=root,
            oracle_path=oracle_path,
            candidate_root=candidate_root,
            visited=visited,
        )
    else:
        run_integrity_failure = not source_stable
        declared_runner_exit = int(
            run_integrity_failure
            or candidate["hard_failures"]
            or control["hard_failures"]
        )

    derived_conclusion = _benchmark_conclusion(
        raw_phase=raw_phase,
        raw_schema=run_schema,
        repetitions=repetitions,
        candidate=candidate,
        control=control,
        complete_pairs=complete_pairs,
        expected_pairs=expected_pairs,
        paired_interval=paired_interval,
        source_stable=source_stable,
        run_integrity_failure=run_integrity_failure,
    )
    _equal(
        _string(metadata.get("claim_label"), "metadata.claim_label"),
        derived_conclusion,
        "metadata.claim_label",
    )

    source_digest_mapping = {
        "candidatePluginSha256": "candidate_plugin_sha256",
        "candidateTreatmentSha256": "candidate_treatment_sha256",
        "runnerSha256": "runner_sha256",
        "configSha256": "config_sha256",
        "oracleSha256": "oracle_sha256",
        "coverageSha256": "coverage_sha256",
        "workspaceSha256": "workspace_sha256",
    }
    for receipt_key, metadata_key in source_digest_mapping.items():
        if run_schema.endswith("/2"):
            _require(receipt_key in artifacts, f"schema-2 receipt.artifacts.{receipt_key} is required")
        if receipt_key in artifacts:
            _equal(
                _sha256(artifacts[receipt_key], f"receipt.artifacts.{receipt_key}"),
                _sha256(metadata.get(metadata_key), f"metadata.{metadata_key}"),
                f"receipt.artifacts.{receipt_key}",
            )
    codex_identity = receipt.get("codexIdentity")
    if run_schema.endswith("/2"):
        _require(codex_identity is not None, "schema-2 receipt.codexIdentity is required")
    if codex_identity is not None:
        codex_identity = _object(codex_identity, "receipt.codexIdentity")
        _equal(codex_identity.get("version"), metadata.get("codex_version"), "receipt.codexIdentity.version")
        _equal(
            _sha256(codex_identity.get("entrySha256"), "receipt.codexIdentity.entrySha256"),
            _sha256(metadata.get("codex_entry_sha256"), "metadata.codex_entry_sha256"),
            "receipt.codexIdentity.entrySha256",
        )

    _validate_artifacts(root, typed_records)
    if run_schema.endswith("/2"):
        _validate_v4_record_semantics(
            root,
            typed_records,
            metadata,
            oracle_path=oracle_path,
            candidate_root=candidate_root,
        )
    _validate_unblinding(root, typed_records, run_id)
    hard_failures = candidate["hard_failures"] + control["hard_failures"]
    integrity_failures = candidate["integrity_failures"] + control["integrity_failures"]
    expected_exit = int(bool(run_integrity_failure or hard_failures))
    if run_schema.endswith("/2"):
        _equal(declared_runner_exit, expected_exit, "metadata.runner_exit_code")
    _validate_result(
        receipt,
        receipt_phase=receipt_phase,
        raw_phase=raw_phase,
        expected_exit=expected_exit,
        derived_conclusion=derived_conclusion,
        integrity_failures=integrity_failures,
        positive_routing_failures=positive_routing_failures,
        negative_routing_failures=negative_routing_failures,
    )
    return {
        "verified": True,
        "receipt": str(receipt_path),
        "rawRoot": str(root),
        "runId": run_id,
        "phase": receipt_phase,
        "protocolVersion": protocol_version,
        "pairs": complete_pairs,
        "cells": len(typed_records),
        "candidateCase04PositiveRoutingFailures": positive_routing_failures,
        "candidateCase11NegativeRoutingFailures": negative_routing_failures,
        "hardFailures": hard_failures,
        "integrityFailures": integrity_failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument(
        "--raw-root",
        type=Path,
        help="Use this raw run root instead of the receipt's ephemeralRoot.",
    )
    args = parser.parse_args(argv)
    try:
        summary = verify_receipt(args.receipt, args.raw_root)
    except (OSError, VerificationError) as error:
        print(json.dumps({"verified": False, "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
