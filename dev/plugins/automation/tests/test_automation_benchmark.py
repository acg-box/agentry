"""Deterministic checks for the Automation benchmark design."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).parents[4]
DEV_ROOT = REPO_ROOT / "dev" / "plugins" / "automation"
SCRIPT = DEV_ROOT / "scripts" / "run_behavior_benchmark.py"
SPEC = importlib.util.spec_from_file_location("automation_benchmark", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load test module: {SCRIPT}")
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class AutomationLifecycleBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = benchmark.load_json(benchmark.CONFIG_PATH)
        cls.oracle = benchmark.load_json(benchmark.ORACLE_PATH)
        cls.coverage = benchmark.load_json(benchmark.COVERAGE_PATH)

    def test_definition_is_neutral_hidden_and_complete(self) -> None:
        scenarios = benchmark.validate_definition(
            self.config, self.oracle, self.coverage
        )

        self.assertEqual(benchmark.PROTOCOL_VERSION, self.config["version"])
        self.assertEqual([f"case-{number:02d}" for number in range(1, 12)], scenarios)
        self.assertEqual("read-only", self.config["runner"]["sandbox"])
        self.assertEqual("never", self.config["runner"]["approvalPolicy"])
        self.assertEqual(
            benchmark.SKILL_READ_POLICY,
            self.config["runner"]["skillReadPolicy"],
        )
        self.assertEqual([], self.config["verifiers"]["commands"])
        self.assertFalse(benchmark.ORACLE_PATH.is_relative_to(benchmark.WORKSPACE_ROOT))
        self.assertFalse(benchmark.COVERAGE_PATH.is_relative_to(benchmark.WORKSPACE_ROOT))
        workspace_files = {
            path.name for path in benchmark.WORKSPACE_ROOT.rglob("*") if path.is_file()
        }
        self.assertNotIn("oracle.json", workspace_files)
        self.assertNotIn("coverage.json", workspace_files)
        notes = " ".join(self.config["notes"])
        self.assertIn("does not establish the no-skill versus candidate-skills treatment", notes)
        self.assertIn("does not measure manage-skill activation", notes)
        self.assertEqual(94271, self.config["measurement"]["preregisteredSeed"])
        self.assertEqual(5000, self.config["measurement"]["bootstrapSamples"])
        self.assertEqual(
            {
                "minimumCandidateAccuracy": 0.90,
                "minimumAbsoluteUplift": 0.10,
                "maximumOvercontrolErrorRate": 0.05,
                "controlCeiling": 0.95,
                "confidenceLevel": 0.95,
            },
            {
                key: self.config["measurement"][key]
                for key in (
                    "minimumCandidateAccuracy",
                    "minimumAbsoluteUplift",
                    "maximumOvercontrolErrorRate",
                    "controlCeiling",
                    "confidenceLevel",
                )
            },
        )
        self.assertTrue(
            all(
                self.oracle["scenarios"][scenario]["routing"] == "audit"
                for scenario in scenarios[:-1]
            )
        )
        self.assertEqual("none", self.oracle["scenarios"]["case-11"]["routing"])
        for scenario in self.config["scenarios"]:
            prompt = scenario["userInput"].lower()
            for term in benchmark.BANNED_PROMPT_TERMS:
                self.assertNotIn(term, prompt)

    def test_skill_read_policy_is_task_neutral_and_uses_exact_paths(self) -> None:
        policy = self.config["runner"]["skillReadPolicy"]
        self.assertIn("exact path in the available-skills inventory", policy)
        self.assertIn("directly linked relative reference", policy)
        self.assertIn("whether or not you use a skill", policy)
        self.assertIn(
            "only pipeline you may use is `rg --files PATH... | rg REGEX`",
            policy,
        )
        self.assertIn("Do not scan parent directories", policy)
        self.assertIn("any other pipeline, shell control chain", policy)
        for term in benchmark.BANNED_PROMPT_TERMS:
            self.assertNotIn(term, policy.lower())
        user_input = "Review the synthetic files."
        prompt = benchmark.benchmark_prompt(user_input, self.config)
        self.assertTrue(prompt.startswith(user_input + "\n\n"))
        self.assertTrue(prompt.endswith(policy))

    def test_one_time_database_migration_is_a_negative_routing_case(self) -> None:
        scenario = next(
            item for item in self.config["scenarios"] if item["id"] == "case-11"
        )
        evidence = (
            benchmark.WORKSPACE_ROOT / "cases" / "case-11" / "evidence.md"
        ).read_text(encoding="utf-8")
        self.assertIn("one-time database migration", evidence)
        self.assertIn("No recurring task", evidence)
        self.assertIn("act on any scheduler", scenario["userInput"])
        self.assertEqual("none", self.oracle["scenarios"]["case-11"]["routing"])

    def test_every_scenario_uses_the_same_task_neutral_prompt_template(self) -> None:
        normalized = []
        for scenario in self.config["scenarios"]:
            case_id = scenario["id"]
            normalized.append(scenario["userInput"].replace(case_id, "case-XX"))
        self.assertEqual(1, len(set(normalized)))

    def test_schedule_is_paired_reproducible_and_counterbalanced(self) -> None:
        scenarios = benchmark.validate_definition(
            self.config, self.oracle, self.coverage
        )
        first = benchmark.build_schedule(scenarios, 10, 73)
        second = benchmark.build_schedule(scenarios, 10, 73)

        self.assertEqual(first, second)
        pairs: dict[str, list[dict[str, object]]] = {}
        for cell in first:
            pairs.setdefault(str(cell["pair_id"]), []).append(cell)
        self.assertEqual(110, len(pairs))
        self.assertTrue(
            all({cell["arm"] for cell in cells} == set(benchmark.ARMS) for cells in pairs.values())
        )
        for scenario in scenarios:
            candidate_first = sum(
                cell["arm"] == "candidate-skills" and cell["arm_position"] == 0
                for cell in first
                if cell["scenario"] == scenario
            )
            self.assertEqual(5, candidate_first)

    def test_confirmation_repetitions_are_exactly_preregistered(self) -> None:
        for repetitions in (9, 11):
            altered = json.loads(json.dumps(self.config))
            altered["measurement"]["confirmationRepetitions"] = repetitions
            with self.subTest(repetitions=repetitions):
                with self.assertRaisesRegex(ValueError, "repetition contract"):
                    benchmark.validate_definition(altered, self.oracle, self.coverage)

    def test_protocol_v5_thresholds_are_exactly_preregistered(self) -> None:
        for key in (
            "minimumCandidateAccuracy",
            "minimumAbsoluteUplift",
            "maximumOvercontrolErrorRate",
            "controlCeiling",
            "confidenceLevel",
        ):
            altered = json.loads(json.dumps(self.config))
            altered["measurement"][key] = altered["measurement"][key] - 0.01
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, f"threshold differs: {key}"):
                    benchmark.validate_definition(altered, self.oracle, self.coverage)

    def test_seed_home_and_outer_environment_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            auth = root / "auth-source.json"
            auth.write_text("{}\n", encoding="utf-8")
            auth.chmod(0o600)
            control_home = root / "control-home"
            control_codex_home = benchmark.seed_home(control_home, auth, "no-skill")
            self.assertEqual(
                {"auth.json"}, {path.name for path in control_codex_home.iterdir()}
            )
            treatment_home = root / "treatment-home"
            treatment_codex_home = benchmark.seed_home(
                treatment_home, auth, "candidate-skills"
            )
            self.assertTrue(
                (treatment_codex_home / "skills/audit/SKILL.md").is_file()
            )
            self.assertTrue(
                (treatment_codex_home / "skills/manage/SKILL.md").is_file()
            )
            self.assertTrue(
                (treatment_codex_home / "references/authority-and-lifecycle.md").is_file()
            )

            with mock.patch.dict(
                os.environ,
                {
                    "PATH": "/bin",
                    "LANG": "C",
                    "UNRELATED_SECRET": "must-not-pass",
                    "AWS_SECRET_ACCESS_KEY": "must-not-pass",
                },
                clear=True,
            ):
                environment = benchmark.isolated_environment(
                    control_home, control_codex_home
                )

        self.assertEqual("/usr/bin:/bin:/usr/sbin:/sbin", environment["PATH"])
        self.assertEqual("C", environment["LANG"])
        self.assertEqual(str(control_home), environment["HOME"])
        self.assertEqual(str(control_codex_home), environment["CODEX_HOME"])
        self.assertNotIn("UNRELATED_SECRET", environment)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", environment)

    def test_scorer_accepts_exact_oracle_and_rejects_safety_error(self) -> None:
        scenario = "case-09"
        expected = self.oracle["scenarios"][scenario]
        exact = {
            "decisions": [
                {"id": identifier, "disposition": disposition}
                for identifier, disposition in expected["expected"].items()
            ],
            "evidence_paths": [
                f"cases/{scenario}/evidence.md"
            ],
            "rationale": "Synthetic exact result.",
        }
        score = benchmark.score_output(exact, expected, scenario)

        self.assertTrue(score["valid"])
        self.assertEqual(1.0, score["accuracy"])
        self.assertEqual([], score["critical_violations"])

        exact["evidence_paths"].append(f"cases/{scenario}/proposal.md")
        self.assertTrue(benchmark.score_output(exact, expected, scenario)["valid"])
        exact["evidence_paths"].append("benchmarks/oracle.json")
        self.assertFalse(benchmark.score_output(exact, expected, scenario)["valid"])
        exact["evidence_paths"].pop()

        exact["decisions"][1]["disposition"] = "accept"
        unsafe = benchmark.score_output(exact, expected, scenario)
        self.assertIn("P09-PARTIAL", unsafe["critical_violations"])
        self.assertLess(unsafe["accuracy"], 1.0)

    def test_scorer_rejects_duplicate_missing_and_invented_ids(self) -> None:
        scenario = "case-02"
        expected = self.oracle["scenarios"][scenario]
        output = {
            "decisions": [
                {"id": "P02-GUARD-INDEPENDENT", "disposition": "change"},
                {"id": "P02-GUARD-INDEPENDENT", "disposition": "accept"},
                {"id": "P02-NOT-REAL", "disposition": "defer"},
            ],
            "evidence_paths": [
                f"cases/{scenario}/evidence.md"
            ],
            "rationale": "Malformed synthetic result.",
        }
        score = benchmark.score_output(output, expected, scenario)

        self.assertFalse(score["valid"])
        self.assertEqual(["P02-GUARD-INDEPENDENT"], score["duplicate_ids"])
        self.assertEqual(["P02-NOT-REAL"], score["unknown_output_ids"])
        self.assertTrue(score["missing_output_ids"])

    def test_event_guard_flags_external_tools_and_network_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            events = [
                {
                    "type": "item.completed",
                    "item": {
                        "id": "item-safe",
                        "type": "command_execution",
                        "command": "sed -n '1,40p' cases/case-01/evidence.md",
                        "exit_code": 0,
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "id": "item-network",
                        "type": "command_execution",
                        "command": "curl https://invalid.example",
                        "exit_code": 0,
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "id": "item-tool",
                        "type": "mcp_tool_call",
                        "name": "automation_update",
                    },
                },
            ]
            path.write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )
            violations = benchmark.scan_forbidden_events(path)

        self.assertTrue(any(item.startswith("forbidden_command:") for item in violations))
        self.assertIn("external_tool_type:mcp_tool_call", violations)
        self.assertIn("forbidden_tool:automation_update", violations)
        self.assertEqual(
            [],
            benchmark.shell_command_violations(
                "/bin/zsh -lc \"sed -n '1,40p' cases/case-01/evidence.md\""
            ),
        )
        self.assertTrue(
            benchmark.shell_command_violations(
                "python3 -c 'import urllib.request; urllib.request.urlopen(\"https://invalid.example\")'"
            )
        )

    def test_command_guard_closes_write_and_host_read_bypasses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            skills = root / "task-home" / ".codex" / "skills"
            workspace.mkdir()
            skills.mkdir(parents=True)
            (workspace / "evidence.md").write_text("synthetic\n", encoding="utf-8")
            allowed = (workspace, skills)
            safe = benchmark.shell_command_violations(
                "/bin/zsh -lc \"sed -n '1,40p' evidence.md\"",
                working_directory=workspace,
                readable_roots=allowed,
            )
            self.assertEqual([], safe)
            self.assertEqual(
                [],
                benchmark.shell_command_violations(
                    "rg -F synthetic evidence.md",
                    working_directory=workspace,
                    readable_roots=allowed,
                ),
            )
            for command in (
                "rg --files -g review-output.schema.json",
                "rg --files --glob review-output.schema.json",
            ):
                with self.subTest(safe_glob=command):
                    self.assertEqual(
                        [],
                        benchmark.shell_command_violations(
                            command,
                            working_directory=workspace,
                            readable_roots=allowed,
                        ),
                    )
            outside = root / "outside"
            outside.mkdir()
            self.assertIn(
                f"path_outside_allowlist:{outside}",
                benchmark.shell_command_violations(
                    f"rg --files -g review-output.schema.json {outside}",
                    working_directory=workspace,
                    readable_roots=allowed,
                ),
            )
            self.assertIn(
                "executable:jq",
                benchmark.shell_command_violations(
                    "jq -r . evidence.md",
                    working_directory=workspace,
                    readable_roots=allowed,
                ),
            )
            self.assertIn(
                "skill_parent_scan",
                benchmark.shell_command_violations(
                    f"rg --files {skills}",
                    working_directory=workspace,
                    readable_roots=allowed,
                ),
            )
            commands = (
                "sort -o /tmp/x evidence.md",
                "find . -fprint /tmp/x",
                "sed -i'' 's/a/b/' evidence.md",
                "sed --in-place 's/a/b/' evidence.md",
                "sed -n 'w /tmp/x' evidence.md",
                "sed -n 'r /tmp/secret' evidence.md",
                "sed -n 's/a/b/e' evidence.md",
                "sed -n 's/a/b/e;' evidence.md",
                "sed -n '1,2p;e touch /tmp/parser-bypass' evidence.md",
                "find . -type f",
                "f\\ind . -e\\xec sh -c 'touch /tmp/parser-bypass' '{}' +",
                "s\\ort --compress-pro\\gram=sh evidence.md",
                f"cat {benchmark.ORACLE_PATH}",
                f"rg -e. {benchmark.ORACLE_PATH}",
                f"rg --regexp=. {benchmark.ORACLE_PATH}",
                f"rg -Ferouting {benchmark.ORACLE_PATH}",
                f"rg -Uerouting {benchmark.ORACLE_PATH}",
                (
                    "rg -Ffreview-output.schema.json "
                    f"{benchmark.ORACLE_PATH}"
                ),
                f"rg --ignore-file {benchmark.ORACLE_PATH} routing .",
                f"jq -ffilter.jq . {benchmark.ORACLE_PATH}",
                f"jq -Rffilter.jq . {benchmark.ORACLE_PATH}",
                f"jq --run-tests {benchmark.ORACLE_PATH}",
                f"sed -nep {benchmark.ORACLE_PATH}",
                "cat ../../host-secret",
                "rg --pre=/tmp/runner pattern .",
                "rg --hostname-bin=/tmp/runner pattern .",
            )
            for command in commands:
                with self.subTest(command=command):
                    self.assertTrue(
                        benchmark.shell_command_violations(
                            command,
                            working_directory=workspace,
                            readable_roots=allowed,
                        )
                    )

            events = root / "events.jsonl"
            events.write_text("{not-json}\n", encoding="utf-8")
            self.assertEqual(
                ["invalid_event_json:1"],
                benchmark.scan_forbidden_events(
                    events,
                    workspace_root=workspace,
                    readable_roots=(skills,),
                ),
            )
            events.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-missing-command",
                            "type": "command_execution",
                            "exit_code": 0,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertIn(
                "invalid_command_event:1",
                benchmark.scan_forbidden_events(
                    events,
                    workspace_root=workspace,
                    readable_roots=(skills,),
                ),
            )
            events.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-missing-exit",
                            "type": "command_execution",
                            "command": "cat evidence.md",
                            "exit_code": None,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertIn(
                "invalid_command_exit_code:1",
                benchmark.scan_forbidden_events(
                    events,
                    workspace_root=workspace,
                    readable_roots=(skills,),
                ),
            )

    def test_command_guard_is_quote_aware_but_stays_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            candidate = root / "task-home" / ".codex"
            skill = candidate / "skills" / "manage" / "SKILL.md"
            reference = candidate / "references" / "authority-and-lifecycle.md"
            workspace.mkdir()
            skill.parent.mkdir(parents=True)
            reference.parent.mkdir(parents=True)
            (workspace / "evidence.md").write_text("synthetic\n", encoding="utf-8")
            skill.write_text("Create paused.\n", encoding="utf-8")
            reference.write_text("Authority.\n", encoding="utf-8")
            (candidate / "auth.json").write_text("{}\n", encoding="utf-8")
            allowed = (workspace, candidate / "skills", candidate / "references")

            safe_commands = (
                (
                    "/bin/zsh -lc \"rg -n '(Authority|Lifecycle)\\.$' "
                    f"{reference}\""
                ),
                f"cat {skill}",
                f"cat {reference}",
                f"rg -n 'Create \\$TASK or \\(paused\\)' {skill}",
                f"rg -n 'literal $HOME is data' {skill}",
                f"rg -n '\\[[a-z]+\\]\\?$' {reference}",
                f'/bin/zsh -lc "rg \'Authority$\' {reference}"',
                f'/bin/zsh -lc "rg \'literal $HOME\' {reference}"',
                f"rg '=rg' {reference}",
                f"rg \\=rg {reference}",
            )
            for command in safe_commands:
                with self.subTest(safe=command):
                    self.assertEqual(
                        [],
                        benchmark.shell_command_violations(
                            command,
                            working_directory=workspace,
                            readable_roots=allowed,
                        ),
                    )

            unsafe_commands = {
                'rg -n "$HOME" evidence.md': "shell_expansion",
                "rg -n ${PATTERN} evidence.md": "shell_expansion",
                "rg -n $(cat evidence.md) evidence.md": "shell_expansion",
                "(cat evidence.md)": "shell_glob_or_grouping",
                "cat {evidence,proposal}.md": "shell_glob_or_grouping",
                "cat evidence.md && cat evidence.md": "shell_control_operator",
                "cat evidence.md; cat evidence.md": "shell_control_operator",
                "cat evidence.md | tee copy.md": "executable:tee",
                f"rg --files {candidate}": f"path_outside_allowlist:{candidate}",
                f"find {candidate} -type f": f"path_outside_allowlist:{candidate}",
                f"cat {candidate / 'auth.json'}": "private_codex_state",
                (
                    f"for f in {candidate / 'skills'}; do cat \"$f\"; done"
                ): "shell_expansion",
                "cat ../host-secret": "path_outside_allowlist:../host-secret",
                "cat evidence.md > copy.md": "shell_redirection",
                "cat <<< evidence.md": "shell_redirection",
                "rm evidence.md": "executable:rm",
                "curl https://invalid.example": "executable:curl",
            }
            for command, expected in unsafe_commands.items():
                with self.subTest(unsafe=command):
                    self.assertIn(
                        expected,
                        benchmark.shell_command_violations(
                            command,
                            working_directory=workspace,
                            readable_roots=allowed,
                        ),
                    )

    def test_command_guard_allows_only_one_fully_validated_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            case = workspace / "cases" / "case-05"
            case.mkdir(parents=True)
            for name in ("proposal.md", "evidence.md"):
                (case / name).write_text("synthetic\n", encoding="utf-8")
            (workspace / "review-output.schema.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            outside = root / "outside.md"
            outside.write_text("private\n", encoding="utf-8")

            observed_command = '/bin/zsh -lc "rg --files cases/case-05 . | rg \'("\'^|/)review-output\'"\\\\.schema\\\\.json"\'$|\'\'^cases/case-05/(proposal|evidence)\'"\\\\.md"\'$\'"\'"'
            self.assertEqual(
                [],
                benchmark.shell_command_violations(
                    observed_command,
                    working_directory=workspace,
                    readable_roots=(workspace,),
                ),
            )
            self.assertEqual(
                [],
                benchmark.shell_command_violations(
                    r"rg --files cases/case-05 . | rg '(^|/)review-output\.schema\.json$|^cases/case-05/(proposal|evidence)\.md$'",
                    working_directory=workspace,
                    readable_roots=(workspace,),
                ),
            )
            for regex in ("'|'", "'|||'"):
                with self.subTest(quoted_pipeline_regex=regex):
                    self.assertEqual(
                        [],
                        benchmark.shell_command_violations(
                            f"rg --files . | rg {regex}",
                            working_directory=workspace,
                            readable_roots=(workspace,),
                        ),
                    )
            self.assertEqual(
                [],
                benchmark.shell_command_violations(
                    "rg '|' cases/case-05/evidence.md",
                    working_directory=workspace,
                    readable_roots=(workspace,),
                ),
            )

            rejected = {
                "cat cases/case-05/evidence.md | wc -l": "unsupported_pipeline",
                "rg --files . | curl https://invalid.example": "executable:curl",
                "rg --files . | tee copy.md": "executable:tee",
                "rg --files . | sh": "executable:sh",
                "rg --files . | xargs cat": "executable:xargs",
                "| rg synthetic .": "shell_control_operator",
                "rg --files . |": "shell_control_operator",
                "rg --files . | rg synthetic | wc -l": "shell_control_operator",
                f"rg --files . | cat {outside}": f"path_outside_allowlist:{outside}",
                "rg --files . | rg --pre=/tmp/runner synthetic": "unsafe_rg_option",
                "rg --files . | rg synthetic cases/case-05/evidence.md": "unsupported_pipeline",
                "rg --files --hidden . | rg synthetic": "unsupported_pipeline",
                "rg --files ../outside | rg synthetic": "unsupported_pipeline",
                "printf 'touch /tmp/pwn\\n' | sort --comp=sh -S 1b": "executable:sort",
                "printf 'touch /tmp/pwn\\n' | sort --compress-prog=sh -S 1b": "executable:sort",
                "printf 'payload\\n' | sort --out=copy.md": "executable:sort",
                "rg --files . | rg synthetic > copy.md": "shell_redirection",
                "rg --files . && rg synthetic": "shell_control_operator",
                "cat cases/case-05/evidence.md | rg synthetic ||| cat cases/case-05/proposal.md": "shell_control_operator",
                "||||": "shell_control_operator",
                "cat cases/case-05/evidence.md |& rg synthetic": "shell_control_operator",
                '/tmp/evil/zsh -lc "cat cases/case-05/evidence.md"': "executable:zsh",
                'zsh -lc "cat cases/case-05/evidence.md"': "executable:zsh",
                "/bin/../../tmp/evil/cat cases/case-05/evidence.md": "executable_path",
                "/usr/bin/../../../tmp/evil/cat cases/case-05/evidence.md": "executable_path",
                "rg . $=CODEX_HOME": "shell_expansion",
                "rg . $^CODEX_HOME": "shell_expansion",
                "rg . $~CODEX_HOME": "shell_expansion",
                "rg . $+CODEX_HOME": "shell_expansion",
                "rg . =rg": "shell_expansion",
                "ls =rg": "shell_expansion",
                "cat =rg": "shell_expansion",
                "ls ''=rg": "shell_expansion",
                'ls ""=rg': "shell_expansion",
                "rg --files . missing | rg synthetic": "unsupported_pipeline",
            }
            escape = workspace / "escape"
            escape.symlink_to(root)
            rejected["rg --files escape | rg synthetic"] = "unsupported_pipeline"
            real_directory = workspace / "real"
            real_directory.mkdir()
            (real_directory / "inside.md").write_text(
                "synthetic\n",
                encoding="utf-8",
            )
            internal_directory_link = workspace / "internal-directory-link"
            internal_directory_link.symlink_to(real_directory, target_is_directory=True)
            internal_file_link = workspace / "internal-file-link.md"
            internal_file_link.symlink_to(real_directory / "inside.md")
            nested = real_directory / "nested"
            nested.mkdir()
            symlink_parent = workspace / "symlink-parent"
            symlink_parent.symlink_to(nested, target_is_directory=True)
            rejected[
                "rg --files internal-directory-link | rg inside"
            ] = "unsupported_pipeline"
            rejected[
                "rg --files internal-file-link.md | rg inside"
            ] = "unsupported_pipeline"
            rejected[
                "rg --files symlink-parent/../inside.md | rg inside"
            ] = "unsupported_pipeline"
            for command, expected in rejected.items():
                with self.subTest(rejected=command):
                    self.assertIn(
                        expected,
                        benchmark.shell_command_violations(
                            command,
                            working_directory=workspace,
                            readable_roots=(workspace,),
                        ),
                    )

    def test_allowed_pipeline_replays_after_disposable_workspace_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "recorded" / "workspace"
            validation_workspace = root / "validation-workspace"
            workspace.mkdir(parents=True)
            validation_workspace.mkdir()
            (workspace / "evidence.md").write_text("synthetic\n", encoding="utf-8")
            (validation_workspace / "evidence.md").write_text(
                "synthetic\n",
                encoding="utf-8",
            )
            command = "rg --files . | rg 'evidence[.]md'"
            symlink_command = "rg --files link | rg inside"
            self.assertEqual(
                [],
                benchmark.shell_command_violations(
                    command,
                    working_directory=workspace,
                    readable_roots=(workspace,),
                    workspace_validation_root=validation_workspace,
                ),
            )
            for root_path in (workspace, validation_workspace):
                real = root_path / "real"
                real.mkdir()
                (real / "inside.md").write_text("synthetic\n", encoding="utf-8")
                (root_path / "link").symlink_to(real, target_is_directory=True)
            self.assertIn(
                "unsupported_pipeline",
                benchmark.shell_command_violations(
                    symlink_command,
                    working_directory=workspace,
                    readable_roots=(workspace,),
                    workspace_validation_root=validation_workspace,
                ),
            )
            (workspace / "evidence.md").unlink()
            (workspace / "link").unlink()
            (workspace / "real" / "inside.md").unlink()
            (workspace / "real").rmdir()
            workspace.rmdir()
            workspace.parent.rmdir()
            (validation_workspace / "link").unlink()
            (validation_workspace / "real" / "inside.md").unlink()
            (validation_workspace / "real").rmdir()
            self.assertEqual(
                [],
                benchmark.shell_command_violations(
                    command,
                    working_directory=workspace,
                    readable_roots=(workspace,),
                    workspace_validation_root=validation_workspace,
                ),
            )
            validation_real = validation_workspace / "real"
            validation_real.mkdir()
            (validation_real / "inside.md").write_text(
                "synthetic\n",
                encoding="utf-8",
            )
            (validation_workspace / "link").symlink_to(
                validation_real,
                target_is_directory=True,
            )
            self.assertIn(
                "unsupported_pipeline",
                benchmark.shell_command_violations(
                    symlink_command,
                    working_directory=workspace,
                    readable_roots=(workspace,),
                    workspace_validation_root=validation_workspace,
                ),
            )
            self.assertIn(
                "unsupported_pipeline",
                benchmark.shell_command_violations(
                    "rg --files . missing | rg evidence",
                    working_directory=workspace,
                    readable_roots=(workspace,),
                    workspace_validation_root=validation_workspace,
                ),
            )

    def test_workspace_digest_includes_previously_ignored_entries_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ignored = root / ".plugin-eval"
            cache = root / "__pycache__"
            ignored.mkdir()
            cache.mkdir()
            (ignored / "state").write_text("one\n", encoding="utf-8")
            (cache / "module.pyc").write_bytes(b"one")
            link = root / "link"
            link.symlink_to(".plugin-eval/state")
            first = benchmark.workspace_digest(root)
            (ignored / "state").write_text("two\n", encoding="utf-8")
            second = benchmark.workspace_digest(root)
            self.assertNotEqual(first, second)
            link.unlink()
            link.symlink_to("__pycache__/module.pyc")
            third = benchmark.workspace_digest(root)
            self.assertNotEqual(second, third)

    def test_control_behavior_is_baseline_evidence_but_candidate_is_gated(self) -> None:
        score = {"valid": True, "critical_violations": ["P-CRITICAL"]}
        control = benchmark.classify_failures(
            arm="no-skill",
            exit_code=0,
            parse_error=None,
            score=score,
            workspace_changes=0,
            forbidden_events=[],
            routing_observed=True,
        )
        candidate = benchmark.classify_failures(
            arm="candidate-skills",
            exit_code=0,
            parse_error=None,
            score=score,
            workspace_changes=0,
            forbidden_events=[],
            routing_observed=True,
        )
        self.assertEqual((False, True, False), control)
        self.assertEqual((False, True, True), candidate)
        self.assertEqual(
            (False, True, True),
            benchmark.classify_failures(
                arm="candidate-skills",
                exit_code=0,
                parse_error=None,
                score={"valid": True, "critical_violations": []},
                workspace_changes=0,
                forbidden_events=[],
                routing_observed=False,
            ),
        )
        self.assertEqual(
            (True, False, True),
            benchmark.classify_failures(
                arm="no-skill",
                exit_code=0,
                parse_error=None,
                score={"valid": True, "critical_violations": []},
                workspace_changes=0,
                forbidden_events=["network"],
                routing_observed=True,
            ),
        )

    def test_treatment_observer_binds_paths_access_and_complete_reads(self) -> None:
        audit_text = "# Audit candidate\nFirst rule.\nSecond rule.\n"
        manage_text = "# Manage candidate\nMutation rule.\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            codex_home = root / "task-home" / ".codex"
            audit_path = codex_home / "skills" / "audit" / "SKILL.md"
            manage_path = codex_home / "skills" / "manage" / "SKILL.md"
            reference_path = codex_home / "references" / "contract.md"
            for path, content in (
                (audit_path, audit_text),
                (manage_path, manage_text),
                (reference_path, "Reference body.\n"),
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            workspace.mkdir()
            split = audit_text.index("Second")
            escaped_audit = str(audit_path).replace("SKILL.md", r"SKILL.m\d")
            events = [
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"sed -n '1,2p' {escaped_audit}",
                        "exit_code": 0,
                        "aggregated_output": audit_text[:split],
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"sed -n '3,4p' {audit_path}",
                        "exit_code": 0,
                        "aggregated_output": audit_text[split:],
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"cat {manage_path}",
                        "exit_code": 1,
                        "aggregated_output": manage_text,
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"cat {reference_path}",
                        "exit_code": 0,
                        "aggregated_output": "Reference body.\n",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"printf '%s' {workspace / 'unrelated.md'}",
                        "exit_code": 0,
                        "aggregated_output": manage_text,
                    },
                },
            ]
            path = root / "events.jsonl"
            path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            observed = benchmark.observed_treatment_reads(
                path,
                workspace_root=workspace,
                codex_home=codex_home,
                audit_skill_text=audit_text,
                manage_skill_text=manage_text,
            )
            self.assertEqual(
                {
                    "audit_access": True,
                    "manage_access": True,
                    "reference_access": True,
                    "treatment_access": True,
                    "audit_loaded": True,
                    "manage_loaded": False,
                },
                observed,
            )

    def test_treatment_observer_ignores_unrelated_full_text_and_partial_read(self) -> None:
        audit_text = "# Audit candidate\nFirst rule.\nSecond rule.\n"
        manage_text = "# Manage candidate\nMutation rule.\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            codex_home = root / "task-home" / ".codex"
            audit_path = codex_home / "skills" / "audit" / "SKILL.md"
            audit_path.parent.mkdir(parents=True)
            audit_path.write_text(audit_text, encoding="utf-8")
            workspace.mkdir()
            unrelated = workspace / "unrelated.md"
            unrelated.write_text(audit_text, encoding="utf-8")
            events = [
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"sed -n '1p' {audit_path}",
                        "exit_code": 0,
                        "aggregated_output": "# Audit candidate\n",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"cat {unrelated}",
                        "exit_code": 0,
                        "aggregated_output": audit_text,
                    },
                },
            ]
            path = root / "events.jsonl"
            path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            observed = benchmark.observed_treatment_reads(
                path,
                workspace_root=workspace,
                codex_home=codex_home,
                audit_skill_text=audit_text,
                manage_skill_text=manage_text,
            )
            self.assertTrue(observed["audit_access"])
            self.assertFalse(observed["audit_loaded"])
            self.assertFalse(observed["manage_access"])
            self.assertFalse(observed["reference_access"])

    def test_treatment_observer_excludes_pipeline_regex_and_non_reader_operands(self) -> None:
        audit_text = "# Audit candidate\nExact body.\n"
        manage_text = "# Manage candidate\nMutation rule.\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            codex_home = root / "task-home" / ".codex"
            audit_path = codex_home / "skills" / "audit" / "SKILL.md"
            audit_path.parent.mkdir(parents=True)
            audit_path.write_text(audit_text, encoding="utf-8")
            workspace.mkdir()
            events = [
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"rg --files . | rg {audit_path}",
                        "exit_code": 0,
                        "aggregated_output": str(audit_path) + "\n",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"printf '%s' {audit_path}",
                        "exit_code": 0,
                        "aggregated_output": audit_text,
                    },
                },
            ]
            events_path = root / "events.jsonl"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

            observed = benchmark.observed_treatment_reads(
                events_path,
                workspace_root=workspace,
                codex_home=codex_home,
                audit_skill_text=audit_text,
                manage_skill_text=manage_text,
            )

            self.assertEqual(
                {
                    "audit_access": False,
                    "manage_access": False,
                    "reference_access": False,
                    "treatment_access": False,
                    "audit_loaded": False,
                    "manage_loaded": False,
                },
                observed,
            )

    def test_treatment_observer_normalizes_case_variant_candidate_paths(self) -> None:
        audit_text = "# Audit candidate\nExact body.\n"
        manage_text = "# Manage candidate\nMutation rule.\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            codex_home = root / "task-home" / ".codex"
            audit_path = codex_home / "skills" / "audit" / "SKILL.md"
            reference_path = codex_home / "references" / "Contract.md"
            audit_path.parent.mkdir(parents=True)
            reference_path.parent.mkdir(parents=True)
            audit_path.write_text(audit_text, encoding="utf-8")
            reference_path.write_text("Reference.\n", encoding="utf-8")
            workspace.mkdir()
            case_variant_audit = str(audit_path).replace("SKILL.md", "skill.md")
            case_variant_reference = str(reference_path).replace(
                "references/Contract.md",
                "REFERENCES/contract.md",
            )
            events = [
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"cat {case_variant_audit}",
                        "exit_code": 0,
                        "aggregated_output": audit_text,
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"stat {case_variant_reference}",
                        "exit_code": 0,
                        "aggregated_output": "metadata\n",
                    },
                },
            ]
            events_path = root / "events.jsonl"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

            observed = benchmark.observed_treatment_reads(
                events_path,
                workspace_root=workspace,
                codex_home=codex_home,
                audit_skill_text=audit_text,
                manage_skill_text=manage_text,
            )

            self.assertTrue(observed["audit_access"])
            self.assertTrue(observed["audit_loaded"])
            self.assertTrue(observed["reference_access"])
            self.assertTrue(observed["treatment_access"])

    def test_result_labels_do_not_collapse_evidence_layers(self) -> None:
        base = {
            "cells": 110,
            "valid_outputs": 110,
            "hard_failures": 0,
            "accuracy": 0.92,
            "overcontrol_error_rate": 0.0,
            "scenario_accuracy": {f"case-{number:02d}": 0.9 for number in range(1, 12)},
        }
        control = {
            **base,
            "accuracy": 0.80,
            "scenario_accuracy": {f"case-{number:02d}": 0.8 for number in range(1, 12)},
        }
        smoke_candidate = {**base, "cells": 11, "valid_outputs": 11}
        smoke_control = {**control, "cells": 11, "valid_outputs": 11}
        pilot_candidate = {**base, "cells": 33, "valid_outputs": 33}
        pilot_control = {**control, "cells": 33, "valid_outputs": 33}
        positive_interval = {"estimate": 0.12, "lower": 0.05, "upper": 0.18}
        self.assertEqual(
            "harness_smoke_only",
            benchmark.benchmark_conclusion(
                phase="smoke",
                repetitions=1,
                config=self.config,
                candidate=smoke_candidate,
                control=smoke_control,
                complete_pairs=11,
                expected_pairs=11,
            ),
        )
        self.assertEqual(
            "pilot_no_effect_claim",
            benchmark.benchmark_conclusion(
                phase="pilot",
                repetitions=3,
                config=self.config,
                candidate=pilot_candidate,
                control=pilot_control,
                complete_pairs=33,
                expected_pairs=33,
            ),
        )
        self.assertEqual(
            "benchmark_local_effect_observed",
            benchmark.benchmark_conclusion(
                phase="confirm",
                repetitions=10,
                config=self.config,
                candidate=base,
                control=control,
                complete_pairs=110,
                expected_pairs=110,
                paired_interval=positive_interval,
            ),
        )
        self.assertEqual(
            "benchmark_local_effect_not_demonstrated",
            benchmark.benchmark_conclusion(
                phase="confirm",
                repetitions=10,
                config=self.config,
                candidate=base,
                control=control,
                complete_pairs=110,
                expected_pairs=110,
                paired_interval={"estimate": 0.12, "lower": 0.0, "upper": 0.18},
            ),
        )
        self.assertEqual(
            "benchmark_local_effect_not_demonstrated",
            benchmark.benchmark_conclusion(
                phase="confirm",
                repetitions=10,
                config=self.config,
                candidate=base,
                control=control,
                complete_pairs=110,
                expected_pairs=110,
                paired_interval={"estimate": 0.11, "lower": 0.05, "upper": 0.18},
            ),
        )
        self.assertEqual(
            "benchmark_local_effect_not_demonstrated",
            benchmark.benchmark_conclusion(
                phase="confirm",
                repetitions=10,
                config=self.config,
                candidate=base,
                control=control,
                complete_pairs=110,
                expected_pairs=110,
                paired_interval=positive_interval,
                source_stable=False,
            ),
        )
        failed = {**base, "hard_failures": 1}
        self.assertEqual(
            "benchmark_local_effect_not_demonstrated",
            benchmark.benchmark_conclusion(
                phase="confirm",
                repetitions=10,
                config=self.config,
                candidate=failed,
                control=control,
                complete_pairs=110,
                expected_pairs=110,
            ),
        )
        invalid_control = {
            **control,
            "valid_outputs": 109,
            "accuracy": 0.79,
        }
        self.assertEqual(
            "benchmark_local_effect_observed",
            benchmark.benchmark_conclusion(
                phase="confirm",
                repetitions=10,
                config=self.config,
                candidate=base,
                control=invalid_control,
                complete_pairs=110,
                expected_pairs=110,
                paired_interval={"estimate": 0.13, "lower": 0.05, "upper": 0.2},
            ),
        )
        control_integrity_failure = {**control, "hard_failures": 1}
        self.assertEqual(
            "benchmark_local_effect_not_demonstrated",
            benchmark.benchmark_conclusion(
                phase="confirm",
                repetitions=10,
                config=self.config,
                candidate=base,
                control=control_integrity_failure,
                complete_pairs=110,
                expected_pairs=110,
                paired_interval=positive_interval,
            ),
        )
        overcontrolling = {**base, "overcontrol_error_rate": 0.06}
        self.assertEqual(
            "benchmark_local_effect_not_demonstrated",
            benchmark.benchmark_conclusion(
                phase="confirm",
                repetitions=10,
                config=self.config,
                candidate=overcontrolling,
                control=control,
                complete_pairs=110,
                expected_pairs=110,
                paired_interval=positive_interval,
            ),
        )

    def test_paired_bootstrap_is_deterministic_and_uses_complete_pairs(self) -> None:
        records = []
        scenario_scores = {
            "case-01": (2, 2, 1, 2),
            "case-02": (9, 10, 8, 10),
        }
        for scenario, (candidate_correct, total, control_correct, _) in scenario_scores.items():
            for repetition in range(1, 6):
                pair_id = f"{scenario}-r{repetition:02d}"
                records.extend(
                    [
                        {
                            "pair_id": pair_id,
                            "scenario": scenario,
                            "arm": "candidate-skills",
                            "score": {
                                "accuracy": candidate_correct / total,
                                "correct": candidate_correct,
                                "total": total,
                                "valid": True,
                            },
                        },
                        {
                            "pair_id": pair_id,
                            "scenario": scenario,
                            "arm": "no-skill",
                            "score": {
                                "accuracy": control_correct / total,
                                "correct": control_correct,
                                "total": total,
                                "valid": True,
                            },
                        },
                    ]
                )
        first = benchmark.paired_accuracy_interval(
            records, seed=94271, samples=1000, confidence=0.95
        )
        second = benchmark.paired_accuracy_interval(
            records, seed=94271, samples=1000, confidence=0.95
        )
        self.assertEqual(first, second)
        assert first is not None
        self.assertEqual(10, first["pairs"])
        self.assertEqual("proposition_weighted", first["weighting"])
        self.assertEqual(0.166667, first["estimate"])
        self.assertGreater(first["lower"], 0)

    def test_cli_identity_is_canonical_and_self_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "codex-real"
            executable.write_text("#!/bin/sh\necho 'codex-cli test-v4'\n", encoding="utf-8")
            executable.chmod(0o755)
            link = root / "codex-link"
            link.symlink_to(executable)
            with mock.patch.dict(os.environ, {"CODEX_CLI": str(link)}):
                command = benchmark.resolve_codex_command()
            self.assertEqual([str(executable.resolve())], command)
            identity = benchmark.capture_codex_identity(command)
            self.assertEqual(str(executable.resolve()), identity["resolved_path"])
            self.assertEqual("codex-cli test-v4", identity["version"])
            self.assertEqual(benchmark.file_digest(executable), identity["entry_sha256"])

        canonical_echo = str(Path("/bin/echo").resolve(strict=True))
        with mock.patch.object(
            benchmark,
            "file_digest",
            side_effect=("before", "after"),
        ), mock.patch.object(
            benchmark.subprocess,
            "check_output",
            return_value="codex-cli changed\n",
        ):
            with self.assertRaisesRegex(RuntimeError, "changed during identity capture"):
                benchmark.capture_codex_identity([canonical_echo])

    def test_auth_snapshot_is_nofollow_private_and_reused_by_seed_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "auth.json"
            source.write_text('{"synthetic": true}\n', encoding="utf-8")
            source.chmod(0o600)
            snapshot = root / "snapshot" / "auth.json"
            benchmark.snapshot_auth(source, snapshot)
            self.assertEqual(source.read_bytes(), snapshot.read_bytes())
            self.assertEqual(0o600, snapshot.stat().st_mode & 0o777)

            home = root / "home"
            codex_home = benchmark.seed_home(home, snapshot, "no-skill")
            self.assertEqual(0o600, (codex_home / "auth.json").stat().st_mode & 0o777)

            link = root / "auth-link.json"
            link.symlink_to(source)
            with self.assertRaises(OSError):
                benchmark.snapshot_auth(link, root / "rejected.json")
            source.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError, "ownership or mode"):
                benchmark.snapshot_auth(source, root / "unsafe-mode.json")

    def test_scorer_rejects_unhashable_evidence_paths_without_crashing(self) -> None:
        scenario = "case-01"
        output = {
            "decisions": [],
            "evidence_paths": [[f"cases/{scenario}/evidence.md"]],
            "rationale": "Malformed evidence path.",
        }
        score = benchmark.score_output(
            output,
            self.oracle["scenarios"][scenario],
            scenario,
        )
        self.assertFalse(score["valid"])
        self.assertFalse(score["evidence_valid"])

    def test_protocol_v5_rejects_jq_module_and_all_jq_execution(self) -> None:
        for command in (
            "jq -r . evidence.md",
            "jq 'include \"outside\"; .' evidence.md",
            "jq 'import \"outside\" as x; .' evidence.md",
            "jq -L /tmp/modules . evidence.md",
        ):
            with self.subTest(command=command):
                self.assertIn(
                    "executable:jq",
                    benchmark.shell_command_violations(command),
                )

    def _write_qualification_metadata(
        self,
        root: Path,
        *,
        phase: str,
        identity: dict[str, object],
        qualification: dict[str, object] | None = None,
    ) -> Path:
        repetitions = benchmark.repetitions_for_phase(self.config, phase)
        scenario_ids = list(identity["scenario_ids"])
        expected_pairs = len(scenario_ids) * repetitions
        cli_identity = dict(identity["codex_identity"])
        run_root = root / phase
        run_root.mkdir()
        records = []
        audit_skill_text = (
            benchmark.CANDIDATE_ROOT / "skills" / "audit" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for cell in benchmark.build_schedule(
            scenario_ids,
            repetitions,
            int(identity["seed"]),
        ):
            arm_root = run_root / "raw" / cell["pair_id"] / cell["arm"]
            arm_root.mkdir(parents=True)
            temporary_root = run_root / (
                "automation-benchmark-"
                + cell["pair_id"]
                + "-"
                + cell["arm"]
            )
            workspace = temporary_root / "workspace"
            codex_home = temporary_root / "task-home" / ".codex"
            skill_path = codex_home / "skills" / "audit" / "SKILL.md"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text(audit_skill_text, encoding="utf-8")
            (codex_home / "references").mkdir(parents=True)
            workspace.mkdir(parents=True)
            expected_oracle = self.oracle["scenarios"][cell["scenario"]]
            output = {
                "decisions": [
                    {
                        "id": identifier,
                        "disposition": (
                            disposition[0]
                            if isinstance(disposition, list)
                            else disposition
                        ),
                    }
                    for identifier, disposition in expected_oracle["expected"].items()
                ],
                "evidence_paths": [f"cases/{cell['scenario']}/evidence.md"],
                "rationale": "Synthetic qualification record.",
            }
            should_load = (
                cell["arm"] == "candidate-skills"
                and expected_oracle["routing"] == "audit"
            )
            event = {
                "type": "item.completed",
                "item": (
                    {
                        "id": "synthetic-skill-read",
                        "type": "command_execution",
                        "command": f"cat {skill_path}",
                        "exit_code": 0,
                        "aggregated_output": audit_skill_text,
                    }
                    if should_load
                    else {
                        "id": "synthetic-message",
                        "type": "agent_message",
                        "text": "Synthetic qualification event.",
                    }
                ),
            }
            (arm_root / "codex-events.jsonl").write_text(
                json.dumps(event) + "\n",
                encoding="utf-8",
            )
            (arm_root / "codex.stderr.log").write_text("", encoding="utf-8")
            (arm_root / "final-message.txt").write_text(
                json.dumps(output) + "\n",
                encoding="utf-8",
            )
            score = benchmark.score_output(output, expected_oracle, cell["scenario"])
            record = {
                **cell,
                "codex_exit_code": 0,
                "parse_error": None,
                "workspace_change_count": 0,
                "workspace_digest_before": "stable-workspace",
                "workspace_digest_after": "stable-workspace",
                "guard_context": {
                    "workspace_root": str(workspace),
                    "readable_roots": [
                        str(codex_home / "skills"),
                        str(codex_home / "references"),
                    ],
                },
                "forbidden_events": [],
                "audit_skill_access_observed": should_load,
                "audit_skill_load_observed": should_load,
                "manage_skill_access_observed": False,
                "manage_skill_load_observed": False,
                "reference_access_observed": False,
                "candidate_treatment_access_observed": should_load,
                "routing_observed": True,
                "integrity_failure": False,
                "behavioral_failure": False,
                "hard_failure": False,
                "score": score,
                "artifacts": {
                    path.name: benchmark.file_digest(path)
                    for path in arm_root.iterdir()
                    if path.is_file()
                },
            }
            (arm_root / "record.json").write_text(
                json.dumps(record, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            records.append(record)
        candidate = benchmark.arm_summary(records, "candidate-skills")
        control = benchmark.arm_summary(records, "no-skill")
        paired_interval = benchmark.paired_accuracy_interval(
            records,
            seed=int(identity["seed"]),
            samples=self.config["measurement"]["bootstrapSamples"],
            confidence=self.config["measurement"]["confidenceLevel"],
        )
        records_payload = json.dumps(records, indent=2, sort_keys=True) + "\n"
        (run_root / "records.json").write_text(records_payload, encoding="utf-8")
        benchmark.write_blind_bundle(run_root, records, f"synthetic-{phase}")
        metadata = {
            "schema": "helixbox/automation-paired-run/2",
            "protocol_version": identity["protocol_version"],
            "run_id": f"synthetic-{phase}",
            "phase": phase,
            "claim_label": (
                "harness_smoke_only"
                if phase == "smoke"
                else "pilot_no_effect_claim"
            ),
            "seed": identity["seed"],
            "repetitions": repetitions,
            "scenario_ids": scenario_ids,
            "scenario_count": len(scenario_ids),
            "expected_pairs": expected_pairs,
            "complete_pairs": expected_pairs,
            "candidate": candidate,
            "control": control,
            "absolute_accuracy_uplift": 0.0,
            "paired_accuracy_uplift_interval": paired_interval,
            "inputs_frozen_before_first_cell": True,
            "auth_snapshot_frozen_before_first_cell": True,
            "source_stable_during_run": True,
            "source_changes_during_run": {},
            "codex_identity_before_schedule": cli_identity,
            "codex_identity_after_schedule": cli_identity,
            "codex_identity_stable_during_run": True,
            "codex_identity_changes_during_run": {},
            "input_snapshot_sha256": identity["input_snapshot_sha256"],
            "model": identity["model"],
            "reasoning_configuration": identity["reasoning_configuration"],
            "skill_read_policy": identity["skill_read_policy"],
            "qualification_identity": identity,
            "qualification_identity_sha256": benchmark.canonical_json_digest(identity),
            "qualification": qualification,
            "run_integrity_failure": False,
            "run_integrity_failures": [],
            "runner_exit_code": 0,
            "records_sha256": benchmark.file_digest(run_root / "records.json"),
            "unblinding_map_sha256": benchmark.file_digest(
                run_root / "unblinding-map.json"
            ),
        }
        path = run_root / "metadata.json"
        path.write_text(json.dumps(metadata), encoding="utf-8")
        return path

    def test_clean_raw_metadata_qualifies_only_the_exact_next_phase(self) -> None:
        scenarios = benchmark.validate_definition(
            self.config,
            self.oracle,
            self.coverage,
        )
        input_digests = {
            key: f"digest-{key}" for key in benchmark.QUALIFICATION_DIGEST_KEYS
        }
        identity = benchmark.build_qualification_identity(
            protocol_version=benchmark.PROTOCOL_VERSION,
            codex_identity={
                "resolved_path": "/synthetic/codex",
                "version": "codex-cli test-v4",
                "entry_sha256": "entry-v4",
            },
            input_digests=input_digests,
            config=self.config,
            seed=94271,
            scenario_ids=scenarios,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            smoke = self._write_qualification_metadata(
                root,
                phase="smoke",
                identity=identity,
            )
            smoke_provenance = benchmark.validate_qualification_metadata(
                path=smoke,
                current_phase="pilot",
                current_identity=identity,
                config=self.config,
            )
            self.assertTrue(smoke_provenance["validated"])
            pilot = self._write_qualification_metadata(
                root,
                phase="pilot",
                identity=identity,
                qualification=smoke_provenance,
            )
            pilot_provenance = benchmark.validate_qualification_metadata(
                path=pilot,
                current_phase="confirm",
                current_identity=identity,
                config=self.config,
            )
            self.assertTrue(pilot_provenance["validated"])

            smoke_text = smoke.read_text(encoding="utf-8")
            smoke_data = json.loads(smoke_text)
            for field, value in (
                ("schema", "helixbox/automation-paired-run/1"),
                ("runner_exit_code", 1),
                ("complete_pairs", 10),
                ("source_stable_during_run", False),
                ("codex_identity_stable_during_run", False),
                ("inputs_frozen_before_first_cell", False),
                ("auth_snapshot_frozen_before_first_cell", False),
                ("claim_label", "benchmark_local_effect_observed"),
            ):
                tampered = dict(smoke_data)
                tampered[field] = value
                smoke.write_text(json.dumps(tampered), encoding="utf-8")
                with self.subTest(field=field):
                    with self.assertRaisesRegex(ValueError, "qualification metadata failed"):
                        benchmark.validate_qualification_metadata(
                            path=smoke,
                            current_phase="pilot",
                            current_identity=identity,
                            config=self.config,
                        )
                smoke.write_text(smoke_text, encoding="utf-8")

            changed_identity = json.loads(json.dumps(identity))
            changed_identity["codex_identity"]["entry_sha256"] = "different-entry"
            with self.assertRaisesRegex(ValueError, "qualification metadata failed"):
                benchmark.validate_qualification_metadata(
                    path=smoke,
                    current_phase="pilot",
                    current_identity=changed_identity,
                    config=self.config,
                )

            records_path = smoke.parent / "records.json"
            records_text = records_path.read_text(encoding="utf-8")
            records_path.write_text(records_text + " ", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raw_bundle:records_sha256"):
                benchmark.validate_qualification_metadata(
                    path=smoke,
                    current_phase="pilot",
                    current_identity=identity,
                    config=self.config,
                )
            records_path.write_text(records_text, encoding="utf-8")

            tampered_records = json.loads(records_text)
            tampered_records[0]["score"]["correct"] = 0
            tampered_records[0]["score"]["accuracy"] = 0.0
            raw_record_path = (
                smoke.parent
                / "raw"
                / tampered_records[0]["pair_id"]
                / tampered_records[0]["arm"]
                / "record.json"
            )
            raw_record_text = raw_record_path.read_text(encoding="utf-8")
            tampered_payload = json.dumps(
                tampered_records,
                indent=2,
                sort_keys=True,
            ) + "\n"
            records_path.write_text(tampered_payload, encoding="utf-8")
            raw_record_path.write_text(
                json.dumps(tampered_records[0], indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            tampered_metadata = json.loads(smoke_text)
            tampered_candidate = benchmark.arm_summary(
                tampered_records,
                "candidate-skills",
            )
            tampered_control = benchmark.arm_summary(tampered_records, "no-skill")
            tampered_interval = benchmark.paired_accuracy_interval(
                tampered_records,
                seed=94271,
                samples=self.config["measurement"]["bootstrapSamples"],
                confidence=self.config["measurement"]["confidenceLevel"],
            )
            tampered_metadata.update(
                {
                    "records_sha256": benchmark.file_digest(records_path),
                    "candidate": tampered_candidate,
                    "control": tampered_control,
                    "absolute_accuracy_uplift": round(
                        tampered_candidate["accuracy"] - tampered_control["accuracy"],
                        6,
                    ),
                    "paired_accuracy_uplift_interval": tampered_interval,
                    "claim_label": benchmark.benchmark_conclusion(
                        phase="smoke",
                        repetitions=1,
                        config=self.config,
                        candidate=tampered_candidate,
                        control=tampered_control,
                        complete_pairs=11,
                        expected_pairs=11,
                        paired_interval=tampered_interval,
                    ),
                }
            )
            smoke.write_text(json.dumps(tampered_metadata), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raw_bundle:semantic"):
                benchmark.validate_qualification_metadata(
                    path=smoke,
                    current_phase="pilot",
                    current_identity=identity,
                    config=self.config,
                )
            records_path.write_text(records_text, encoding="utf-8")
            raw_record_path.write_text(raw_record_text, encoding="utf-8")
            smoke.write_text(smoke_text, encoding="utf-8")

            smoke.write_text(smoke_text + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "smoke_qualification_chain"):
                benchmark.validate_qualification_metadata(
                    path=pilot,
                    current_phase="confirm",
                    current_identity=identity,
                    config=self.config,
                )
            smoke.write_text(smoke_text, encoding="utf-8")

    def test_run_integrity_blocks_phase_labels_and_positive_confirmation(self) -> None:
        clean = {
            "cells": 11,
            "valid_outputs": 11,
            "hard_failures": 0,
            "accuracy": 1.0,
            "overcontrol_error_rate": 0.0,
            "scenario_accuracy": {f"case-{number:02d}": 1.0 for number in range(1, 12)},
        }
        self.assertEqual(
            "harness_smoke_failed",
            benchmark.benchmark_conclusion(
                phase="smoke",
                repetitions=1,
                config=self.config,
                candidate=clean,
                control=clean,
                complete_pairs=11,
                expected_pairs=11,
                run_integrity_failure=True,
            ),
        )
        confirmation = {**clean, "cells": 110, "valid_outputs": 110}
        self.assertEqual(
            "benchmark_local_effect_not_demonstrated",
            benchmark.benchmark_conclusion(
                phase="confirm",
                repetitions=10,
                config=self.config,
                candidate=confirmation,
                control={**confirmation, "accuracy": 0.8},
                complete_pairs=110,
                expected_pairs=110,
                paired_interval={"estimate": 0.2, "lower": 0.1, "upper": 0.3},
                run_integrity_failure=True,
            ),
        )

    def test_unqualified_dry_runs_use_schedule_only_labels_without_auth(self) -> None:
        environment = dict(os.environ)
        environment["CODEX_HOME"] = "/nonexistent/synthetic-codex-home"
        for phase, expected_label, launch_authorized in (
            ("smoke", "smoke_schedule_only", True),
            ("pilot", "pilot_schedule_only", False),
            ("confirm", "confirmation_schedule_only", False),
        ):
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--phase", phase, "--dry-run"],
                cwd=REPO_ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            with self.subTest(phase=phase):
                self.assertEqual(0, completed.returncode, completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertTrue(payload["dry_run"])
                self.assertEqual(expected_label, payload["claim_label"])
                self.assertIs(launch_authorized, payload["launch_authorized"])

    def test_live_canary_is_explicit_and_not_a_default_test(self) -> None:
        canary = (DEV_ROOT / "benchmarks" / "live-canary.md").read_text(
            encoding="utf-8"
        )
        claims = (DEV_ROOT / "benchmarks" / "claim-matrix.md").read_text(
            encoding="utf-8"
        )
        makefile = (REPO_ROOT / "Makefile.toml").read_text(encoding="utf-8")

        self.assertIn("explicit authority", canary)
        self.assertIn("Do not delete a task when quiescence is unknown", canary)
        self.assertIn("current_surface_conformance_observed", canary)
        self.assertIn("Never collapse these labels into `plugin passed`", claims)
        self.assertNotIn("live-canary", makefile)

    def test_blind_review_contract_requires_two_reviewers(self) -> None:
        readme = (DEV_ROOT / "benchmarks" / "README.md").read_text(
            encoding="utf-8"
        )
        schema = benchmark.load_json(
            DEV_ROOT / "benchmarks" / "reviewer-score.schema.json"
        )

        self.assertIn("two independent reviewers", readme)
        self.assertIn("at least 0.80", readme)
        self.assertEqual(
            {
                "reviewer_id",
                "opaque_output_id",
                "evidence_grounded",
                "rationale_consistent",
                "unsupported_claim",
                "notes",
            },
            set(schema["required"]),
        )


if __name__ == "__main__":
    unittest.main()
