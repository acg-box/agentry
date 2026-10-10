"""Contract checks for the guidance-first Automation plugin."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).parents[4]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "automation"
DEV_ROOT = REPO_ROOT / "dev" / "plugins" / "automation"
REPO_VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def flatten(text: str) -> str:
    return " ".join(text.split())


class AutomationLifecycleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        cls.audit = (
            PLUGIN_ROOT / "skills" / "audit" / "SKILL.md"
        ).read_text(encoding="utf-8")
        cls.manage = (
            PLUGIN_ROOT / "skills" / "manage" / "SKILL.md"
        ).read_text(encoding="utf-8")
        cls.audit_agents = (
            PLUGIN_ROOT
            / "skills"
            / "audit"
            / "agents"
            / "openai.yaml"
        ).read_text(encoding="utf-8")
        cls.manage_agents = (
            PLUGIN_ROOT
            / "skills"
            / "manage"
            / "agents"
            / "openai.yaml"
        ).read_text(encoding="utf-8")
        cls.authority = (
            PLUGIN_ROOT / "references" / "authority-and-lifecycle.md"
        ).read_text(encoding="utf-8")
        cls.coordination = (
            PLUGIN_ROOT / "references" / "contract-and-coordination.md"
        ).read_text(encoding="utf-8")
        cls.audit_flat = flatten(cls.audit)
        cls.manage_flat = flatten(cls.manage)
        cls.authority_flat = flatten(cls.authority)
        cls.coordination_flat = flatten(cls.coordination)

    def test_manifest_packages_guidance_and_read_only_analysis_helper(self) -> None:
        self.assertEqual(REPO_VERSION, self.manifest["version"])
        self.assertEqual(
            {".codex-plugin/**", "references/**", "scripts/**", "skills/**"},
            set(self.manifest["package"]["include"]),
        )
        self.assertEqual(
            ["Interactive", "Read", "Write"],
            self.manifest["interface"]["capabilities"],
        )
        for unsupported_surface in ("hooks", "mcpServers", "apps", "scripts"):
            self.assertNotIn(unsupported_surface, self.manifest)

    def test_audit_is_scoped_and_strictly_read_only(self) -> None:
        self.assertIn("Keep this workflow strictly read-only", self.audit_flat)
        self.assertIn("call the result a scoped audit", self.audit_flat)
        self.assertIn("Never claim portfolio completeness", self.audit_flat)
        self.assertIn("observed", self.audit)
        self.assertIn("declared", self.audit)
        self.assertIn("inferred", self.audit)
        self.assertIn("unknown", self.audit)
        self.assertIn("without applying it", self.audit_flat)

    def test_management_requires_authority_and_supported_readback(self) -> None:
        self.assertIn("does not authorize a mutation", self.manage_flat)
        self.assertIn(
            "Find the current supported automation-management tool",
            self.manage_flat,
        )
        self.assertIn("preserve every unchanged field", self.manage_flat)
        self.assertIn("read it back", self.manage_flat)
        self.assertIn("explicitly authorizes deletion", self.manage_flat)
        self.assertIn(
            "Pause stops new activations; it is not proof",
            self.manage_flat,
        )
        external_boundary = (
            "does not authorize repository, connector, credential, claim, "
            "worktree, or external-workload changes"
        )
        self.assertIn(external_boundary, self.manage_flat)
        self.assertIn(
            "separate explicit authority and exact targets",
            self.manage_flat,
        )
        self.assertIn("show raw RRULE strings", self.manage_flat)

    def test_simple_change_path_excludes_coordination_risk(self) -> None:
        change = self.manage_flat.split("## Change", 1)[1].split("## Retire", 1)[0]
        simple, graph = change.split("treat it as a graph operation:", 1)
        for cue in (
            "rename", "notification", "cadence-only", "no dependency",
            "shared-resource", "overlap", "replay implication", "view the task",
            "prior definition", "unchanged fields preserved", "read it back",
            "Missing run history alone does not block such an update",
        ):
            self.assertIn(cue, simple)
        for safeguard in (
            "Prepare backward-compatible consumer guards",
            "Establish quiescence from supported run evidence",
            "If active-run state is unknown, leave the tasks paused",
            "Roll back from the snapshot",
        ):
            self.assertIn(safeguard, graph)

    def test_routing_requires_positive_scheduled_or_recurring_scope(self) -> None:
        audit_description = self.audit.split("---", 2)[1]
        manage_description = self.manage.split("---", 2)[1]
        for description in (audit_description, manage_description):
            self.assertIn("Use when", description)
            self.assertIn("Codex Scheduled", description)
            self.assertIn("generic review of named files", description)
            self.assertIn("inspect those files", description)
            self.assertIn("Do not trigger", description)
            for unrelated in (
                "database migration",
                "data migration",
                "schema migration",
                "code migration",
            ):
                self.assertNotIn(unrelated, description.lower())
        self.assertIn("before completing the review", audit_description)
        self.assertIn("evidence positively identifies", audit_description)
        self.assertIn("shared-resource coordination", audit_description)
        self.assertIn("existing Codex Scheduled or recurring", self.audit_agents)
        self.assertIn("explicit Codex Scheduled or recurring", self.manage_agents)
        for prompt in self.manifest["interface"]["defaultPrompt"]:
            self.assertTrue(
                "Codex Scheduled" in prompt or "recurring Codex automation" in prompt
            )

    def test_coordination_claims_are_conditional(self) -> None:
        self.assertIn("When coordination risk exists", self.manage_flat)
        self.assertIn("target-enforced", self.manage_flat)
        self.assertIn("required workload contracts", self.manage_flat)
        self.assertIn("workload or platform owner", self.manage_flat)
        self.assertIn("does not add a scheduler", self.authority_flat)
        self.assertIn("label the result ambiguous", self.coordination_flat)
        self.assertIn(
            "target must reject every write from an older token",
            self.coordination_flat,
        )

    def test_contract_covers_combinations_and_replay(self) -> None:
        for term in (
            "dependency graph",
            "shared-resource graph",
            "Independent and resource-disjoint",
            "Dependency plus shared writer",
            "skip, coalesce, queue, replace, or parallel",
            "missed-run or catch-up policy",
            "partial-failure",
            "replay",
            "overrun response",
        ):
            self.assertIn(term, self.coordination)

    def test_large_structured_audits_use_the_packaged_read_only_helper(self) -> None:
        self.assertIn("../../references/portfolio-analysis.md", self.audit)
        self.assertIn("../../scripts/audit_portfolio.py", self.audit)
        self.assertIn("preserve every evidence label and unknown value", self.audit_flat)
        self.assertIn("not as live enumeration or scheduler evidence", self.audit_flat)
        self.assertTrue((PLUGIN_ROOT / "scripts" / "audit_portfolio.py").is_file())

    def test_skills_load_only_the_reference_needed_for_the_action(self) -> None:
        for skill in (self.audit, self.manage):
            self.assertEqual(
                1,
                skill.count("../../references/authority-and-lifecycle.md"),
            )
            self.assertEqual(
                1,
                skill.count("../../references/contract-and-coordination.md"),
            )
            self.assertIn("only when", skill)
        self.assertIn(
            "Do not load the authority or coordination reference",
            self.audit_flat,
        )
        self.assertIn("Do not load both references by default", self.manage_flat)
        self.assertNotIn(
            "Read ../../references/authority-and-lifecycle.md and",
            self.audit_flat,
        )
        self.assertNotIn(
            "Read ../../references/authority-and-lifecycle.md and",
            self.manage_flat,
        )

    def test_skill_and_reference_owners_do_not_duplicate_mutation_policy(self) -> None:
        self.assertIn("does not authorize a mutation", self.manage_flat)
        self.assertIn("explicitly requests that action", self.manage_flat)
        self.assertIn("does not grant mutation authority", self.authority_flat)
        self.assertNotIn("## Mutation Authority", self.authority)
        self.assertIn("## Owner Boundary", self.coordination)
        self.assertIn("risk classification", self.coordination_flat)
        self.assertIn("workload or platform owner", self.coordination_flat)
        for contract in (
            "output/receipt atomicity",
            "transactional claims",
            "leases",
            "fencing tokens",
            "target-enforced stale-writer rejection",
        ):
            self.assertIn(contract, self.coordination_flat)


if __name__ == "__main__":
    unittest.main()
