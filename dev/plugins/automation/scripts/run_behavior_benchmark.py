#!/usr/bin/env python3
"""Run the paired synthetic Automation benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).parents[4]
DEV_ROOT = REPO_ROOT / "dev" / "plugins" / "automation"
CONFIG_PATH = DEV_ROOT / "benchmark.json"
WORKSPACE_ROOT = DEV_ROOT / "benchmark-workspace"
ORACLE_PATH = DEV_ROOT / "benchmarks" / "oracle.json"
COVERAGE_PATH = DEV_ROOT / "benchmarks" / "coverage.json"
CANDIDATE_ROOT = REPO_ROOT / "plugins" / "automation"
RUNS_ROOT = DEV_ROOT / ".benchmark" / "runs"
ARMS = ("no-skill", "candidate-skills")
PROTOCOL_VERSION = 5
SKILL_READ_POLICY = (
    "If you choose to use an available skill, read its SKILL.md at the exact path "
    "in the available-skills inventory. Resolve each directly linked relative "
    "reference from that file. These rules apply to every benchmark file access, "
    "whether or not you use a skill. Use one simple read-only command at a time. "
    "The only pipeline you may use is `rg --files PATH... | rg REGEX`, with "
    "workspace paths and one non-option regex. Do not scan parent directories to "
    "discover skill files. Do not use any other pipeline, shell control chain, "
    "variable, loop, command substitution, redirection, or glob."
)
PROPOSAL_PATTERN = re.compile(r"\bP\d{2}-[A-Z0-9-]+\b")
BANNED_PROMPT_TERMS = (
    "$automation:",
    "plugins/automation",
    "audit",
    "manage",
    "scoped audit",
    "dependency graph",
    "shared-resource graph",
    "fencing token",
)
SENSITIVE_FIXTURE_PATTERNS = (
    re.compile(r"/(?:Users|home)/[^/\s]+/"),
    re.compile(r"~/.codex"),
    re.compile(r"\b(?:password|api[_-]?key|access[_-]?token)\s*[:=]", re.I),
    re.compile(r"\bsk-[A-Za-z0-9]{12,}\b"),
)
READ_ONLY_COMMANDS = {
    "cat",
    "cut",
    "head",
    "ls",
    "printf",
    "pwd",
    "rg",
    "sed",
    "stat",
    "tail",
    "test",
    "wc",
}
SAFE_COMMAND_OPTIONS = {
    "sed": {"-n", "--quiet", "--silent"},
    "rg": {
        "-F",
        "-g",
        "-i",
        "-n",
        "-N",
        "-s",
        "-S",
        "-U",
        "-w",
        "-x",
        "--count",
        "--files",
        "--glob",
        "--hidden",
        "--json",
        "--no-ignore",
        "--no-messages",
        "--stats",
        "--text",
    },
}
FORBIDDEN_TOOL_TERMS = (
    "automation_update",
    "automation-delete",
    "create_thread",
    "send_message",
    "gmail",
    "slack",
    "calendar",
    "notion",
    "outlook",
    "sharepoint",
    "teams",
    "computer_use",
    "browser",
    "web_search",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def load_json_list(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"expected a JSON object list: {path}")
    return value


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if ".plugin-eval" in path.parts or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def workspace_digest(root: Path) -> str:
    """Digest every workspace entry, including modes, links, and ignored paths."""

    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        stat = path.lstat()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(oct(stat.st_mode).encode("ascii"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"L\0")
            digest.update(os.readlink(path).encode("utf-8"))
        elif path.is_dir():
            digest.update(b"D")
        elif path.is_file():
            digest.update(b"F\0")
            digest.update(path.read_bytes())
        else:
            digest.update(b"O")
        digest.update(b"\0")
    return digest.hexdigest()


def treatment_digest(candidate_root: Path = CANDIDATE_ROOT) -> str:
    """Digest exactly the candidate files added to the treatment home."""

    digest = hashlib.sha256()
    roots = (
        candidate_root / "skills" / "audit",
        candidate_root / "skills" / "manage",
        candidate_root / "references",
    )
    for root in roots:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(candidate_root).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def fixture_paths(
    scenario: str,
    workspace_root: Path = WORKSPACE_ROOT,
) -> tuple[Path, Path]:
    root = workspace_root / "cases" / scenario
    return root / "evidence.md", root / "proposal.md"


def validate_definition(
    config: dict[str, Any],
    oracle: dict[str, Any],
    coverage: dict[str, Any],
    selected: set[str] | None = None,
    workspace_root: Path = WORKSPACE_ROOT,
) -> list[str]:
    """Validate the preregistration without invoking Codex."""

    if config.get("kind") != "plugin-eval-benchmark" or config.get("schemaVersion") != 2:
        raise ValueError("benchmark must use Plugin Eval schema version 2")
    if config.get("version") != PROTOCOL_VERSION:
        raise ValueError("benchmark protocol version differs")
    if config.get("targetKind") != "plugin" or config.get("targetName") != "automation":
        raise ValueError("benchmark target identity is invalid")

    runner = config.get("runner", {})
    if runner.get("sandbox") != "read-only" or runner.get("approvalPolicy") != "never":
        raise ValueError("benchmark must use read-only sandbox and never approval")
    if runner.get("skillReadPolicy") != SKILL_READ_POLICY:
        raise ValueError("benchmark skill-read policy differs")
    extra_args = runner.get("extraArgs")
    required_args = {"--strict-config", "--ignore-user-config", "apps", "multi_agent"}
    if not isinstance(extra_args, list) or not required_args.issubset(set(extra_args)):
        raise ValueError("benchmark runner isolation arguments are incomplete")
    if config.get("workspace") != {
        "sourcePath": "dev/plugins/automation/benchmark-workspace",
        "setupMode": "copy",
        "preserve": "never",
    }:
        raise ValueError("benchmark workspace contract differs")
    if config.get("targetProvisioning", {}).get("mode") != "workspace-plugin-marketplace":
        raise ValueError("benchmark target provisioning differs")
    if config.get("verifiers", {}).get("commands") != []:
        raise ValueError("benchmark must not run workspace verifier commands")

    measurement = config.get("measurement", {})
    if tuple(measurement.get("arms", [])) != ARMS:
        raise ValueError(f"benchmark arms must be {ARMS}")
    if (
        measurement.get("smokeRepetitions") != 1
        or measurement.get("pilotRepetitions") != 3
        or measurement.get("confirmationRepetitions") != 10
    ):
        raise ValueError("benchmark repetition contract differs")
    exact_thresholds = {
        "minimumCandidateAccuracy": 0.90,
        "minimumAbsoluteUplift": 0.10,
        "maximumOvercontrolErrorRate": 0.05,
        "controlCeiling": 0.95,
        "confidenceLevel": 0.95,
    }
    for key, expected_value in exact_thresholds.items():
        if measurement.get(key) != expected_value:
            raise ValueError(f"benchmark threshold differs: {key}")
    if measurement.get("preregisteredSeed") != 94271:
        raise ValueError("benchmark preregistered seed differs")
    if measurement.get("bootstrapSamples") != 5000:
        raise ValueError("benchmark bootstrap sample count differs")

    scenarios = config.get("scenarios")
    oracle_scenarios = oracle.get("scenarios")
    requirements = coverage.get("requirements")
    if not isinstance(scenarios, list) or not isinstance(oracle_scenarios, dict):
        raise ValueError("benchmark scenarios and hidden oracle are required")
    if not isinstance(requirements, dict) or not requirements:
        raise ValueError("benchmark coverage requirements are required")
    scenario_ids = [item.get("id") for item in scenarios if isinstance(item, dict)]
    if len(scenario_ids) != len(scenarios) or len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("scenario IDs must be unique strings")
    if set(scenario_ids) != set(oracle_scenarios):
        raise ValueError("benchmark and oracle scenario sets differ")
    if selected:
        missing = selected - set(scenario_ids)
        if missing:
            raise ValueError(f"unknown scenarios: {sorted(missing)}")
        scenario_ids = [scenario for scenario in scenario_ids if scenario in selected]

    all_proposals: set[str] = set()
    for item in scenarios:
        scenario = item["id"]
        prompt = item.get("userInput")
        checklist = item.get("successChecklist")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"missing prompt: {scenario}")
        leaked = [term for term in BANNED_PROMPT_TERMS if term in prompt.lower()]
        if leaked:
            raise ValueError(f"prompt leaks target vocabulary in {scenario}: {leaked}")
        expected_prompt = (
            f"Review cases/{scenario}/proposal.md against cases/{scenario}/evidence.md. "
            "Return only one JSON object that matches review-output.schema.json. "
            "Assess every labeled proposal exactly once. Do not edit files, use "
            "network services, or act on any scheduler."
        )
        if prompt != expected_prompt:
            raise ValueError(f"scenario prompt differs from neutral template: {scenario}")
        if not isinstance(checklist, list) or not checklist:
            raise ValueError(f"scenario checklist is empty: {scenario}")

        evidence_path, proposal_path = fixture_paths(scenario, workspace_root)
        if not evidence_path.is_file() or not proposal_path.is_file():
            raise ValueError(f"fixture files are missing: {scenario}")
        fixture_text = evidence_path.read_text(encoding="utf-8") + proposal_path.read_text(
            encoding="utf-8"
        )
        for pattern in SENSITIVE_FIXTURE_PATTERNS:
            if pattern.search(fixture_text):
                raise ValueError(f"fixture contains private or credential-like data: {scenario}")
        proposal_ids = PROPOSAL_PATTERN.findall(proposal_path.read_text(encoding="utf-8"))
        if len(proposal_ids) != len(set(proposal_ids)):
            raise ValueError(f"fixture proposal IDs repeat: {scenario}")
        expected = oracle_scenarios[scenario]
        if set(expected) != {"routing", "expected", "critical_ids", "overcontrol_ids"}:
            raise ValueError(f"oracle fields differ: {scenario}")
        if expected["routing"] not in {"audit", "manage", "none"}:
            raise ValueError(f"oracle routing differs: {scenario}")
        expected_map = expected["expected"]
        if not isinstance(expected_map, dict) or set(proposal_ids) != set(expected_map):
            raise ValueError(f"fixture and oracle proposal IDs differ: {scenario}")
        for value in expected_map.values():
            allowed = {value} if isinstance(value, str) else set(value) if isinstance(value, list) else set()
            if not allowed or not allowed.issubset({"accept", "change", "defer"}):
                raise ValueError(f"oracle disposition differs: {scenario}")
        for field in ("critical_ids", "overcontrol_ids"):
            values = expected[field]
            if not isinstance(values, list) or not set(values).issubset(expected_map):
                raise ValueError(f"oracle {field} differs: {scenario}")
        overlap = all_proposals.intersection(proposal_ids)
        if overlap:
            raise ValueError(f"proposal IDs are not globally unique: {sorted(overlap)}")
        all_proposals.update(proposal_ids)

    covered: set[str] = set()
    for requirement, identifiers in requirements.items():
        if not isinstance(requirement, str) or not isinstance(identifiers, list) or not identifiers:
            raise ValueError("coverage entries must be named non-empty lists")
        unknown = set(identifiers) - all_proposals
        if unknown:
            raise ValueError(f"coverage references unknown proposals: {sorted(unknown)}")
        covered.update(identifiers)
    if covered != all_proposals:
        raise ValueError(f"uncovered proposals: {sorted(all_proposals - covered)}")
    if ORACLE_PATH.is_relative_to(WORKSPACE_ROOT) or COVERAGE_PATH.is_relative_to(WORKSPACE_ROOT):
        raise ValueError("hidden scoring files must stay outside the benchmark workspace")
    return scenario_ids


def repetitions_for_phase(config: dict[str, Any], phase: str) -> int:
    key = {
        "smoke": "smokeRepetitions",
        "pilot": "pilotRepetitions",
        "confirm": "confirmationRepetitions",
    }[phase]
    return int(config["measurement"][key])


def build_schedule(
    scenarios: list[str], repetitions: int, seed: int
) -> list[dict[str, Any]]:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    rng = random.Random(seed)
    pairs = [
        (scenario, repetition)
        for scenario in scenarios
        for repetition in range(1, repetitions + 1)
    ]
    rng.shuffle(pairs)
    starts = {scenario: rng.randrange(2) for scenario in scenarios}
    schedule: list[dict[str, Any]] = []
    for pair_index, (scenario, repetition) in enumerate(pairs):
        first = (repetition - 1 + starts[scenario]) % 2
        order = (ARMS[first], ARMS[1 - first])
        pair_id = f"{scenario}-r{repetition:02d}"
        for arm_position, arm in enumerate(order):
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


QUALIFICATION_DIGEST_KEYS = (
    "runner",
    "config",
    "oracle",
    "coverage",
    "workspace",
    "candidate",
    "candidate_treatment",
)


def resolve_codex_command() -> list[str]:
    """Resolve one stable executable path for every cell in the run."""

    override = os.environ.get("CODEX_CLI")
    executable = override or shutil.which("codex")
    if not executable:
        raise RuntimeError("Codex CLI is unavailable; set CODEX_CLI")
    path = Path(executable).expanduser().resolve(strict=True)
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f"Codex CLI is not an executable regular file: {path}")
    return [str(path)]


def codex_command() -> list[str]:
    """Compatibility wrapper for callers that used the protocol-v3 name."""

    return resolve_codex_command()


def capture_codex_identity(command: list[str]) -> dict[str, str]:
    """Capture a self-consistent executable path, version, and entry digest."""

    if len(command) != 1:
        raise RuntimeError("Codex command must contain one resolved executable")
    path = Path(command[0]).resolve(strict=True)
    if str(path) != command[0] or not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError("Codex command is not the canonical executable path")
    digest_before = file_digest(path)
    version = subprocess.check_output(
        [str(path), "--version"],
        text=True,
        env=isolated_environment(Path.home(), Path.home() / ".codex"),
    ).strip()
    digest_after = file_digest(path)
    if digest_before != digest_after:
        raise RuntimeError("Codex CLI changed during identity capture")
    if not version:
        raise RuntimeError("Codex CLI returned an empty version")
    return {
        "resolved_path": str(path),
        "version": version,
        "entry_sha256": digest_before,
    }


def codex_identity_changes(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    keys = ("resolved_path", "version", "entry_sha256")
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in keys
        if before.get(key) != after.get(key)
    }


def build_qualification_identity(
    *,
    protocol_version: int,
    codex_identity: dict[str, str],
    input_digests: dict[str, str],
    config: dict[str, Any],
    seed: int,
    scenario_ids: list[str],
) -> dict[str, Any]:
    missing = [key for key in QUALIFICATION_DIGEST_KEYS if key not in input_digests]
    if missing:
        raise ValueError(f"qualification input digests are missing: {missing}")
    return {
        "protocol_version": protocol_version,
        "codex_identity": {
            key: codex_identity[key]
            for key in ("resolved_path", "version", "entry_sha256")
        },
        "input_snapshot_sha256": {
            key: input_digests[key] for key in QUALIFICATION_DIGEST_KEYS
        },
        "model": config["runner"]["model"],
        "reasoning_configuration": config["runner"]["extraArgs"],
        "skill_read_policy": config["runner"]["skillReadPolicy"],
        "seed": seed,
        "scenario_ids": list(scenario_ids),
    }


def qualification_identity_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return build_qualification_identity(
        protocol_version=int(metadata["protocol_version"]),
        codex_identity=metadata["codex_identity_before_schedule"],
        input_digests=metadata["input_snapshot_sha256"],
        config={
            "runner": {
                "model": metadata["model"],
                "extraArgs": metadata["reasoning_configuration"],
                "skillReadPolicy": metadata["skill_read_policy"],
            }
        },
        seed=int(metadata["seed"]),
        scenario_ids=metadata["scenario_ids"],
    )


def validate_qualification_metadata(
    *,
    path: Path,
    current_phase: str,
    current_identity: dict[str, Any],
    config: dict[str, Any],
    oracle: dict[str, Any] | None = None,
    candidate_root: Path = CANDIDATE_ROOT,
    workspace_validation_root: Path = WORKSPACE_ROOT,
) -> dict[str, Any]:
    """Validate runner-generated raw evidence before launching the next phase."""

    if current_phase not in {"pilot", "confirm"}:
        raise ValueError("only pilot or confirmation can consume qualification metadata")
    resolved = path.expanduser().resolve(strict=True)
    metadata = load_json(resolved)
    expected_prior_phase = "smoke" if current_phase == "pilot" else "pilot"
    expected_repetitions = repetitions_for_phase(config, expected_prior_phase)
    scenario_ids = current_identity["scenario_ids"]
    expected_pairs = len(scenario_ids) * expected_repetitions
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(metadata.get("schema") == "helixbox/automation-paired-run/2", "schema")
    require(
        metadata.get("protocol_version") == current_identity["protocol_version"],
        "protocol_version",
    )
    require(metadata.get("phase") == expected_prior_phase, "prior_phase")
    require(
        metadata.get("claim_label")
        == (
            "harness_smoke_only"
            if expected_prior_phase == "smoke"
            else "pilot_no_effect_claim"
        ),
        "claim_label",
    )
    require(metadata.get("repetitions") == expected_repetitions, "repetitions")
    require(metadata.get("seed") == current_identity["seed"], "seed")
    require(metadata.get("scenario_ids") == scenario_ids, "scenario_ids")
    require(metadata.get("scenario_count") == len(scenario_ids), "scenario_count")
    require(metadata.get("expected_pairs") == expected_pairs, "expected_pairs")
    require(metadata.get("complete_pairs") == expected_pairs, "complete_pairs")
    require(metadata.get("inputs_frozen_before_first_cell") is True, "input_freeze")
    require(
        metadata.get("auth_snapshot_frozen_before_first_cell") is True,
        "auth_freeze",
    )
    require(metadata.get("source_stable_during_run") is True, "source_stability")
    require(metadata.get("source_changes_during_run") == {}, "source_changes")
    require(metadata.get("codex_identity_stable_during_run") is True, "cli_stability")
    require(metadata.get("codex_identity_changes_during_run") == {}, "cli_changes")
    before_cli = metadata.get("codex_identity_before_schedule")
    after_cli = metadata.get("codex_identity_after_schedule")
    require(
        isinstance(before_cli, dict)
        and isinstance(after_cli, dict)
        and codex_identity_changes(before_cli, after_cli) == {},
        "cli_identity_fields",
    )
    require(metadata.get("run_integrity_failure") is False, "run_integrity")
    require(metadata.get("run_integrity_failures") == [], "run_integrity_failures")
    require(metadata.get("runner_exit_code") == 0, "runner_exit_code")
    failures.extend(
        qualification_bundle_failures(
            resolved,
            metadata,
            config,
            oracle=oracle or load_json(ORACLE_PATH),
            candidate_root=candidate_root,
            workspace_validation_root=workspace_validation_root,
        )
    )

    for arm in ("candidate", "control"):
        summary = metadata.get(arm)
        require(isinstance(summary, dict), f"{arm}_summary")
        if not isinstance(summary, dict):
            continue
        require(summary.get("cells") == expected_pairs, f"{arm}_cells")
        require(summary.get("hard_failures") == 0, f"{arm}_hard_failures")
        require(summary.get("integrity_failures") == 0, f"{arm}_integrity_failures")
        if arm == "candidate":
            require(
                summary.get("valid_outputs") == expected_pairs,
                "candidate_valid_outputs",
            )

    try:
        declared_identity = metadata.get("qualification_identity")
        recomputed_identity = qualification_identity_from_metadata(metadata)
        require(declared_identity == recomputed_identity, "declared_qualification_identity")
        declared_digest = metadata.get("qualification_identity_sha256")
        recomputed_digest = canonical_json_digest(recomputed_identity)
        require(declared_digest == recomputed_digest, "qualification_identity_digest")
        require(recomputed_identity == current_identity, "qualification_identity_match")
    except (KeyError, TypeError, ValueError) as error:
        failures.append(f"qualification_identity:{type(error).__name__}")
        recomputed_digest = ""

    if current_phase == "confirm":
        provenance = metadata.get("qualification")
        require(isinstance(provenance, dict), "smoke_qualification_provenance")
        if isinstance(provenance, dict):
            require(provenance.get("validated") is True, "smoke_qualification_validated")
            require(
                provenance.get("required_prior_phase") == "smoke",
                "smoke_qualification_phase",
            )
            require(
                provenance.get("qualification_identity_sha256")
                == recomputed_digest,
                "smoke_qualification_identity",
            )
            prior_path = provenance.get("prior_metadata_path")
            require(isinstance(prior_path, str), "smoke_qualification_path")
            if isinstance(prior_path, str):
                try:
                    revalidated = validate_qualification_metadata(
                        path=Path(prior_path),
                        current_phase="pilot",
                        current_identity=current_identity,
                        config=config,
                        oracle=oracle,
                        candidate_root=candidate_root,
                        workspace_validation_root=workspace_validation_root,
                    )
                    for key in (
                        "required_prior_phase",
                        "prior_run_id",
                        "prior_metadata_sha256",
                        "qualification_identity_sha256",
                    ):
                        require(
                            provenance.get(key) == revalidated.get(key),
                            f"smoke_qualification_chain:{key}",
                        )
                except (OSError, ValueError) as error:
                    failures.append(
                        f"smoke_qualification_chain:{type(error).__name__}"
                    )

    if failures:
        raise ValueError("qualification metadata failed: " + ", ".join(failures))
    return {
        "required_prior_phase": expected_prior_phase,
        "prior_run_id": metadata["run_id"],
        "prior_metadata_path": str(resolved),
        "prior_metadata_sha256": file_digest(resolved),
        "qualification_identity_sha256": recomputed_digest,
        "validated": True,
    }


def snapshot_auth(source: Path, destination: Path) -> None:
    """Copy one credential snapshot without following links or retaining its mode."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(source, flags)
    try:
        source_before = os.fstat(descriptor)
        if not stat.S_ISREG(source_before.st_mode):
            raise RuntimeError("Codex authentication source is not a regular file")
        if source_before.st_uid != os.getuid() or stat.S_IMODE(source_before.st_mode) & 0o077:
            raise RuntimeError("Codex authentication source ownership or mode is unsafe")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            payload = handle.read()
        source_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if not payload:
        raise RuntimeError("Codex authentication source is empty")
    identity_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(source_before, field) != getattr(source_after, field)
        for field in identity_fields
    ):
        raise RuntimeError("Codex authentication source changed during snapshot")
    try:
        auth_value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Codex authentication source is invalid JSON") from error
    if not isinstance(auth_value, dict):
        raise RuntimeError("Codex authentication source must contain a JSON object")
    destination.parent.mkdir(parents=True, exist_ok=True)
    output_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    output = os.open(destination, output_flags, 0o600)
    try:
        with os.fdopen(output, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(output)
    os.chmod(destination, 0o600)


def isolated_environment(task_home: Path, codex_home: Path) -> dict[str, str]:
    """Return an allowlisted environment for one isolated Codex cell."""

    allowed = ("LANG", "LC_ALL", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR")
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    environment["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    environment.setdefault("LANG", "C.UTF-8")
    environment["HOME"] = str(task_home)
    environment["CODEX_HOME"] = str(codex_home)
    return environment


def seed_home(
    destination: Path,
    auth_source: Path,
    arm: str,
    candidate_root: Path = CANDIDATE_ROOT,
) -> Path:
    """Create an auth-only control or an auth-plus-candidate-skills treatment."""

    codex_home = destination / ".codex"
    codex_home.mkdir(parents=True)
    snapshot_auth(auth_source, codex_home / "auth.json")
    if arm == "candidate-skills":
        skills_root = codex_home / "skills"
        skills_root.mkdir()
        for name in ("audit", "manage"):
            shutil.copytree(candidate_root / "skills" / name, skills_root / name)
        shutil.copytree(candidate_root / "references", codex_home / "references")
    elif arm != "no-skill":
        raise ValueError(f"unknown benchmark arm: {arm}")

    if (codex_home / "config.toml").exists() or (codex_home / "plugins").exists():
        raise RuntimeError("isolated benchmark home contains user config or plugins")
    return codex_home


def parse_usage(events_path: Path) -> dict[str, int] | None:
    usage: dict[str, int] | None = None
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidate = event.get("usage")
        if not isinstance(candidate, dict):
            continue
        usage = {
            "input_tokens": int(candidate.get("input_tokens", 0)),
            "cached_input_tokens": int(candidate.get("cached_input_tokens", 0)),
            "output_tokens": int(candidate.get("output_tokens", 0)),
        }
    return usage


def benchmark_prompt(user_input: str, config: dict[str, Any]) -> str:
    """Add one task-neutral file-access rule to both benchmark arms."""

    policy = config.get("runner", {}).get("skillReadPolicy")
    if policy != SKILL_READ_POLICY:
        raise ValueError("benchmark skill-read policy differs")
    return f"{user_input}\n\nBenchmark file-access rule: {policy}"


def parse_final_message(text: str) -> tuple[dict[str, Any] | None, str | None]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            stripped = "\n".join(lines[1:-1]).strip()
            if stripped.startswith("json\n"):
                stripped = stripped[5:]
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as error:
        return None, f"invalid_json:{error.msg}"
    if not isinstance(value, dict):
        return None, "final_output_not_object"
    return value, None


def score_output(
    output: dict[str, Any] | None,
    expected: dict[str, Any],
    scenario: str,
) -> dict[str, Any]:
    expected_map = expected["expected"]
    decisions: dict[str, str] = {}
    duplicate_ids: list[str] = []
    structure_valid = output is not None and set(output) == {
        "decisions",
        "evidence_paths",
        "rationale",
    }
    evidence_valid = False
    if output is not None:
        raw = output.get("decisions")
        if not isinstance(raw, list):
            structure_valid = False
        else:
            for item in raw:
                if not isinstance(item, dict) or set(item) != {"id", "disposition"}:
                    structure_valid = False
                    continue
                identifier = item.get("id")
                disposition = item.get("disposition")
                if not isinstance(identifier, str) or disposition not in {
                    "accept",
                    "change",
                    "defer",
                }:
                    structure_valid = False
                    continue
                if identifier in decisions:
                    duplicate_ids.append(identifier)
                    structure_valid = False
                    continue
                decisions[identifier] = disposition
        evidence_paths = output.get("evidence_paths")
        required_path = f"cases/{scenario}/evidence.md"
        allowed_paths = {
            required_path,
            f"cases/{scenario}/proposal.md",
        }
        paths_are_strings = bool(
            isinstance(evidence_paths, list)
            and all(isinstance(path, str) for path in evidence_paths)
        )
        evidence_valid = bool(
            paths_are_strings
            and required_path in evidence_paths
            and set(evidence_paths).issubset(allowed_paths)
            and len(evidence_paths) == len(set(evidence_paths))
        )
        if not isinstance(output.get("rationale"), str) or not output["rationale"].strip():
            structure_valid = False

    output_ids = set(decisions)
    expected_ids = set(expected_map)
    unknown_output_ids = sorted(output_ids - expected_ids)
    missing_output_ids = sorted(expected_ids - output_ids)
    valid = bool(
        structure_valid
        and evidence_valid
        and not duplicate_ids
        and not unknown_output_ids
        and not missing_output_ids
    )
    correct_ids = []
    for identifier, expected_disposition in expected_map.items():
        accepted = (
            {expected_disposition}
            if isinstance(expected_disposition, str)
            else set(expected_disposition)
        )
        if decisions.get(identifier) in accepted:
            correct_ids.append(identifier)
    correct_ids.sort()
    incorrect_ids = sorted(expected_ids - set(correct_ids))
    critical_violations = sorted(set(expected["critical_ids"]).intersection(incorrect_ids))
    overcontrol_errors = sorted(set(expected["overcontrol_ids"]).intersection(incorrect_ids))
    return {
        "valid": valid,
        "correct": len(correct_ids),
        "total": len(expected_ids),
        "accuracy": round(len(correct_ids) / len(expected_ids), 6),
        "incorrect_ids": incorrect_ids,
        "critical_violations": critical_violations,
        "overcontrol_errors": overcontrol_errors,
        "overcontrol_total": len(expected["overcontrol_ids"]),
        "duplicate_ids": sorted(set(duplicate_ids)),
        "unknown_output_ids": unknown_output_ids,
        "missing_output_ids": missing_output_ids,
        "evidence_valid": evidence_valid,
    }


def classify_failures(
    *,
    arm: str,
    exit_code: int,
    parse_error: str | None,
    score: dict[str, Any],
    workspace_changes: int,
    forbidden_events: list[str],
    routing_observed: bool,
) -> tuple[bool, bool, bool]:
    """Separate experiment integrity from arm behavior and candidate gating."""

    integrity_failure = bool(
        exit_code != 0
        or workspace_changes
        or forbidden_events
        or (arm == "no-skill" and not routing_observed)
    )
    behavioral_failure = bool(
        parse_error
        or not score["valid"]
        or score["critical_violations"]
        or (arm == "candidate-skills" and not routing_observed)
    )
    hard_failure = bool(
        integrity_failure
        or (arm == "candidate-skills" and behavioral_failure)
    )
    return integrity_failure, behavioral_failure, hard_failure


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    resolved = path.resolve(strict=False)
    return any(resolved == root or resolved.is_relative_to(root) for root in roots)


def _path_like(token: str, working_directory: Path) -> bool:
    return bool(
        token.startswith(("/", "~", "./", "../"))
        or "/" in token
        or (working_directory / token).exists()
    )


def _path_tokens(
    executable: str,
    arguments: list[str],
    working_directory: Path,
) -> list[str]:
    """Return likely file operands while excluding filters and format strings."""

    skip: set[int] = set()
    if executable == "sed":
        expression_supplied = False
        index = 0
        while index < len(arguments):
            token = arguments[index]
            if token in {"-e", "--expression"} and index + 1 < len(arguments):
                skip.add(index + 1)
                expression_supplied = True
                index += 2
                continue
            if token.startswith(("-e", "--expression=")):
                expression_supplied = True
            if token in {"-f", "--file"}:
                index += 2
                continue
            index += 1
        if not expression_supplied:
            for index, token in enumerate(arguments):
                if token == "--":
                    continue
                if not token.startswith("-"):
                    skip.add(index)
                    break
    elif executable == "rg":
        pattern_supplied = False
        index = 0
        while index < len(arguments):
            token = arguments[index]
            if token in {"-g", "--glob"} and index + 1 < len(arguments):
                skip.add(index + 1)
                index += 2
                continue
            if token in {"-e", "--regexp"} and index + 1 < len(arguments):
                skip.add(index + 1)
                pattern_supplied = True
                index += 2
                continue
            if (
                (token.startswith("-e") and not token.startswith("--") and token != "-e")
                or token.startswith("--regexp=")
                or token in {"-f", "--file", "--files"}
                or (token.startswith("-f") and not token.startswith("--") and token != "-f")
                or token.startswith("--file=")
            ):
                pattern_supplied = True
            index += 1
        if not pattern_supplied:
            for index, token in enumerate(arguments):
                if token == "--":
                    continue
                if not token.startswith("-"):
                    skip.add(index)
                    break
    elif executable == "jq":
        filter_file_supplied = any(
            token in {"-f", "--from-file"}
            or (token.startswith("-f") and not token.startswith("--") and token != "-f")
            or token.startswith("--from-file=")
            for token in arguments
        )
        if not filter_file_supplied:
            for index, token in enumerate(arguments):
                if token == "--":
                    continue
                if not token.startswith("-"):
                    skip.add(index)
                    break
    elif executable == "printf":
        for index, token in enumerate(arguments):
            if token == "--":
                continue
            if not token.startswith("-"):
                skip.add(index)
                break

    paths: list[str] = []
    for index, token in enumerate(arguments):
        if index in skip:
            continue
        if token.startswith("-"):
            if "=" in token:
                value = token.split("=", 1)[1]
                if _path_like(value, working_directory):
                    paths.append(value)
            else:
                embedded = re.search(r"(?:^-[A-Za-z]+)(/.*|\.\./.*)$", token)
                if embedded:
                    paths.append(embedded.group(1))
            continue
        if _path_like(token, working_directory):
            paths.append(token)
    return paths


def _sed_expressions(arguments: list[str]) -> list[str]:
    expressions: list[str] = []
    file_script = False
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token in {"-e", "--expression"} and index + 1 < len(arguments):
            expressions.append(arguments[index + 1])
            index += 2
            continue
        if token.startswith("-e") and token != "-e":
            expressions.append(token[2:])
        elif token.startswith("--expression="):
            expressions.append(token.split("=", 1)[1])
        elif token in {"-f", "--file"}:
            file_script = True
            index += 2
            continue
        elif token.startswith(("-f", "--file=")):
            file_script = True
        index += 1
    if not expressions and not file_script:
        for token in arguments:
            if token == "--":
                continue
            if not token.startswith("-"):
                expressions.append(token)
                break
    return expressions


SAFE_SED_PRINT_EXPRESSION = re.compile(
    r"^(?:[0-9]+|\$)(?:,(?:[0-9]+|\$))?p$"
)


def _shell_metacharacter_violations(
    command: str,
    *,
    allow_pipeline: bool = False,
) -> set[str]:
    """Detect active shell metacharacters without treating quoted data as code."""

    violations: set[str] = set()
    quote: str | None = None
    escaped = False
    for index, character in enumerate(command):
        if escaped:
            escaped = False
            continue
        if quote == "'":
            if character == "'":
                quote = None
            continue
        if character == "\\":
            escaped = True
            continue
        if quote == '"':
            if character == '"':
                quote = None
            elif character in {"`", "$"}:
                violations.add("shell_expansion")
            continue
        if character in {"'", '"'}:
            quote = character
        elif character in {"`", "$"}:
            violations.add("shell_expansion")
        elif character in {"*", "?", "[", "]", "(", ")", "{", "}"}:
            violations.add("shell_glob_or_grouping")
        elif character in {";", "&"} or (
            character == "|" and not allow_pipeline
        ):
            violations.add("shell_control_operator")
        elif character in {"<", ">"}:
            violations.add("shell_redirection")
    if quote is not None or escaped:
        violations.add("unparseable_shell")
    return violations


def _active_shell_punctuation(command: str) -> list[tuple[int, str]]:
    """Return unquoted and unescaped shell operator characters with positions."""

    active: list[tuple[int, str]] = []
    quote: str | None = None
    escaped = False
    for index, character in enumerate(command):
        if escaped:
            escaped = False
            continue
        if quote == "'":
            if character == "'":
                quote = None
            continue
        if character == "\\":
            escaped = True
            continue
        if quote == '"':
            if character == '"':
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character in ";&|<>":
            active.append((index, character))
    return active


def _has_zsh_equals_expansion(command: str) -> bool:
    """Return true when an active token starts with zsh's `=command` syntax."""

    quote: str | None = None
    quote_had_content = False
    escaped = False
    token_start = True
    for character in command:
        if escaped:
            escaped = False
            token_start = False
            continue
        if quote == "'":
            if character == "'":
                quote = None
                if quote_had_content:
                    token_start = False
            else:
                quote_had_content = True
                token_start = False
            continue
        if character == "\\":
            escaped = True
            token_start = False
            continue
        if quote == '"':
            if character == '"':
                quote = None
                if quote_had_content:
                    token_start = False
            else:
                quote_had_content = True
                token_start = False
            continue
        if character in {"'", '"'}:
            quote = character
            quote_had_content = False
        elif character.isspace() or character in ";&|<>":
            token_start = True
        else:
            if character == "=" and token_start:
                return True
            token_start = False
    return False


def _valid_rg_files_pipeline(
    segments: list[list[str]],
    working_directory: Path,
    workspace_validation_root: Path,
) -> bool:
    """Accept one replayable `rg --files PATH... | rg REGEX` pipeline."""

    if len(segments) != 2:
        return False
    producer, consumer = segments
    if (
        len(producer) < 3
        or producer[0] != "rg"
        or producer[1] != "--files"
    ):
        return False
    recorded_root = working_directory.resolve(strict=False)
    try:
        validation_root = workspace_validation_root.resolve(strict=True)
    except OSError:
        return False

    def lexical_relative(candidate: Path, root: Path) -> Path | None:
        normalized_root = Path(os.path.abspath(root))
        normalized_candidate = Path(os.path.abspath(candidate))
        root_parts = tuple(part.casefold() for part in normalized_root.parts)
        candidate_parts = tuple(
            part.casefold() for part in normalized_candidate.parts
        )
        if candidate_parts[: len(root_parts)] != root_parts:
            return None
        return Path(*normalized_candidate.parts[len(root_parts) :])

    def has_symlink_component(root: Path, relative: Path) -> bool:
        current = root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                return True
        return False

    mapped_paths: list[Path] = []
    for token in producer[2:]:
        if (
            not token
            or token.startswith(("-", "~"))
            or ".." in Path(token).parts
        ):
            return False
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = recorded_root / candidate
        relative = lexical_relative(candidate, recorded_root)
        if relative is None:
            return False
        if recorded_root.exists():
            if has_symlink_component(recorded_root, relative):
                return False
            try:
                resolved_candidate = candidate.resolve(strict=True)
                resolved_recorded = recorded_root.resolve(strict=True)
            except (OSError, ValueError):
                return False
            if not _inside(resolved_candidate, (resolved_recorded,)):
                return False
        else:
            if any(part == ".." for part in relative.parts):
                return False
        mapped_lexical = validation_root / relative
        if has_symlink_component(validation_root, relative):
            return False
        try:
            mapped = mapped_lexical.resolve(strict=True)
        except OSError:
            return False
        if not _inside(mapped, (validation_root,)):
            return False
        if mapped.is_file():
            if not os.access(mapped, os.R_OK):
                return False
        elif mapped.is_dir():
            walk_errors: list[OSError] = []
            for current, directories, files in os.walk(
                mapped,
                followlinks=False,
                onerror=walk_errors.append,
            ):
                current_path = Path(current)
                if not os.access(current_path, os.R_OK | os.X_OK):
                    return False
                for name in (*directories, *files):
                    child = current_path / name
                    if child.is_symlink() or (
                        child.is_file() and not os.access(child, os.R_OK)
                    ):
                        return False
            if walk_errors:
                return False
        else:
            return False
        mapped_paths.append(mapped)
    consumer_valid = (
        len(consumer) == 2
        and consumer[0] == "rg"
        and bool(consumer[1])
        and not consumer[1].startswith("-")
    )
    if not consumer_valid:
        return False
    rg_executable = shutil.which("rg")
    if rg_executable is None:
        return False
    try:
        producer_check = subprocess.run(
            [
                rg_executable,
                "--no-config",
                "--files",
                *(str(path) for path in mapped_paths),
            ],
            cwd=validation_root,
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return producer_check.returncode == 0


def scan_forbidden_events(
    events_path: Path,
    *,
    workspace_root: Path | None = None,
    readable_roots: tuple[Path, ...] = (),
    workspace_validation_root: Path | None = None,
) -> list[str]:
    """Fail closed on malformed events, external tools, and unsafe commands."""

    violations: set[str] = set()
    if not events_path.is_file():
        return ["missing_event_log"]
    lines = events_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return ["empty_event_log"]
    allowed_events = {
        "thread.started",
        "turn.started",
        "turn.completed",
        "item.started",
        "item.completed",
    }
    allowed_items = {"agent_message", "command_execution", "reasoning"}
    roots = tuple(root.resolve() for root in readable_roots)
    if workspace_root is not None:
        roots = (workspace_root.resolve(), *roots)
    for line_number, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            violations.add(f"invalid_event_json:{line_number}")
            continue
        if not isinstance(event, dict):
            violations.add(f"invalid_event_object:{line_number}")
            continue
        event_type = event.get("type")
        if event_type == "error":
            violations.add(f"error_event:{line_number}")
        elif event_type not in allowed_events:
            violations.add(f"unexpected_event_type:{event_type}")
        item = event.get("item")
        if event_type in {"item.started", "item.completed"} and not isinstance(item, dict):
            violations.add(f"missing_event_item:{line_number}")
            continue
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", "")).lower()
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            violations.add(f"invalid_item_id:{line_number}")
        if item_type not in allowed_items:
            violations.add(f"unexpected_item_type:{item_type or '<missing>'}")
        if any(marker in item_type for marker in ("mcp", "computer", "web_search", "tool_call")):
            violations.add(f"external_tool_type:{item_type}")
        names = " ".join(
            str(item.get(key, ""))
            for key in ("name", "tool", "tool_name", "server")
        ).lower()
        for term in FORBIDDEN_TOOL_TERMS:
            if term in names:
                violations.add(f"forbidden_tool:{term}")
        if item_type == "command_execution":
            command = item.get("command")
            if not isinstance(command, str) or not command.strip():
                violations.add(f"invalid_command_event:{line_number}")
                continue
            exit_code = item.get("exit_code")
            if event_type == "item.completed" and (
                not isinstance(exit_code, int) or isinstance(exit_code, bool)
            ):
                violations.add(f"invalid_command_exit_code:{line_number}")
            for violation in shell_command_violations(
                command,
                working_directory=workspace_root,
                readable_roots=roots,
                workspace_validation_root=workspace_validation_root,
            ):
                violations.add(f"forbidden_command:{violation}:{command[:160]}")
        elif item_type == "agent_message" and event_type == "item.completed":
            message = item.get("text")
            if not isinstance(message, str) or not message.strip():
                violations.add(f"invalid_agent_message:{line_number}")
    return sorted(violations)


def shell_command_violations(
    command: str,
    *,
    working_directory: Path | None = None,
    readable_roots: tuple[Path, ...] = (),
    workspace_validation_root: Path | None = None,
) -> list[str]:
    """Require a fail-closed read-only command and path surface."""

    violations: set[str] = set()
    try:
        outer = shlex.split(command)
    except ValueError:
        return sorted(
            _shell_metacharacter_violations(command) | {"unparseable_shell"}
        )
    inner = command
    if (
        len(outer) >= 3
        and outer[0] in {"/bin/bash", "/bin/sh", "/bin/zsh"}
        and outer[1] in {"-c", "-lc"}
    ):
        inner = outer[2]
        if len(outer) != 3:
            violations.add("shell_extra_arguments")
    if "\n" in inner or "\r" in inner:
        violations.add("multi_line_shell")
    active_punctuation = _active_shell_punctuation(inner)
    safe_pipeline = (
        len(active_punctuation) == 1
        and active_punctuation[0][1] == "|"
        and bool(inner[: active_punctuation[0][0]].strip())
        and bool(inner[active_punctuation[0][0] + 1 :].strip())
    )
    try:
        if safe_pipeline:
            pipe_index = active_punctuation[0][0]
            segments = [
                shlex.split(inner[:pipe_index]),
                shlex.split(inner[pipe_index + 1 :]),
            ]
        else:
            segments = [shlex.split(inner)]
    except ValueError:
        return sorted(
            violations
            | _shell_metacharacter_violations(inner)
            | {"unparseable_shell"}
        )

    violations.update(
        _shell_metacharacter_violations(
            inner,
            allow_pipeline=safe_pipeline,
        )
    )
    if _has_zsh_equals_expansion(inner):
        violations.add("shell_expansion")

    if any(character in ";&|" for _, character in active_punctuation) and not safe_pipeline:
        violations.add("shell_control_operator")
    if any(character in "<>" for _, character in active_punctuation):
        violations.add("shell_redirection")

    working = (working_directory or Path.cwd()).resolve()
    roots = tuple(root.resolve() for root in readable_roots)
    non_workspace_roots = tuple(
        root for root in roots if root != working and not root.is_relative_to(working)
    )
    validation_root = (workspace_validation_root or working).resolve(strict=False)
    if safe_pipeline and not _valid_rg_files_pipeline(
        segments,
        working,
        validation_root,
    ):
        violations.add("unsupported_pipeline")
    for segment in segments:
        if not segment:
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", segment[0]):
            violations.add("environment_assignment")
            continue
        executable_token = segment[0]
        executable = Path(executable_token).name
        if executable not in READ_ONLY_COMMANDS:
            violations.add(f"executable:{executable}")
        if "/" in executable_token and executable_token not in {
            f"/bin/{executable}",
            f"/usr/bin/{executable}",
        }:
            violations.add("executable_path")
        arguments = segment[1:]
        if executable in SAFE_COMMAND_OPTIONS:
            for token in arguments:
                if token == "--" or (
                    token.startswith("-")
                    and token not in SAFE_COMMAND_OPTIONS[executable]
                ):
                    violations.add(f"unsupported_{executable}_option")
        if executable in {"jq", "rg", "sed"} and any(
            token.startswith("-")
            and not token.startswith("--")
            and len(token) > 2
            for token in arguments
        ):
            violations.add("ambiguous_compact_short_options")
        if executable == "sed":
            expressions = _sed_expressions(arguments)
            if not expressions or any(
                SAFE_SED_PRINT_EXPRESSION.fullmatch(expression) is None
                for expression in expressions
            ):
                violations.add("unsafe_sed_command")
        path_tokens = _path_tokens(executable, arguments, working)
        for token in path_tokens:
            if Path(token).name in {"auth.json", "config.toml"}:
                violations.add("private_codex_state")
            if token.startswith("~"):
                violations.add(f"path_outside_allowlist:{token}")
                continue
            candidate = Path(token)
            if not candidate.is_absolute():
                candidate = working / candidate
            if roots and not _inside(candidate, roots):
                violations.add(f"path_outside_allowlist:{token}")
            if non_workspace_roots and _inside(candidate, non_workspace_roots):
                if (executable == "rg" and "--files" in arguments) or (
                    executable in {"ls", "rg"} and candidate.suffix != ".md"
                ):
                    violations.add("skill_parent_scan")

    if re.search(
        r"\bsed\b[^\n]*(?:(?:^|\s)-i(?:[^\s]*)|--in-place(?:\s|=|$))",
        inner,
    ):
        violations.add("in_place_sed")
    if re.search(r"\brg\b[^\n]*\s(?:--pre|--hostname-bin)(?:\s|=)", inner):
        violations.add("unsafe_rg_option")
    if re.search(r"\brg\b[^\n]*\s--ignore-file(?:\s|=)", inner):
        violations.add("unsafe_rg_option")
    if re.search(r"\bjq\b[^\n]*\s(?:--run-tests|--library-path|-L)(?:\s|=|$)", inner):
        violations.add("unsafe_jq_option")
    return sorted(violations)


def _canonical_command_segments(command: str) -> list[list[str]]:
    """Return quote-aware segments from one exact wrapper or direct command."""

    try:
        outer = shlex.split(command)
    except ValueError:
        return []
    if (
        len(outer) == 3
        and outer[0] in {"/bin/bash", "/bin/sh", "/bin/zsh"}
        and outer[1] in {"-c", "-lc"}
    ):
        inner = outer[2]
    else:
        inner = command
    punctuation = _active_shell_punctuation(inner)
    if not punctuation:
        raw_segments = [inner]
    elif len(punctuation) == 1 and punctuation[0][1] == "|":
        pipe_index = punctuation[0][0]
        raw_segments = [inner[:pipe_index], inner[pipe_index + 1 :]]
    else:
        return []
    try:
        segments = [shlex.split(segment) for segment in raw_segments]
    except ValueError:
        return []
    return segments if all(segments) else []


def _outputs_cover_text(outputs: list[str], expected: str) -> bool:
    """Return true when exact successful output spans cover the full source."""

    intervals: list[tuple[int, int]] = []
    for output in outputs:
        if expected in output:
            return True
        start = expected.find(output)
        if output and start >= 0:
            intervals.append((start, start + len(output)))
    cursor = 0
    for start, end in sorted(intervals):
        if start > cursor:
            break
        cursor = max(cursor, end)
    return cursor == len(expected)


def _path_identity_parts(path: Path) -> tuple[str, ...]:
    """Return a case-stable identity for the synthetic treatment tree."""

    return tuple(part.casefold() for part in path.parts)


def observed_treatment_reads(
    events_path: Path,
    *,
    workspace_root: Path,
    codex_home: Path,
    audit_skill_text: str,
    manage_skill_text: str,
) -> dict[str, bool]:
    """Observe canonical candidate access and complete target-skill reads."""

    result = {
        "audit_access": False,
        "manage_access": False,
        "reference_access": False,
        "treatment_access": False,
        "audit_loaded": False,
        "manage_loaded": False,
    }
    if not events_path.is_file():
        return result
    audit_path = (codex_home / "skills" / "audit" / "SKILL.md").resolve(
        strict=False
    )
    manage_path = (
        codex_home / "skills" / "manage" / "SKILL.md"
    ).resolve(strict=False)
    references_root = (codex_home / "references").resolve(strict=False)
    audit_identity = _path_identity_parts(audit_path)
    manage_identity = _path_identity_parts(manage_path)
    reference_identity = _path_identity_parts(references_root)
    audit_outputs: list[str] = []
    manage_outputs: list[str] = []
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item")
        if (
            event.get("type") != "item.completed"
            or not isinstance(item, dict)
            or item.get("type") != "command_execution"
        ):
            continue
        command = item.get("command")
        output = item.get("aggregated_output")
        if not isinstance(command, str):
            continue
        successful_output = (
            output
            if item.get("exit_code") == 0 and isinstance(output, str)
            else None
        )
        for tokens in _canonical_command_segments(command):
            executable = Path(tokens[0]).name
            if executable in {"printf", "pwd"}:
                continue
            content_reader = executable in {"cat", "cut", "head", "rg", "sed", "tail"}
            for token in _path_tokens(
                executable,
                tokens[1:],
                workspace_root.resolve(),
            ):
                candidate = Path(token)
                if not candidate.is_absolute():
                    candidate = workspace_root / candidate
                resolved = candidate.resolve(strict=False)
                identity = _path_identity_parts(resolved)
                if identity == audit_identity:
                    result["audit_access"] = True
                    if content_reader and successful_output is not None:
                        audit_outputs.append(successful_output)
                elif identity == manage_identity:
                    result["manage_access"] = True
                    if content_reader and successful_output is not None:
                        manage_outputs.append(successful_output)
                elif identity[: len(reference_identity)] == reference_identity:
                    result["reference_access"] = True
    result["treatment_access"] = bool(
        result["audit_access"]
        or result["manage_access"]
        or result["reference_access"]
    )
    result["audit_loaded"] = _outputs_cover_text(audit_outputs, audit_skill_text)
    result["manage_loaded"] = _outputs_cover_text(manage_outputs, manage_skill_text)
    return result


def run_arm(
    cell: dict[str, Any],
    *,
    command: list[str],
    auth_source: Path,
    run_root: Path,
    config: dict[str, Any],
    oracle: dict[str, Any],
    workspace_source: Path = WORKSPACE_ROOT,
    candidate_source: Path = CANDIDATE_ROOT,
) -> dict[str, Any]:
    arm_root = run_root / "raw" / cell["pair_id"] / cell["arm"]
    arm_root.mkdir(parents=True, exist_ok=False)
    events_path = arm_root / "codex-events.jsonl"
    stderr_path = arm_root / "codex.stderr.log"
    final_path = arm_root / "final-message.txt"
    user_input = next(
        scenario["userInput"]
        for scenario in config["scenarios"]
        if scenario["id"] == cell["scenario"]
    )
    prompt = benchmark_prompt(user_input, config)

    with tempfile.TemporaryDirectory(prefix="automation-benchmark-") as temporary:
        temporary_root = Path(temporary)
        workspace = temporary_root / "workspace"
        shutil.copytree(workspace_source, workspace)
        before_digest = workspace_digest(workspace)
        task_home = temporary_root / "task-home"
        codex_home = seed_home(
            task_home,
            auth_source,
            cell["arm"],
            candidate_root=candidate_source,
        )
        args = [
            *command,
            "exec",
            "--json",
            "--strict-config",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--skip-git-repo-check",
            "--disable",
            "multi_agent",
            "--disable",
            "apps",
            "--cd",
            str(workspace),
            "--sandbox",
            "read-only",
            "--config",
            'approval_policy="never"',
            "--config",
            'model_reasoning_effort="high"',
            "--model",
            config["runner"]["model"],
            "--output-schema",
            str(workspace / "review-output.schema.json"),
            "--output-last-message",
            str(final_path),
            prompt,
        ]
        started = time.monotonic()
        with events_path.open("w", encoding="utf-8") as events, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            try:
                completed = subprocess.run(
                    args,
                    cwd=workspace,
                    env=isolated_environment(task_home, codex_home),
                    text=True,
                    stdout=events,
                    stderr=stderr,
                    check=False,
                    timeout=600,
                )
            except subprocess.TimeoutExpired:
                stderr.write("benchmark cell timed out after 600 seconds\n")
                completed = subprocess.CompletedProcess(args, 124)
        duration_ms = round((time.monotonic() - started) * 1000)
        after_digest = workspace_digest(workspace)

        forbidden_events = scan_forbidden_events(
            events_path,
            workspace_root=workspace,
            readable_roots=(codex_home / "skills", codex_home / "references"),
        )

    final_text = final_path.read_text(encoding="utf-8") if final_path.is_file() else ""
    output, parse_error = parse_final_message(final_text)
    expected = oracle["scenarios"][cell["scenario"]]
    score = score_output(output, expected, cell["scenario"])
    workspace_changes = int(before_digest != after_digest)
    skill_root = candidate_source / "skills"
    treatment_reads = observed_treatment_reads(
        events_path,
        workspace_root=workspace,
        codex_home=codex_home,
        audit_skill_text=(skill_root / "audit" / "SKILL.md").read_text(
            encoding="utf-8"
        ),
        manage_skill_text=(skill_root / "manage" / "SKILL.md").read_text(
            encoding="utf-8"
        ),
    )
    audit_loaded = treatment_reads["audit_loaded"]
    manage_loaded = treatment_reads["manage_loaded"]
    expected_routing = expected["routing"]
    routing_observed = (
        not treatment_reads["treatment_access"]
        if cell["arm"] == "no-skill" or expected_routing == "none"
        else audit_loaded and not treatment_reads["manage_access"]
        if expected_routing == "audit"
        else manage_loaded
    )
    integrity_failure, behavioral_failure, hard_failure = classify_failures(
        arm=cell["arm"],
        exit_code=completed.returncode,
        parse_error=parse_error,
        score=score,
        workspace_changes=workspace_changes,
        forbidden_events=forbidden_events,
        routing_observed=routing_observed,
    )
    record = {
        **cell,
        "model": config["runner"]["model"],
        "sandbox": config["runner"]["sandbox"],
        "codex_exit_code": completed.returncode,
        "parse_error": parse_error,
        "workspace_change_count": workspace_changes,
        "workspace_digest_before": before_digest,
        "workspace_digest_after": after_digest,
        "guard_context": {
            "workspace_root": str(workspace),
            "readable_roots": [
                str(codex_home / "skills"),
                str(codex_home / "references"),
            ],
        },
        "forbidden_events": forbidden_events,
        "audit_skill_access_observed": treatment_reads["audit_access"],
        "audit_skill_load_observed": audit_loaded,
        "manage_skill_access_observed": treatment_reads["manage_access"],
        "manage_skill_load_observed": manage_loaded,
        "reference_access_observed": treatment_reads["reference_access"],
        "candidate_treatment_access_observed": treatment_reads["treatment_access"],
        "routing_observed": routing_observed,
        "integrity_failure": integrity_failure,
        "behavioral_failure": behavioral_failure,
        "hard_failure": hard_failure,
        "score": score,
        "usage": parse_usage(events_path),
        "duration_ms": duration_ms,
        "artifacts": {
            path.name: file_digest(path)
            for path in arm_root.iterdir()
            if path.is_file()
        },
    }
    (arm_root / "record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return record


def write_blind_bundle(run_root: Path, records: list[dict[str, Any]], run_id: str) -> None:
    blind_root = run_root / "blind"
    blind_root.mkdir()
    mapping: list[dict[str, Any]] = []
    for record in records:
        source = (
            run_root
            / "raw"
            / record["pair_id"]
            / record["arm"]
            / "final-message.txt"
        )
        if not source.is_file():
            continue
        opaque = hashlib.sha256(
            f"{run_id}:{record['pair_id']}:{record['arm']}".encode("utf-8")
        ).hexdigest()[:20]
        text = source.read_text(encoding="utf-8", errors="replace")
        for term in ("automation", "audit", "manage"):
            text = re.sub(term, "[target]", text, flags=re.I)
        destination = blind_root / f"{opaque}.json"
        destination.write_text(text, encoding="utf-8")
        mapping.append(
            {
                "opaque_output_id": opaque,
                "pair_id": record["pair_id"],
                "scenario": record["scenario"],
                "repetition": record["repetition"],
                "arm": record["arm"],
                "source_sha256": file_digest(source),
                "blind_sha256": file_digest(destination),
            }
        )
    (run_root / "unblinding-map.json").write_text(
        json.dumps(mapping, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def arm_summary(records: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    selected = [record for record in records if record["arm"] == arm]
    correct = sum(
        record["score"]["correct"] if record["score"]["valid"] else 0
        for record in selected
    )
    total = sum(record["score"]["total"] for record in selected)
    scenario_accuracy: dict[str, float] = {}
    for scenario in sorted({record["scenario"] for record in selected}):
        scenario_records = [record for record in selected if record["scenario"] == scenario]
        scenario_correct = sum(
            record["score"]["correct"] if record["score"]["valid"] else 0
            for record in scenario_records
        )
        scenario_total = sum(record["score"]["total"] for record in scenario_records)
        scenario_accuracy[scenario] = round(scenario_correct / scenario_total, 6)
    return {
        "arm": arm,
        "cells": len(selected),
        "valid_outputs": sum(record["score"]["valid"] for record in selected),
        "integrity_failures": sum(record["integrity_failure"] for record in selected),
        "behavioral_failures": sum(record["behavioral_failure"] for record in selected),
        "hard_failures": sum(record["hard_failure"] for record in selected),
        "critical_violations": sum(
            len(record["score"]["critical_violations"]) for record in selected
        ),
        "overcontrol_errors": sum(
            len(record["score"]["overcontrol_errors"]) for record in selected
        ),
        "overcontrol_total": sum(
            record["score"]["overcontrol_total"] for record in selected
        ),
        "overcontrol_error_rate": (
            round(
                sum(
                    len(record["score"]["overcontrol_errors"])
                    for record in selected
                )
                / sum(record["score"]["overcontrol_total"] for record in selected),
                6,
            )
            if sum(record["score"]["overcontrol_total"] for record in selected)
            else 0.0
        ),
        "accuracy": round(correct / total, 6) if total else None,
        "scenario_accuracy": scenario_accuracy,
    }


def paired_accuracy_interval(
    records: list[dict[str, Any]],
    *,
    seed: int,
    samples: int,
    confidence: float,
) -> dict[str, Any] | None:
    """Return a scenario-stratified paired bootstrap interval for accuracy uplift."""

    by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        by_pair.setdefault(record["pair_id"], {})[record["arm"]] = record
    by_scenario: dict[str, list[tuple[int, int, int, int]]] = {}
    for arms in by_pair.values():
        if set(arms) != set(ARMS):
            continue
        candidate = arms["candidate-skills"]
        control = arms["no-skill"]
        if candidate["scenario"] != control["scenario"]:
            raise ValueError("paired records disagree on scenario")
        candidate_correct = (
            candidate["score"]["correct"] if candidate["score"]["valid"] else 0
        )
        control_correct = (
            control["score"]["correct"] if control["score"]["valid"] else 0
        )
        by_scenario.setdefault(candidate["scenario"], []).append(
            (
                candidate_correct,
                candidate["score"]["total"],
                control_correct,
                control["score"]["total"],
            )
        )
    if not by_scenario or samples < 1 or not 0 < confidence < 1:
        return None

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
    for _ in range(samples):
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

    alpha = (1 - confidence) / 2
    return {
        "method": "scenario_stratified_paired_bootstrap",
        "confidence": confidence,
        "samples": samples,
        "seed": seed,
        "weighting": "proposition_weighted",
        "pairs": len(pairs),
        "estimate": round(estimate, 6),
        "lower": round(percentile(alpha), 6),
        "upper": round(percentile(1 - alpha), 6),
    }


def benchmark_conclusion(
    *,
    phase: str,
    repetitions: int,
    config: dict[str, Any],
    candidate: dict[str, Any],
    control: dict[str, Any],
    complete_pairs: int,
    expected_pairs: int,
    paired_interval: dict[str, Any] | None = None,
    source_stable: bool = True,
    run_integrity_failure: bool = False,
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
    if phase == "smoke":
        return "harness_smoke_only" if phase_ready else "harness_smoke_failed"
    if phase == "pilot":
        return "pilot_no_effect_claim" if phase_ready else "pilot_failed_no_effect_claim"
    measurement = config["measurement"]
    if repetitions != measurement["confirmationRepetitions"]:
        return "benchmark_local_effect_not_demonstrated"
    if not source_stable or run_integrity_failure:
        return "benchmark_local_effect_not_demonstrated"
    if complete_pairs != expected_pairs:
        return "benchmark_local_effect_not_demonstrated"
    if (
        candidate["cells"] != expected_pairs
        or control["cells"] != expected_pairs
        or candidate["valid_outputs"] != candidate["cells"]
        or candidate["hard_failures"]
        or control["hard_failures"]
    ):
        return "benchmark_local_effect_not_demonstrated"
    if control["accuracy"] is not None and control["accuracy"] >= measurement["controlCeiling"]:
        return "benchmark_control_ceiling_no_improvement_claim"
    uplift = round(candidate["accuracy"] - control["accuracy"], 6)
    interval_matches_uplift = bool(
        paired_interval is not None
        and paired_interval["estimate"] == uplift
    )
    no_scenario_regression = all(
        candidate["scenario_accuracy"][scenario]
        >= control["scenario_accuracy"][scenario]
        for scenario in candidate["scenario_accuracy"]
    )
    if (
        candidate["accuracy"] >= measurement["minimumCandidateAccuracy"]
        and uplift >= measurement["minimumAbsoluteUplift"]
        and candidate["overcontrol_error_rate"]
        <= measurement["maximumOvercontrolErrorRate"]
        and no_scenario_regression
        and interval_matches_uplift
        and paired_interval["lower"] > 0
    ):
        return "benchmark_local_effect_observed"
    return "benchmark_local_effect_not_demonstrated"


def qualification_bundle_failures(
    metadata_path: Path,
    metadata: dict[str, Any],
    config: dict[str, Any],
    *,
    oracle: dict[str, Any],
    candidate_root: Path,
    workspace_validation_root: Path,
) -> list[str]:
    """Re-derive one prior phase from its records and immutable raw artifacts."""

    failures: list[str] = []
    run_root = metadata_path.parent
    records_path = run_root / "records.json"
    map_path = run_root / "unblinding-map.json"
    if metadata_path.name != "metadata.json":
        failures.append("raw_bundle:metadata_filename")
    try:
        records = load_json_list(records_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return [*failures, "raw_bundle:records"]
    if metadata.get("records_sha256") != file_digest(records_path):
        failures.append("raw_bundle:records_sha256")
    if not map_path.is_file() or metadata.get("unblinding_map_sha256") != file_digest(map_path):
        failures.append("raw_bundle:unblinding_map_sha256")

    try:
        expected_schedule = build_schedule(
            metadata["scenario_ids"],
            int(metadata["repetitions"]),
            int(metadata["seed"]),
        )
    except (KeyError, TypeError, ValueError):
        return [*failures, "raw_bundle:schedule_fields"]
    schedule_fields = (
        "pair_id",
        "pair_index",
        "scenario",
        "repetition",
        "arm",
        "arm_position",
    )
    if len(records) != len(expected_schedule):
        failures.append("raw_bundle:record_count")
    try:
        audit_skill_text = (
            candidate_root / "skills" / "audit" / "SKILL.md"
        ).read_text(encoding="utf-8")
        manage_skill_text = (
            candidate_root / "skills" / "manage" / "SKILL.md"
        ).read_text(encoding="utf-8")
    except OSError:
        return [*failures, "raw_bundle:candidate_skill_sources"]
    for index, (record, expected) in enumerate(zip(records, expected_schedule, strict=False)):
        if any(record.get(key) != expected[key] for key in schedule_fields):
            failures.append(f"raw_bundle:schedule:{index}")
            continue
        arm_root = run_root / "raw" / record["pair_id"] / record["arm"]
        record_path = arm_root / "record.json"
        try:
            if load_json(record_path) != record:
                failures.append(f"raw_bundle:record_mismatch:{index}")
                continue
        except (OSError, ValueError, json.JSONDecodeError):
            failures.append(f"raw_bundle:record_missing:{index}")
            continue
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, dict) or not all(
            isinstance(name, str)
            and Path(name).name == name
            and isinstance(digest, str)
            for name, digest in artifacts.items()
        ):
            failures.append(f"raw_bundle:artifact_manifest:{index}")
            continue
        observed_files = {
            path.name
            for path in arm_root.iterdir()
            if path.is_file() and path.name != "record.json"
        }
        if set(artifacts) != observed_files:
            failures.append(f"raw_bundle:artifact_set:{index}")
            continue
        for name, digest in artifacts.items():
            if file_digest(arm_root / name) != digest:
                failures.append(f"raw_bundle:artifact_digest:{index}:{name}")

        guard_context = record.get("guard_context")
        if not isinstance(guard_context, dict):
            failures.append(f"raw_bundle:guard_context:{index}")
            continue
        workspace_value = guard_context.get("workspace_root")
        readable_values = guard_context.get("readable_roots")
        if not isinstance(workspace_value, str) or not (
            isinstance(readable_values, list)
            and len(readable_values) == 2
            and all(isinstance(value, str) for value in readable_values)
        ):
            failures.append(f"raw_bundle:guard_context:{index}")
            continue
        workspace = Path(workspace_value)
        codex_home = workspace.parent / "task-home" / ".codex"
        expected_roots = [
            str(codex_home / "skills"),
            str(codex_home / "references"),
        ]
        if (
            workspace.name != "workspace"
            or not workspace.parent.name.startswith("automation-benchmark-")
            or readable_values != expected_roots
        ):
            failures.append(f"raw_bundle:guard_root_shape:{index}")
            continue
        events_path = arm_root / "codex-events.jsonl"
        final_path = arm_root / "final-message.txt"
        final_text = final_path.read_text(encoding="utf-8", errors="replace")
        output, parse_error = parse_final_message(final_text)
        scenario = record["scenario"]
        expected_oracle = oracle.get("scenarios", {}).get(scenario)
        if not isinstance(expected_oracle, dict):
            failures.append(f"raw_bundle:oracle:{index}")
            continue
        score = score_output(output, expected_oracle, scenario)
        forbidden_events = scan_forbidden_events(
            events_path,
            workspace_root=workspace,
            readable_roots=tuple(Path(value) for value in readable_values),
            workspace_validation_root=workspace_validation_root,
        )
        treatment_reads = observed_treatment_reads(
            events_path,
            workspace_root=workspace,
            codex_home=codex_home,
            audit_skill_text=audit_skill_text,
            manage_skill_text=manage_skill_text,
        )
        audit_loaded = treatment_reads["audit_loaded"]
        manage_loaded = treatment_reads["manage_loaded"]
        expected_routing = expected_oracle["routing"]
        routing_observed = (
            not treatment_reads["treatment_access"]
            if record["arm"] == "no-skill" or expected_routing == "none"
            else audit_loaded and not treatment_reads["manage_access"]
            if expected_routing == "audit"
            else manage_loaded
        )
        before_digest = record.get("workspace_digest_before")
        after_digest = record.get("workspace_digest_after")
        if not isinstance(before_digest, str) or not isinstance(after_digest, str):
            failures.append(f"raw_bundle:workspace_digests:{index}")
            continue
        workspace_changes = int(before_digest != after_digest)
        exit_code = record.get("codex_exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            failures.append(f"raw_bundle:codex_exit_code:{index}")
            continue
        integrity_failure, behavioral_failure, hard_failure = classify_failures(
            arm=record["arm"],
            exit_code=exit_code,
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
            if record.get(field) != derived:
                failures.append(f"raw_bundle:semantic:{index}:{field}")

    expected_pairs = len(metadata.get("scenario_ids", [])) * int(
        metadata.get("repetitions", 0)
    )
    by_pair: dict[str, set[str]] = {}
    for record in records:
        pair_id = record.get("pair_id")
        arm = record.get("arm")
        if isinstance(pair_id, str) and isinstance(arm, str):
            by_pair.setdefault(pair_id, set()).add(arm)
    derived_complete_pairs = sum(arms == set(ARMS) for arms in by_pair.values())
    candidate = arm_summary(records, "candidate-skills")
    control = arm_summary(records, "no-skill")
    if metadata.get("expected_pairs") != expected_pairs:
        failures.append("raw_bundle:expected_pairs")
    if metadata.get("complete_pairs") != derived_complete_pairs:
        failures.append("raw_bundle:complete_pairs")
    if metadata.get("candidate") != candidate:
        failures.append("raw_bundle:candidate_summary")
    if metadata.get("control") != control:
        failures.append("raw_bundle:control_summary")

    paired_interval = paired_accuracy_interval(
        records,
        seed=int(metadata.get("seed", 0)),
        samples=int(config["measurement"]["bootstrapSamples"]),
        confidence=float(config["measurement"]["confidenceLevel"]),
    )
    if metadata.get("paired_accuracy_uplift_interval") != paired_interval:
        failures.append("raw_bundle:paired_interval")
    uplift = round(candidate["accuracy"] - control["accuracy"], 6)
    if metadata.get("absolute_accuracy_uplift") != uplift:
        failures.append("raw_bundle:accuracy_uplift")

    source_changed = bool(metadata.get("source_changes_during_run")) or (
        metadata.get("source_stable_during_run") is not True
    )
    before_cli = metadata.get("codex_identity_before_schedule")
    after_cli = metadata.get("codex_identity_after_schedule")
    cli_changed = not isinstance(before_cli, dict) or not isinstance(after_cli, dict)
    if not cli_changed:
        cli_changed = bool(codex_identity_changes(before_cli, after_cli))
    cli_changed = bool(
        cli_changed
        or metadata.get("codex_identity_changes_during_run")
        or metadata.get("codex_identity_stable_during_run") is not True
    )
    expected_integrity_failures = []
    if source_changed:
        expected_integrity_failures.append("benchmark_sources_changed_during_run")
    if cli_changed:
        expected_integrity_failures.append("codex_identity_changed_during_run")
    expected_run_integrity = bool(expected_integrity_failures)
    if metadata.get("run_integrity_failure") is not expected_run_integrity:
        failures.append("raw_bundle:run_integrity_failure")
    if metadata.get("run_integrity_failures") != expected_integrity_failures:
        failures.append("raw_bundle:run_integrity_failures")
    expected_exit = int(
        expected_run_integrity or any(record.get("hard_failure") is True for record in records)
    )
    if metadata.get("runner_exit_code") != expected_exit:
        failures.append("raw_bundle:runner_exit_code")
    expected_conclusion = benchmark_conclusion(
        phase=str(metadata.get("phase")),
        repetitions=int(metadata.get("repetitions", 0)),
        config=config,
        candidate=candidate,
        control=control,
        complete_pairs=derived_complete_pairs,
        expected_pairs=expected_pairs,
        paired_interval=paired_interval,
        source_stable=not source_changed,
        run_integrity_failure=expected_run_integrity,
    )
    if metadata.get("claim_label") != expected_conclusion:
        failures.append("raw_bundle:claim_label")
    return failures


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), *args], text=True
    ).strip()


def source_digests() -> dict[str, str]:
    return {
        "runner": file_digest(Path(__file__).resolve()),
        "config": file_digest(CONFIG_PATH),
        "oracle": file_digest(ORACLE_PATH),
        "coverage": file_digest(COVERAGE_PATH),
        "workspace": workspace_digest(WORKSPACE_ROOT),
        "candidate": workspace_digest(CANDIDATE_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("smoke", "pilot", "confirm"), default="smoke")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--scenario", action="append")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--qualification-metadata", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_preflight = source_digests()
    config = load_json(CONFIG_PATH)
    oracle = load_json(ORACLE_PATH)
    coverage = load_json(COVERAGE_PATH)
    if args.phase == "smoke" and args.qualification_metadata is not None:
        parser.error("smoke must not consume qualification metadata")
    if (
        args.phase in {"pilot", "confirm"}
        and not args.dry_run
        and args.qualification_metadata is None
    ):
        parser.error("pilot and confirmation require --qualification-metadata")
    if args.phase in {"pilot", "confirm"} and args.scenario and (
        not args.dry_run or args.qualification_metadata is not None
    ):
        parser.error("qualified pilot and confirmation require the full scenario set")
    preregistered_seed = int(config["measurement"]["preregisteredSeed"])
    seed = preregistered_seed if args.seed is None else args.seed
    if args.phase in {"pilot", "confirm"} and seed != preregistered_seed and (
        not args.dry_run or args.qualification_metadata is not None
    ):
        parser.error("qualified pilot and confirmation require the preregistered seed")
    scenarios = validate_definition(config, oracle, coverage, set(args.scenario or []))
    repetitions = repetitions_for_phase(config, args.phase)
    schedule = build_schedule(scenarios, repetitions, seed)
    if source_digests() != source_preflight:
        raise RuntimeError("benchmark sources changed during preflight; rerun")
    if args.dry_run:
        qualification = None
        launch_authorized = args.phase == "smoke"
        if args.qualification_metadata is not None:
            command = resolve_codex_command()
            cli_identity = capture_codex_identity(command)
            dry_snapshot = {
                **source_preflight,
                "candidate_treatment": treatment_digest(CANDIDATE_ROOT),
            }
            identity = build_qualification_identity(
                protocol_version=int(config["version"]),
                codex_identity=cli_identity,
                input_digests=dry_snapshot,
                config=config,
                seed=seed,
                scenario_ids=scenarios,
            )
            qualification = validate_qualification_metadata(
                path=args.qualification_metadata,
                current_phase=args.phase,
                current_identity=identity,
                config=config,
                oracle=oracle,
                candidate_root=CANDIDATE_ROOT,
                workspace_validation_root=WORKSPACE_ROOT,
            )
            launch_authorized = True
        print(
            json.dumps(
                {
                    "claim_label": (
                        "smoke_schedule_only"
                        if args.phase == "smoke"
                        else "pilot_schedule_only"
                        if args.phase == "pilot"
                        else "confirmation_schedule_only"
                    ),
                    "dry_run": True,
                    "phase": args.phase,
                    "seed": seed,
                    "repetitions": repetitions,
                    "scenarios": scenarios,
                    "schedule": schedule,
                    "qualification": qualification,
                    "launch_authorized": launch_authorized,
                },
                indent=2,
            )
        )
        return 0

    auth_source = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json"
    command = resolve_codex_command()
    codex_identity_before = capture_codex_identity(command)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_root = (args.output_dir or RUNS_ROOT / run_id).resolve()
    if run_root.is_relative_to(WORKSPACE_ROOT.resolve()) or run_root.is_relative_to(
        CANDIDATE_ROOT.resolve()
    ):
        raise ValueError("benchmark output must stay outside runtime and fixture inputs")
    run_root.mkdir(parents=True, exist_ok=False)

    source_start = source_preflight
    records: list[dict[str, Any]] = []
    qualification: dict[str, Any] | None = None
    with tempfile.TemporaryDirectory(
        prefix="automation-frozen-inputs-"
    ) as temporary:
        frozen_root = Path(temporary)
        frozen_workspace = frozen_root / "workspace"
        frozen_candidate = frozen_root / "candidate"
        frozen_control = frozen_root / "control"
        frozen_auth = frozen_root / "auth.json"
        frozen_control.mkdir()
        snapshot_auth(auth_source, frozen_auth)
        shutil.copytree(WORKSPACE_ROOT, frozen_workspace, symlinks=True)
        shutil.copytree(CANDIDATE_ROOT, frozen_candidate, symlinks=True)
        for source in (CONFIG_PATH, ORACLE_PATH, COVERAGE_PATH):
            shutil.copy2(source, frozen_control / source.name)

        source_after_snapshot = source_digests()
        if source_after_snapshot != source_start:
            raise RuntimeError("benchmark sources changed while inputs were frozen; rerun")
        config = load_json(frozen_control / CONFIG_PATH.name)
        oracle = load_json(frozen_control / ORACLE_PATH.name)
        coverage = load_json(frozen_control / COVERAGE_PATH.name)
        frozen_scenarios = validate_definition(
            config,
            oracle,
            coverage,
            set(args.scenario or []),
            workspace_root=frozen_workspace,
        )
        if frozen_scenarios != scenarios:
            raise RuntimeError("frozen scenario set differs from the preflight")
        schedule = build_schedule(frozen_scenarios, repetitions, seed)
        snapshot_digests = {
            "runner": source_start["runner"],
            "config": file_digest(frozen_control / CONFIG_PATH.name),
            "oracle": file_digest(frozen_control / ORACLE_PATH.name),
            "coverage": file_digest(frozen_control / COVERAGE_PATH.name),
            "workspace": workspace_digest(frozen_workspace),
            "candidate": workspace_digest(frozen_candidate),
            "candidate_treatment": treatment_digest(frozen_candidate),
        }
        for name in ("runner", "config", "oracle", "coverage", "workspace", "candidate"):
            if snapshot_digests[name] != source_start[name]:
                raise RuntimeError(f"frozen {name} digest differs from source preflight")

        qualification_identity = build_qualification_identity(
            protocol_version=int(config["version"]),
            codex_identity=codex_identity_before,
            input_digests=snapshot_digests,
            config=config,
            seed=seed,
            scenario_ids=frozen_scenarios,
        )
        qualification_identity_sha256 = canonical_json_digest(qualification_identity)
        if args.qualification_metadata is not None:
            qualification = validate_qualification_metadata(
                path=args.qualification_metadata,
                current_phase=args.phase,
                current_identity=qualification_identity,
                config=config,
                oracle=oracle,
                candidate_root=frozen_candidate,
                workspace_validation_root=frozen_workspace,
            )

        for cell in schedule:
            record = run_arm(
                cell,
                command=command,
                auth_source=frozen_auth,
                run_root=run_root,
                config=config,
                oracle=oracle,
                workspace_source=frozen_workspace,
                candidate_source=frozen_candidate,
            )
            records.append(record)
            print(
                json.dumps(
                    {
                        "pair_id": record["pair_id"],
                        "arm": record["arm"],
                        "integrity_failure": record["integrity_failure"],
                        "behavioral_failure": record["behavioral_failure"],
                        "hard_failure": record["hard_failure"],
                        "accuracy": record["score"]["accuracy"],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    postflight_error: str | None = None
    try:
        codex_identity_after = capture_codex_identity(command)
        cli_changes = codex_identity_changes(
            codex_identity_before,
            codex_identity_after,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        postflight_error = f"{type(error).__name__}:{error}"
        codex_identity_after = {
            "resolved_path": command[0],
            "version": None,
            "entry_sha256": None,
            "capture_error": postflight_error,
        }
        cli_changes = {
            "capture_error": {
                "before": None,
                "after": postflight_error,
            }
        }
    cli_stable = not cli_changes

    source_end = source_digests()
    source_changes = {
        name: {"start": source_start[name], "end": source_end[name]}
        for name in source_start
        if source_start[name] != source_end[name]
    }
    source_stable = not source_changes
    run_integrity_failures: list[str] = []
    if not source_stable:
        run_integrity_failures.append("benchmark_sources_changed_during_run")
    if not cli_stable:
        run_integrity_failures.append("codex_identity_changed_during_run")
    run_integrity_failure = bool(run_integrity_failures)

    by_pair: dict[str, set[str]] = {}
    for record in records:
        by_pair.setdefault(record["pair_id"], set()).add(record["arm"])
    complete_pairs = sum(arms == set(ARMS) for arms in by_pair.values())
    expected_pairs = len(scenarios) * repetitions
    candidate = arm_summary(records, "candidate-skills")
    control = arm_summary(records, "no-skill")
    paired_interval = paired_accuracy_interval(
        records,
        seed=seed,
        samples=int(config["measurement"]["bootstrapSamples"]),
        confidence=float(config["measurement"]["confidenceLevel"]),
    )
    conclusion = benchmark_conclusion(
        phase=args.phase,
        repetitions=repetitions,
        config=config,
        candidate=candidate,
        control=control,
        complete_pairs=complete_pairs,
        expected_pairs=expected_pairs,
        paired_interval=paired_interval,
        source_stable=source_stable,
        run_integrity_failure=run_integrity_failure,
    )
    runner_exit_code = int(
        run_integrity_failure or any(record["hard_failure"] for record in records)
    )
    write_blind_bundle(run_root, records, run_id)
    records_payload = json.dumps(records, indent=2, sort_keys=True) + "\n"
    records_sha256 = hashlib.sha256(records_payload.encode("utf-8")).hexdigest()
    unblinding_map_sha256 = file_digest(run_root / "unblinding-map.json")
    metadata = {
        "schema": "helixbox/automation-paired-run/2",
        "protocol_version": int(config["version"]),
        "created_at": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "phase": args.phase,
        "claim_label": conclusion,
        "seed": seed,
        "repetitions": repetitions,
        "scenario_ids": scenarios,
        "scenario_count": len(scenarios),
        "complete_pairs": complete_pairs,
        "expected_pairs": expected_pairs,
        "candidate": candidate,
        "control": control,
        "absolute_accuracy_uplift": round(
            candidate["accuracy"] - control["accuracy"], 6
        ),
        "paired_accuracy_uplift_interval": paired_interval,
        "inputs_frozen_before_first_cell": True,
        "auth_snapshot_frozen_before_first_cell": True,
        "source_stable_during_run": source_stable,
        "source_changes_during_run": source_changes,
        "codex_identity_before_schedule": codex_identity_before,
        "codex_identity_after_schedule": codex_identity_after,
        "codex_identity_stable_during_run": cli_stable,
        "codex_identity_changes_during_run": cli_changes,
        "qualification_identity": qualification_identity,
        "qualification_identity_sha256": qualification_identity_sha256,
        "qualification": qualification,
        "run_integrity_failure": run_integrity_failure,
        "run_integrity_failures": run_integrity_failures,
        "runner_exit_code": runner_exit_code,
        "records_sha256": records_sha256,
        "unblinding_map_sha256": unblinding_map_sha256,
        "repository_head": git_output("rev-parse", "HEAD"),
        "repository_status": git_output("status", "--short"),
        "codex_command": command,
        "codex_version": codex_identity_before["version"],
        "codex_entry_sha256": codex_identity_before["entry_sha256"],
        "input_snapshot_sha256": snapshot_digests,
        "runner_sha256": snapshot_digests["runner"],
        "candidate_plugin_sha256": snapshot_digests["candidate"],
        "candidate_treatment_sha256": snapshot_digests["candidate_treatment"],
        "config_sha256": snapshot_digests["config"],
        "oracle_sha256": snapshot_digests["oracle"],
        "coverage_sha256": snapshot_digests["coverage"],
        "workspace_sha256": snapshot_digests["workspace"],
        "model": config["runner"]["model"],
        "reasoning_configuration": config["runner"]["extraArgs"],
        "skill_read_policy": config["runner"]["skillReadPolicy"],
        "environment": (
            "allowlisted process; auth-only no-skill home or auth plus the two "
            "candidate skill trees and shared references; one frozen auth snapshot; "
            "frozen workspace and treatment snapshots; scoring files outside all "
            "allowed command roots"
        ),
        "oracle_boundary": (
            "Hidden from the model workspace and permitted command surface. The "
            "guard rejects jq and dynamic module loading. This is a harness boundary, "
            "not cryptographic isolation from the host."
        ),
        "claim_boundary": (
            "Synthetic proposition classification only; no real scheduler, "
            "inventory, mutation, readback, pause, drain, or timing claim."
        ),
    }
    (run_root / "records.json").write_text(
        records_payload, encoding="utf-8"
    )
    (run_root / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(run_root)
    return runner_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
