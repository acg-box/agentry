"""Deterministic tests for the Automation management contract."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).parents[4]
DEV_ROOT = REPO_ROOT / "dev" / "plugins" / "automation"
SCRIPT = DEV_ROOT / "scripts" / "manage_contract.py"
SPEC = importlib.util.spec_from_file_location("manage_contract", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load test module: {SCRIPT}")
contract = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = contract
SPEC.loader.exec_module(contract)


class AutomationLifecycleManageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition = {
            "name": "synthetic-nightly",
            "prompt": "Write one harmless synthetic receipt.",
            "project": "disposable-project",
            "schedule": {"cadence": "daily", "business_timezone": "UTC"},
            "notification": {"enabled": False},
            "metadata": {"owner": "test", "purpose": "contract"},
        }
        self.create_authority = contract.MutationAuthority(
            project="disposable-project",
            actions=frozenset({"create"}),
            create_names=frozenset({"synthetic-nightly"}),
        )

    @staticmethod
    def manage_authority(stable_id: str) -> object:
        return contract.MutationAuthority(
            project="disposable-project",
            actions=frozenset({"update", "activate", "pause", "delete"}),
            task_ids=frozenset({stable_id}),
        )

    def test_full_authorized_lifecycle_requires_readback_and_quiescence(self) -> None:
        control = contract.InMemoryAutomationControlPlane()
        created = control.create_paused(
            self.definition, authority=self.create_authority
        )
        stable_id = created["stable_id"]
        authority = self.manage_authority(stable_id)

        self.assertEqual("task-0001", stable_id)
        self.assertEqual("paused", created["status"])
        self.assertEqual(created, control.view(stable_id))
        prior = control.view(stable_id)
        requested = deepcopy(prior)
        requested["prompt"] = "Write one updated harmless synthetic receipt."
        updated = control.update_full(
            requested,
            authority=authority,
            requested_changes={"prompt": requested["prompt"]},
        )
        for field in contract.TASK_FIELDS - {"prompt", "revision"}:
            self.assertEqual(prior[field], updated[field])
        self.assertEqual(prior["revision"] + 1, updated["revision"])
        self.assertEqual(updated, control.view(stable_id))

        run = control.activate_once(stable_id, authority=authority)
        self.assertEqual(stable_id, run["task_id"])
        self.assertEqual("running", run["state"])
        paused = control.pause(stable_id, authority=authority)
        self.assertEqual("paused", paused["status"])
        self.assertEqual(contract.Quiescence.ACTIVE, control.quiescence(stable_id))
        with self.assertRaisesRegex(contract.ContractViolation, "known_active"):
            control.delete(
                stable_id,
                authority=authority,
                retention_complete=True,
                consumers_clear=True,
            )

        completed = control.complete_run(run["run_id"], "succeeded")
        self.assertEqual("succeeded", completed["state"])
        self.assertEqual(
            contract.Quiescence.QUIESCENT, control.quiescence(stable_id)
        )
        self.assertEqual(
            {"stable_id": stable_id, "result": "deleted"},
            control.delete(
                stable_id,
                authority=authority,
                retention_complete=True,
                consumers_clear=True,
            ),
        )
        with self.assertRaisesRegex(contract.ContractViolation, "unknown stable task ID"):
            control.view(stable_id)

    def test_every_mutation_requires_explicit_exact_authority(self) -> None:
        control = contract.InMemoryAutomationControlPlane()
        with self.assertRaisesRegex(contract.ContractViolation, "explicit mutation"):
            control.create_paused(self.definition, authority=None)
        wrong_create = contract.MutationAuthority(
            project="disposable-project",
            actions=frozenset({"create"}),
            create_names=frozenset({"another-task"}),
        )
        with self.assertRaisesRegex(contract.ContractViolation, "exact target"):
            control.create_paused(self.definition, authority=wrong_create)

        created = control.create_paused(
            self.definition, authority=self.create_authority
        )
        stable_id = created["stable_id"]
        wrong_target = contract.MutationAuthority(
            project="disposable-project",
            actions=frozenset({"update", "activate", "pause", "delete"}),
            task_ids=frozenset({"task-9999"}),
        )
        operations = (
            lambda: control.update_full(
                created,
                authority=None,
                requested_changes={"prompt": created["prompt"]},
            ),
            lambda: control.activate_once(stable_id, authority=None),
            lambda: control.pause(stable_id, authority=None),
            lambda: control.delete(
                stable_id,
                authority=None,
                retention_complete=True,
                consumers_clear=True,
            ),
            lambda: control.delete(
                stable_id,
                authority=wrong_target,
                retention_complete=True,
                consumers_clear=True,
            ),
        )
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(contract.ContractViolation):
                    operation()

    def test_duplicate_partial_update_and_stale_writer_fail_closed(self) -> None:
        control = contract.InMemoryAutomationControlPlane()
        created = control.create_paused(
            self.definition, authority=self.create_authority
        )
        stable_id = created["stable_id"]
        authority = self.manage_authority(stable_id)
        with self.assertRaisesRegex(contract.ContractViolation, "duplicate"):
            control.create_paused(self.definition, authority=self.create_authority)

        partial = control.view(stable_id)
        del partial["notification"]
        with self.assertRaisesRegex(contract.ContractViolation, "full definition"):
            control.update_full(
                partial,
                authority=authority,
                requested_changes={"prompt": partial["prompt"]},
            )

        first_writer = control.view(stable_id)
        stale_writer = control.view(stable_id)
        first_writer["prompt"] = "First writer."
        control.update_full(
            first_writer,
            authority=authority,
            requested_changes={"prompt": first_writer["prompt"]},
        )
        stale_writer["prompt"] = "Stale writer."
        with self.assertRaisesRegex(contract.ContractViolation, "stale task revision"):
            control.update_full(
                stale_writer,
                authority=authority,
                requested_changes={"prompt": stale_writer["prompt"]},
            )

    def test_update_rejects_unrequested_loss_and_name_collision(self) -> None:
        control = contract.InMemoryAutomationControlPlane()
        created = control.create_paused(
            self.definition, authority=self.create_authority
        )
        stable_id = created["stable_id"]
        authority = self.manage_authority(stable_id)

        lossy = control.view(stable_id)
        lossy["prompt"] = "Requested prompt."
        lossy["notification"] = {"enabled": True}
        with self.assertRaisesRegex(contract.ContractViolation, "unchanged field"):
            control.update_full(
                lossy,
                authority=authority,
                requested_changes={"prompt": lossy["prompt"]},
            )

        second_definition = deepcopy(self.definition)
        second_definition["name"] = "synthetic-other"
        second_create = contract.MutationAuthority(
            project="disposable-project",
            actions=frozenset({"create"}),
            create_names=frozenset({"synthetic-other"}),
        )
        control.create_paused(second_definition, authority=second_create)
        collision = control.view(stable_id)
        collision["name"] = "synthetic-other"
        with self.assertRaisesRegex(contract.ContractViolation, "duplicate"):
            control.update_full(
                collision,
                authority=authority,
                requested_changes={"name": "synthetic-other"},
            )

    def test_unknown_quiescence_and_incomplete_retention_block_delete(self) -> None:
        unknown_surface = contract.InMemoryAutomationControlPlane(
            run_state_supported=False
        )
        created = unknown_surface.create_paused(
            self.definition, authority=self.create_authority
        )
        stable_id = created["stable_id"]
        authority = self.manage_authority(stable_id)
        self.assertEqual(
            contract.Quiescence.UNKNOWN, unknown_surface.quiescence(stable_id)
        )
        with self.assertRaisesRegex(contract.ContractViolation, "unknown"):
            unknown_surface.delete(
                stable_id,
                authority=authority,
                retention_complete=True,
                consumers_clear=True,
            )

        known_surface = contract.InMemoryAutomationControlPlane()
        created = known_surface.create_paused(
            self.definition, authority=self.create_authority
        )
        stable_id = created["stable_id"]
        authority = self.manage_authority(stable_id)
        with self.assertRaisesRegex(contract.ContractViolation, "retention"):
            known_surface.delete(
                stable_id,
                authority=authority,
                retention_complete=False,
                consumers_clear=True,
            )
        with self.assertRaisesRegex(contract.ContractViolation, "consumer"):
            known_surface.delete(
                stable_id,
                authority=authority,
                retention_complete=True,
                consumers_clear=False,
            )

    def test_target_enforced_fencing_rejects_unfenced_and_stale_writers(self) -> None:
        target = contract.FencedEffectTarget()
        committed = target.write(
            "shared-report",
            idempotency_key="cycle-2026-07-21",
            fencing_token=12,
            value="synthetic effect",
        )
        self.assertEqual("committed", committed["result"])
        replayed = target.write(
            "shared-report",
            idempotency_key="cycle-2026-07-21",
            fencing_token=12,
            value="synthetic effect",
        )
        self.assertEqual("replayed", replayed["result"])
        with self.assertRaisesRegex(contract.ContractViolation, "unfenced"):
            target.write(
                "shared-report",
                idempotency_key="cycle-2026-07-22",
                fencing_token=None,
                value="unfenced effect",
            )
        with self.assertRaisesRegex(contract.ContractViolation, "invalid"):
            target.write(
                "other-report",
                idempotency_key="cycle-2026-07-22",
                fencing_token=-1,
                value="invalid effect",
            )
        with self.assertRaisesRegex(contract.ContractViolation, "stale"):
            target.write(
                "shared-report",
                idempotency_key="cycle-2026-07-22",
                fencing_token=11,
                value="stale effect",
            )

    def test_newer_replay_and_conflict_advance_the_fencing_watermark(self) -> None:
        target = contract.FencedEffectTarget()
        target.write(
            "shared-report",
            idempotency_key="cycle-a",
            fencing_token=12,
            value="effect-a",
        )
        replayed = target.write(
            "shared-report",
            idempotency_key="cycle-a",
            fencing_token=13,
            value="effect-a",
        )
        self.assertEqual("replayed", replayed["result"])
        with self.assertRaisesRegex(contract.ContractViolation, "stale"):
            target.write(
                "shared-report",
                idempotency_key="cycle-b",
                fencing_token=12,
                value="effect-b",
            )
        with self.assertRaisesRegex(contract.ContractViolation, "stale"):
            target.write(
                "shared-report",
                idempotency_key="cycle-a",
                fencing_token=12,
                value="effect-a",
            )

        with self.assertRaisesRegex(contract.ContractViolation, "idempotency key"):
            target.write(
                "shared-report",
                idempotency_key="cycle-a",
                fencing_token=13,
                value="conflicting-effect",
            )
        self.assertEqual(
            "replayed",
            target.write(
                "shared-report",
                idempotency_key="cycle-a",
                fencing_token=13,
                value="effect-a",
            )["result"],
        )

        with self.assertRaisesRegex(contract.ContractViolation, "idempotency key"):
            target.write(
                "shared-report",
                idempotency_key="cycle-a",
                fencing_token=14,
                value="another-conflict",
            )
        with self.assertRaisesRegex(contract.ContractViolation, "stale"):
            target.write(
                "shared-report",
                idempotency_key="cycle-c",
                fencing_token=13,
                value="effect-c",
            )
        self.assertEqual(
            "committed",
            target.write(
                "shared-report",
                idempotency_key="cycle-d",
                fencing_token=14,
                value="effect-d",
            )["result"],
        )

    def test_documentation_keeps_manage_harness_below_live_conformance(self) -> None:
        readme = (DEV_ROOT / "benchmarks" / "README.md").read_text(
            encoding="utf-8"
        )
        claims = (DEV_ROOT / "benchmarks" / "claim-matrix.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Deterministic Manage Contract", readme)
        self.assertIn("does not call a real automation control plane", readme)
        self.assertIn("Deterministic manage contract harness", claims)
        self.assertIn("does not prove manage-skill routing", claims)


if __name__ == "__main__":
    unittest.main()
