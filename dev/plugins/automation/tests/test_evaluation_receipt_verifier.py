"""Synthetic tamper checks for the evaluation receipt verifier."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).parents[4]
SCRIPT = (
    REPO_ROOT
    / "dev"
    / "plugins"
    / "automation"
    / "scripts"
    / "verify_evaluation_receipt.py"
)
SPEC = importlib.util.spec_from_file_location("automation_receipt_verifier", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load test module: {SCRIPT}")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def workspace_digest(root: Path) -> str:
    result = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        status = path.lstat()
        result.update(relative.encode("utf-8"))
        result.update(b"\0")
        result.update(oct(status.st_mode).encode("ascii"))
        result.update(b"\0")
        if path.is_symlink():
            result.update(b"L\0")
            result.update(os.readlink(path).encode("utf-8"))
        elif path.is_dir():
            result.update(b"D")
        elif path.is_file():
            result.update(b"F\0")
            result.update(path.read_bytes())
        else:
            result.update(b"O")
        result.update(b"\0")
    return result.hexdigest()


def treatment_digest(candidate_root: Path) -> str:
    result = hashlib.sha256()
    roots = (
        candidate_root / "skills" / "audit",
        candidate_root / "skills" / "manage",
        candidate_root / "references",
    )
    for root in roots:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(candidate_root).as_posix()
            result.update(relative.encode("utf-8"))
            result.update(b"\0")
            result.update(path.read_bytes())
            result.update(b"\0")
    return result.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def arm_summary(records: list[dict[str, object]], arm: str) -> dict[str, object]:
    selected = [record for record in records if record["arm"] == arm]
    correct = sum(
        int(record["score"]["correct"]) if record["score"]["valid"] else 0  # type: ignore[index]
        for record in selected
    )
    total = sum(int(record["score"]["total"]) for record in selected)  # type: ignore[index]
    scenarios = sorted({str(record["scenario"]) for record in selected})
    scenario_accuracy = {}
    for scenario in scenarios:
        values = [record for record in selected if record["scenario"] == scenario]
        scenario_correct = sum(
            int(record["score"]["correct"]) if record["score"]["valid"] else 0  # type: ignore[index]
            for record in values
        )
        scenario_total = sum(int(record["score"]["total"]) for record in values)  # type: ignore[index]
        scenario_accuracy[scenario] = round(scenario_correct / scenario_total, 6)
    overcontrol_errors = sum(len(record["score"]["overcontrol_errors"]) for record in selected)  # type: ignore[index]
    overcontrol_total = sum(int(record["score"]["overcontrol_total"]) for record in selected)  # type: ignore[index]
    return {
        "arm": arm,
        "cells": len(selected),
        "valid_outputs": sum(bool(record["score"]["valid"]) for record in selected),  # type: ignore[index]
        "integrity_failures": sum(bool(record["integrity_failure"]) for record in selected),
        "behavioral_failures": sum(bool(record["behavioral_failure"]) for record in selected),
        "hard_failures": sum(bool(record["hard_failure"]) for record in selected),
        "critical_violations": sum(len(record["score"]["critical_violations"]) for record in selected),  # type: ignore[index]
        "overcontrol_errors": overcontrol_errors,
        "overcontrol_total": overcontrol_total,
        "overcontrol_error_rate": round(overcontrol_errors / overcontrol_total, 6),
        "accuracy": round(correct / total, 6),
        "scenario_accuracy": scenario_accuracy,
    }


class SyntheticRun:
    def __init__(self, base: Path) -> None:
        self.root = base / "raw-run"
        self.root.mkdir()
        (self.root / "raw").mkdir()
        (self.root / "blind").mkdir()
        self.oracle_path = base / "oracle.json"
        self.candidate_root = base / "candidate"
        audit_text = "---\nname: audit\n---\n\n# Synthetic audit\n"
        manage_text = "---\nname: manage\n---\n\n# Synthetic manage\n"
        for name, text in (
            ("audit", audit_text),
            ("manage", manage_text),
        ):
            skill = self.candidate_root / "skills" / name / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(text, encoding="utf-8")
        references = self.candidate_root / "references"
        references.mkdir()
        (references / "fixture.md").write_text("# Fixture\n", encoding="utf-8")
        oracle = {
            "schema": "helixbox/automation-hidden-oracle/1",
            "scenarios": {
                scenario: {
                    "routing": "audit" if scenario == "case-04" else "none",
                    "expected": {f"P-{scenario}": "accept"},
                    "critical_ids": [],
                    "overcontrol_ids": [f"P-{scenario}"],
                }
                for scenario in ("case-04", "case-11")
            },
        }
        write_json(self.oracle_path, oracle)
        workspace = base / "automation-benchmark-fixture" / "workspace"
        codex_home = workspace.parent / "task-home" / ".codex"
        self.run_id = "20260722T120000Z"
        self.records: list[dict[str, object]] = []
        for scenario in ("case-04", "case-11"):
            pair_id = f"{scenario}-r01"
            for arm in verifier.ARMS:
                audit_loaded = arm == "candidate-skills" and scenario == "case-04"
                cell = self.root / "raw" / pair_id / arm
                cell.mkdir(parents=True)
                events = cell / "codex-events.jsonl"
                event_lines = [
                    json.dumps({"type": "thread.started", "thread_id": "thread-1"})
                    ,
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "id": "item-1",
                                "type": "command_execution",
                                "command": f'/bin/zsh -lc "sed -n \'1,20p\' cases/{scenario}/evidence.md"',
                                "aggregated_output": "fixture",
                                "exit_code": 0,
                                "status": "completed",
                            },
                        }
                    ),
                ]
                if audit_loaded:
                    event_lines.append(
                        json.dumps(
                            {
                                "type": "item.completed",
                                "item": {
                                    "id": "item-skill",
                                    "type": "command_execution",
                                    "command": (
                                        "/bin/zsh -lc \"sed -n '1,80p' "
                                        f"{codex_home}/skills/audit/SKILL.md\""
                                    ),
                                    "aggregated_output": audit_text,
                                    "exit_code": 0,
                                    "status": "completed",
                                },
                            }
                        )
                    )
                events.write_text("\n".join(event_lines) + "\n", encoding="utf-8")
                (cell / "codex.stderr.log").write_text("", encoding="utf-8")
                proposition = f"P-{scenario}"
                (cell / "final-message.txt").write_text(
                    json.dumps(
                        {
                            "decisions": [
                                {"id": proposition, "disposition": "accept"}
                            ],
                            "evidence_paths": [f"cases/{scenario}/evidence.md"],
                            "rationale": "Synthetic fixture.",
                        },
                        separators=(",", ":"),
                    )
                    + "\n",
                    encoding="utf-8",
                )
                record: dict[str, object] = {
                    "pair_id": pair_id,
                    "pair_index": len(self.records) // 2,
                    "arm_position": 0 if arm == "candidate-skills" else 1,
                    "scenario": scenario,
                    "repetition": 1,
                    "arm": arm,
                    "model": "gpt-5.6-sol",
                    "sandbox": "read-only",
                    "codex_exit_code": 0,
                    "parse_error": None,
                    "workspace_change_count": 0,
                    "forbidden_events": [],
                    "audit_skill_access_observed": audit_loaded,
                    "audit_skill_load_observed": audit_loaded,
                    "manage_skill_access_observed": False,
                    "manage_skill_load_observed": False,
                    "reference_access_observed": False,
                    "candidate_treatment_access_observed": audit_loaded,
                    "routing_observed": True,
                    "integrity_failure": False,
                    "behavioral_failure": False,
                    "hard_failure": False,
                    "score": {
                        "valid": True,
                        "correct": 1,
                        "total": 1,
                        "accuracy": 1.0,
                        "critical_violations": [],
                        "overcontrol_errors": [],
                        "overcontrol_total": 1,
                        "incorrect_ids": [],
                        "duplicate_ids": [],
                        "unknown_output_ids": [],
                        "missing_output_ids": [],
                        "evidence_valid": True,
                    },
                    "workspace_digest_before": "b" * 64,
                    "workspace_digest_after": "b" * 64,
                    "guard_context": {
                        "workspace_root": str(workspace),
                        "readable_roots": [
                            str(codex_home / "skills"),
                            str(codex_home / "references"),
                        ],
                    },
                    "artifacts": {},
                }
                self.records.append(record)

        self.metadata: dict[str, object] = {
            "schema": "helixbox/automation-paired-run/1",
            "run_id": self.run_id,
            "phase": "smoke",
            "claim_label": "harness_smoke_only",
            "seed": 94271,
            "repetitions": 1,
            "scenario_count": 2,
            "expected_pairs": 2,
            "complete_pairs": 2,
            "inputs_frozen_before_first_cell": True,
            "source_stable_during_run": True,
            "source_changes_during_run": {},
            "model": "gpt-5.6-sol",
            "reasoning_configuration": [
                "--strict-config",
                "--config",
                'model_reasoning_effort="high"',
            ],
        }
        self.receipt: dict[str, object] = {
            "schema": "helixbox/automation-evaluation-receipt/1",
            "runId": self.run_id,
            "phase": "smoke-routing-probe",
            "protocolVersion": 3,
            "result": "opposed_routing_probe_passed",
            "processExitCode": 0,
            "model": "gpt-5.6-sol",
            "reasoningEffort": "high",
            "seed": 94271,
            "repetitions": 1,
            "expectedPairs": 2,
            "completePairs": 2,
            "cells": 4,
            "sourceStableDuringRun": True,
            "candidate": {},
            "control": {},
            "artifacts": {"ephemeralRoot": str(self.root)},
        }
        self.receipt_path = base / "receipt.json"
        self.refresh()

    def refresh(self) -> None:
        for record in self.records:
            cell = self.root / "raw" / str(record["pair_id"]) / str(record["arm"])
            record["artifacts"] = {
                path.name: digest(path)
                for path in cell.iterdir()
                if path.is_file() and path.name != "record.json"
            }
            write_json(cell / "record.json", record)
        write_json(self.root / "records.json", self.records)
        candidate = arm_summary(self.records, "candidate-skills")
        control = arm_summary(self.records, "no-skill")
        self.metadata["candidate"] = candidate
        self.metadata["control"] = control
        self.metadata["absolute_accuracy_uplift"] = round(
            float(candidate["accuracy"]) - float(control["accuracy"]), 6
        )
        self.metadata["paired_accuracy_uplift_interval"] = {
            "method": "scenario_stratified_paired_bootstrap",
            "confidence": 0.95,
            "samples": 5000,
            "seed": 94271,
            "weighting": "proposition_weighted",
            "pairs": 2,
            "estimate": 0.0,
            "lower": 0.0,
            "upper": 0.0,
        }

        mapping = []
        for record in self.records:
            pair_id = str(record["pair_id"])
            arm = str(record["arm"])
            opaque = hashlib.sha256(f"{self.run_id}:{pair_id}:{arm}".encode()).hexdigest()[:20]
            source = self.root / "raw" / pair_id / arm / "final-message.txt"
            blind = self.root / "blind" / f"{opaque}.json"
            blind.write_bytes(source.read_bytes())
            mapping.append(
                {
                    "opaque_output_id": opaque,
                    "pair_id": pair_id,
                    "scenario": record["scenario"],
                    "repetition": record["repetition"],
                    "arm": arm,
                    "source_sha256": digest(source),
                    "blind_sha256": digest(blind),
                }
            )
        write_json(self.root / "unblinding-map.json", mapping)
        if str(self.metadata["schema"]).endswith("/2"):
            self.metadata["records_sha256"] = digest(self.root / "records.json")
            self.metadata["unblinding_map_sha256"] = digest(
                self.root / "unblinding-map.json"
            )
        write_json(self.root / "metadata.json", self.metadata)

        for arm_name, receipt_name in (
            ("candidate", "candidate"),
            ("control", "control"),
        ):
            summary = self.metadata[arm_name]
            assert isinstance(summary, dict)
            self.receipt[receipt_name] = {
                "cells": summary["cells"],
                "accuracy": summary["accuracy"],
                "validOutputs": summary["valid_outputs"],
                "behavioralFailures": summary["behavioral_failures"],
                "hardFailures": summary["hard_failures"],
                "integrityFailures": summary["integrity_failures"],
                "criticalViolations": summary["critical_violations"],
            }
        candidate_receipt = self.receipt["candidate"]
        assert isinstance(candidate_receipt, dict)
        candidate_receipt["case04PositiveRoutingFailures"] = 0
        candidate_receipt["case11NegativeRoutingFailures"] = 0
        artifacts = self.receipt["artifacts"]
        assert isinstance(artifacts, dict)
        artifacts.update(
            {
                "metadataSha256": digest(self.root / "metadata.json"),
                "recordsSha256": digest(self.root / "records.json"),
                "unblindingMapSha256": digest(self.root / "unblinding-map.json"),
            }
        )
        if str(self.receipt["schema"]).endswith("/2"):
            input_digests = self.metadata["input_snapshot_sha256"]
            assert isinstance(input_digests, dict)
            artifacts.update(
                {
                    "candidatePluginSha256": input_digests["candidate"],
                    "candidateTreatmentSha256": input_digests[
                        "candidate_treatment"
                    ],
                    "runnerSha256": input_digests["runner"],
                    "configSha256": input_digests["config"],
                    "oracleSha256": input_digests["oracle"],
                    "coverageSha256": input_digests["coverage"],
                    "workspaceSha256": input_digests["workspace"],
                }
            )
            interval = self.metadata["paired_accuracy_uplift_interval"]
            assert isinstance(interval, dict)
            self.receipt["pairedAccuracyUplift"] = {
                "estimate": interval["estimate"],
                "lower95": interval["lower"],
                "upper95": interval["upper"],
            }
            self.receipt["claimBoundary"] = {
                "scope": self.metadata["claim_boundary"],
                "rawClaimLabel": self.metadata["claim_label"],
                "manageSkillRoutingVerified": False,
                "realAutomationMutationVerified": False,
            }
        write_json(self.receipt_path, self.receipt)

    def enable_v4(self) -> None:
        benchmark_config = json.loads(verifier.CONFIG_PATH.read_text(encoding="utf-8"))
        benchmark_runner = benchmark_config["runner"]
        identity = {
            "resolved_path": "/synthetic/codex",
            "version": "codex-cli synthetic-v4",
            "entry_sha256": "a" * 64,
        }
        input_digests = {
            "runner": digest(verifier.BENCHMARK_RUNNER_PATH),
            "config": digest(verifier.CONFIG_PATH),
            "oracle": digest(self.oracle_path),
            "coverage": digest(verifier.COVERAGE_PATH),
            "workspace": workspace_digest(verifier.WORKSPACE_ROOT),
            "candidate": workspace_digest(self.candidate_root),
            "candidate_treatment": treatment_digest(self.candidate_root),
        }
        qualification_identity = {
            "protocol_version": verifier.CURRENT_PROTOCOL_VERSION,
            "codex_identity": identity,
            "input_snapshot_sha256": input_digests,
            "model": benchmark_runner["model"],
            "reasoning_configuration": benchmark_runner["extraArgs"],
            "skill_read_policy": benchmark_runner["skillReadPolicy"],
            "seed": 94271,
            "scenario_ids": ["case-04", "case-11"],
        }
        self.metadata.update(
            {
                "schema": "helixbox/automation-paired-run/2",
                "protocol_version": verifier.CURRENT_PROTOCOL_VERSION,
                "scenario_ids": ["case-04", "case-11"],
                "auth_snapshot_frozen_before_first_cell": True,
                "codex_identity_before_schedule": identity,
                "codex_identity_after_schedule": dict(identity),
                "codex_identity_stable_during_run": True,
                "codex_identity_changes_during_run": {},
                "run_integrity_failure": False,
                "run_integrity_failures": [],
                "runner_exit_code": 0,
                "codex_version": identity["version"],
                "codex_entry_sha256": identity["entry_sha256"],
                "input_snapshot_sha256": input_digests,
                "model": benchmark_runner["model"],
                "reasoning_configuration": benchmark_runner["extraArgs"],
                "skill_read_policy": benchmark_runner["skillReadPolicy"],
                "qualification_identity": qualification_identity,
                "qualification_identity_sha256": canonical_digest(qualification_identity),
                "qualification": None,
                "runner_sha256": input_digests["runner"],
                "config_sha256": input_digests["config"],
                "oracle_sha256": input_digests["oracle"],
                "coverage_sha256": input_digests["coverage"],
                "workspace_sha256": input_digests["workspace"],
                "candidate_plugin_sha256": input_digests["candidate"],
                "candidate_treatment_sha256": input_digests["candidate_treatment"],
                "claim_boundary": (
                    "Synthetic proposition classification only; no real scheduler, "
                    "inventory, mutation, readback, pause, drain, or timing claim."
                ),
            }
        )
        self.receipt["schema"] = "helixbox/automation-evaluation-receipt/2"
        self.receipt["protocolVersion"] = verifier.CURRENT_PROTOCOL_VERSION
        self.receipt["scenarioCount"] = 2
        self.receipt["codexIdentity"] = {
            "version": identity["version"],
            "entrySha256": identity["entry_sha256"],
        }
        artifacts = self.receipt["artifacts"]
        assert isinstance(artifacts, dict)
        artifacts.update(
            {
                "candidatePluginSha256": input_digests["candidate"],
                "candidateTreatmentSha256": input_digests["candidate_treatment"],
                "runnerSha256": input_digests["runner"],
                "configSha256": input_digests["config"],
            }
        )
        self.refresh()

    def set_event_text(self, pair_id: str, arm: str, text: str) -> None:
        path = self.root / "raw" / pair_id / arm / "codex-events.jsonl"
        path.write_text(text, encoding="utf-8")
        self.refresh()


class EvaluationReceiptVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.run = SyntheticRun(Path(self.temporary.name))

    def verify_v4(self) -> dict[str, object]:
        return verifier.verify_receipt(
            self.run.receipt_path,
            oracle_path=self.run.oracle_path,
            candidate_root=self.run.candidate_root,
        )

    def test_accepts_complete_v1_receipt_and_raw_run(self) -> None:
        summary = verifier.verify_receipt(self.run.receipt_path)

        self.assertTrue(summary["verified"])
        self.assertEqual(2, summary["pairs"])
        self.assertEqual(4, summary["cells"])
        self.assertEqual(0, summary["candidateCase04PositiveRoutingFailures"])
        self.assertEqual(0, summary["candidateCase11NegativeRoutingFailures"])

    def test_accepts_paired_v2_schemas_with_explicit_protocol_version(self) -> None:
        self.run.enable_v4()

        summary = self.verify_v4()

        self.assertEqual(verifier.CURRENT_PROTOCOL_VERSION, summary["protocolVersion"])

    def test_rejects_unknown_receipt_schema(self) -> None:
        self.run.receipt["schema"] = "helixbox/automation-evaluation-receipt/3"
        write_json(self.run.receipt_path, self.run.receipt)

        with self.assertRaisesRegex(verifier.VerificationError, "unsupported receipt schema"):
            verifier.verify_receipt(self.run.receipt_path)

    def test_rejects_v4_raw_with_legacy_receipt_schema(self) -> None:
        self.run.enable_v4()
        self.run.receipt["schema"] = "helixbox/automation-evaluation-receipt/1"
        write_json(self.run.receipt_path, self.run.receipt)

        with self.assertRaisesRegex(verifier.VerificationError, "schema pairing"):
            self.verify_v4()

    def test_rejects_v4_smoke_with_forged_qualification(self) -> None:
        self.run.enable_v4()
        self.run.metadata["qualification"] = {"validated": True}
        self.run.refresh()

        with self.assertRaisesRegex(verifier.VerificationError, "must not contain qualification"):
            self.verify_v4()

    def test_rejects_synchronized_v4_source_alias_and_receipt_tamper(self) -> None:
        self.run.enable_v4()
        forged_digest = "c" * 64
        self.run.metadata["candidate_plugin_sha256"] = forged_digest
        write_json(self.run.root / "metadata.json", self.run.metadata)
        artifacts = self.run.receipt["artifacts"]
        assert isinstance(artifacts, dict)
        artifacts["candidatePluginSha256"] = forged_digest
        artifacts["metadataSha256"] = digest(self.run.root / "metadata.json")
        write_json(self.run.receipt_path, self.run.receipt)

        with self.assertRaisesRegex(
            verifier.VerificationError,
            "candidate_plugin_sha256 input snapshot binding",
        ):
            self.verify_v4()

    def test_rejects_v4_claim_boundary_overclaim(self) -> None:
        self.run.enable_v4()
        boundary = self.run.receipt["claimBoundary"]
        assert isinstance(boundary, dict)
        boundary["realAutomationMutationVerified"] = True
        write_json(self.run.receipt_path, self.run.receipt)

        with self.assertRaisesRegex(verifier.VerificationError, "claimBoundary mismatch"):
            self.verify_v4()

    def test_rejects_self_bound_skill_policy_that_differs_from_config(self) -> None:
        self.run.enable_v4()
        forged_policy = "Use a forged policy."
        self.run.metadata["skill_read_policy"] = forged_policy
        identity = self.run.metadata["qualification_identity"]
        assert isinstance(identity, dict)
        identity["skill_read_policy"] = forged_policy
        self.run.metadata["qualification_identity_sha256"] = canonical_digest(identity)
        self.run.refresh()

        with self.assertRaisesRegex(
            verifier.VerificationError,
            "metadata.skill_read_policy versus benchmark config",
        ):
            self.verify_v4()

    def test_rejects_unknown_v4_top_level_claim(self) -> None:
        self.run.enable_v4()
        self.run.receipt["provesRealSchedulerSafety"] = True
        write_json(self.run.receipt_path, self.run.receipt)

        with self.assertRaisesRegex(verifier.VerificationError, "top-level fields mismatch"):
            self.verify_v4()

    def test_rejects_unknown_v4_nested_candidate_claim(self) -> None:
        self.run.enable_v4()
        candidate = self.run.receipt["candidate"]
        assert isinstance(candidate, dict)
        candidate["realSchedulerSafe"] = True
        write_json(self.run.receipt_path, self.run.receipt)

        with self.assertRaisesRegex(verifier.VerificationError, "candidate fields mismatch"):
            self.verify_v4()

    def test_v4_rederives_score_from_final_message_after_hash_refresh(self) -> None:
        self.run.enable_v4()
        final_message = (
            self.run.root
            / "raw"
            / "case-04-r01"
            / "candidate-skills"
            / "final-message.txt"
        )
        final_message.write_text(
            json.dumps(
                {
                    "decisions": [
                        {"id": "P-case-04", "disposition": "change"}
                    ],
                    "evidence_paths": ["cases/case-04/evidence.md"],
                    "rationale": "Synchronized tamper.",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.run.refresh()

        with self.assertRaisesRegex(verifier.VerificationError, "schema-2 semantic record .*score"):
            self.verify_v4()

    def test_v4_qualification_recursively_verifies_bound_prior_bundle(self) -> None:
        self.run.enable_v4()
        prior_metadata_path = self.run.root / "metadata.json"
        current = json.loads(json.dumps(self.run.metadata))
        current["phase"] = "pilot"
        current["qualification"] = {
            "required_prior_phase": "smoke",
            "prior_run_id": self.run.run_id,
            "prior_metadata_path": str(prior_metadata_path),
            "prior_metadata_sha256": digest(prior_metadata_path),
            "qualification_identity_sha256": current[
                "qualification_identity_sha256"
            ],
            "validated": True,
        }

        verifier._validate_v4_qualification(
            current,
            root=self.run.root,
            oracle_path=self.run.oracle_path,
            candidate_root=self.run.candidate_root,
            visited=set(),
        )

        final_message = (
            self.run.root
            / "raw"
            / "case-04-r01"
            / "candidate-skills"
            / "final-message.txt"
        )
        final_message.write_text(
            json.dumps(
                {
                    "decisions": [
                        {"id": "P-case-04", "disposition": "change"}
                    ],
                    "evidence_paths": ["cases/case-04/evidence.md"],
                    "rationale": "Tampered prior.",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.run.refresh()
        current["qualification"]["prior_metadata_sha256"] = digest(
            prior_metadata_path
        )
        with self.assertRaisesRegex(verifier.VerificationError, "schema-2 semantic record .*score"):
            verifier._validate_v4_qualification(
                current,
                root=self.run.root,
                oracle_path=self.run.oracle_path,
                candidate_root=self.run.candidate_root,
                visited=set(),
            )

    def test_v4_cli_drift_forces_run_integrity_failure_and_nonzero_exit(self) -> None:
        self.run.enable_v4()
        before = self.run.metadata["codex_identity_before_schedule"]
        assert isinstance(before, dict)
        after = dict(before)
        after["version"] = "codex-cli changed-v4"
        self.run.metadata.update(
            {
                "codex_identity_after_schedule": after,
                "codex_identity_stable_during_run": False,
                "codex_identity_changes_during_run": {
                    "version": {
                        "before": before["version"],
                        "after": after["version"],
                    }
                },
                "run_integrity_failure": True,
                "run_integrity_failures": ["codex_identity_changed_during_run"],
                "runner_exit_code": 1,
                "claim_label": "harness_smoke_failed",
            }
        )
        self.run.receipt["processExitCode"] = 1
        self.run.receipt["result"] = "opposed_routing_probe_failed"
        self.run.refresh()

        summary = self.verify_v4()
        self.assertTrue(summary["verified"])
        self.assertEqual(0, summary["hardFailures"])

        self.run.metadata["runner_exit_code"] = 0
        self.run.receipt["processExitCode"] = 0
        self.run.refresh()
        with self.assertRaisesRegex(verifier.VerificationError, "runner_exit_code mismatch"):
            self.verify_v4()

    def test_recomputes_confirmation_conclusion_instead_of_trusting_labels(self) -> None:
        self.run.metadata["phase"] = "confirm"
        self.run.metadata["claim_label"] = "benchmark_local_effect_observed"
        self.run.receipt["phase"] = "confirm"
        self.run.receipt["result"] = "benchmark_local_effect_observed"
        self.run.receipt["scenarioCount"] = 2
        self.run.refresh()

        with self.assertRaisesRegex(verifier.VerificationError, "metadata.claim_label mismatch"):
            verifier.verify_receipt(self.run.receipt_path)

    def test_rejects_synchronized_paired_interval_tamper(self) -> None:
        altered = {
            "method": "scenario_stratified_paired_bootstrap",
            "confidence": 0.95,
            "samples": 5000,
            "seed": 94271,
            "weighting": "proposition_weighted",
            "pairs": 2,
            "estimate": 0.5,
            "lower": 0.4,
            "upper": 0.6,
        }
        self.run.metadata["paired_accuracy_uplift_interval"] = altered
        write_json(self.run.root / "metadata.json", self.run.metadata)
        self.run.receipt["pairedAccuracyUplift"] = {
            "estimate": 0.5,
            "lower95": 0.4,
            "upper95": 0.6,
        }
        artifacts = self.run.receipt["artifacts"]
        assert isinstance(artifacts, dict)
        artifacts["metadataSha256"] = digest(self.run.root / "metadata.json")
        write_json(self.run.receipt_path, self.run.receipt)

        with self.assertRaisesRegex(
            verifier.VerificationError, "paired_accuracy_uplift_interval mismatch"
        ):
            verifier.verify_receipt(self.run.receipt_path)

    def test_rejects_top_level_metadata_tamper(self) -> None:
        metadata_path = self.run.root / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["seed"] = 1
        write_json(metadata_path, metadata)

        with self.assertRaisesRegex(verifier.VerificationError, "metadataSha256 mismatch"):
            verifier.verify_receipt(self.run.receipt_path)

    def test_rejects_per_cell_artifact_tamper(self) -> None:
        final_message = (
            self.run.root
            / "raw"
            / "case-04-r01"
            / "candidate-skills"
            / "final-message.txt"
        )
        final_message.write_text("tampered\n", encoding="utf-8")

        with self.assertRaisesRegex(verifier.VerificationError, "artifact digest"):
            verifier.verify_receipt(self.run.receipt_path)

    def test_rejects_jq_even_when_all_artifact_hashes_are_refreshed(self) -> None:
        event = {
            "type": "item.completed",
            "item": {
                "id": "item-jq",
                "type": "command_execution",
                "command": "/bin/zsh -lc \"jq 'include \\\"helpers\\\"; .' fixture.json\"",
                "aggregated_output": "{}",
                "exit_code": 0,
            },
        }
        self.run.set_event_text(
            "case-04-r01",
            "candidate-skills",
            json.dumps(event) + "\n",
        )

        with self.assertRaisesRegex(verifier.VerificationError, "jq use is forbidden"):
            verifier.verify_receipt(self.run.receipt_path)

    def test_rejects_malformed_event_even_when_hashes_are_refreshed(self) -> None:
        self.run.set_event_text(
            "case-04-r01",
            "candidate-skills",
            "{not-json}\n",
        )

        with self.assertRaisesRegex(verifier.VerificationError, "malformed event JSON"):
            verifier.verify_receipt(self.run.receipt_path)

    def test_v4_rejects_unrecorded_negative_case_reference_access(self) -> None:
        self.run.enable_v4()
        record = next(
            item
            for item in self.run.records
            if item["pair_id"] == "case-11-r01"
            and item["arm"] == "candidate-skills"
        )
        guard_context = record["guard_context"]
        assert isinstance(guard_context, dict)
        readable_roots = guard_context["readable_roots"]
        assert isinstance(readable_roots, list)
        reference_path = Path(str(readable_roots[1])) / "contract.md"
        event = {
            "type": "item.completed",
            "item": {
                "id": "item-reference",
                "type": "command_execution",
                "command": f"cat {reference_path}",
                "aggregated_output": "Candidate reference.\n",
                "exit_code": 0,
            },
        }
        self.run.set_event_text(
            "case-11-r01",
            "candidate-skills",
            json.dumps(event) + "\n",
        )

        with self.assertRaisesRegex(
            verifier.VerificationError,
            "reference_access_observed",
        ):
            self.verify_v4()

    def test_rejects_receipt_routing_count_not_derived_from_cells(self) -> None:
        candidate = self.run.receipt["candidate"]
        assert isinstance(candidate, dict)
        candidate["case04PositiveRoutingFailures"] = 1
        write_json(self.run.receipt_path, self.run.receipt)

        with self.assertRaisesRegex(verifier.VerificationError, "case04PositiveRoutingFailures"):
            verifier.verify_receipt(self.run.receipt_path)

    def test_rejects_success_result_with_nonzero_process_exit_code(self) -> None:
        self.run.receipt["processExitCode"] = 1
        write_json(self.run.receipt_path, self.run.receipt)

        with self.assertRaisesRegex(verifier.VerificationError, "processExitCode mismatch"):
            verifier.verify_receipt(self.run.receipt_path)

    def test_rejects_incomplete_raw_cell_directories(self) -> None:
        cell = self.run.root / "raw" / "case-11-r01" / "no-skill"
        for path in cell.iterdir():
            path.unlink()
        cell.rmdir()

        with self.assertRaisesRegex(verifier.VerificationError, "raw arms"):
            verifier.verify_receipt(self.run.receipt_path)


if __name__ == "__main__":
    unittest.main()
