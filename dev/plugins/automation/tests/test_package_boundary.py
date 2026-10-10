"""Verify the migrated runtime package boundary and release identity."""
import json
from fnmatch import fnmatch
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]

class PackageBoundaryTests(unittest.TestCase):
    def test_runtime_selection_contains_only_installed_assets(self):
        runtime = ROOT / "plugins/automation"
        manifest = json.loads((runtime / ".codex-plugin/plugin.json").read_text())
        files = set()
        for path in runtime.rglob("*"):
            self.assertFalse(path.is_symlink(), str(path))
            if path.is_file():
                files.add(path.relative_to(runtime).as_posix())
        selected = {name for name in files if any(fnmatch(name, pattern)
                    for pattern in manifest["package"]["include"])}
        self.assertEqual(files, selected)
        self.assertEqual({name.split("/")[0] for name in files},
                         {".codex-plugin", "references", "scripts", "skills"})
        self.assertTrue(all(not name.endswith(".pyc") for name in files))

    def test_marketplace_versions_and_local_sources_match(self):
        catalog = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        version = (ROOT / "VERSION").read_text().strip()
        for entry in catalog["plugins"]:
            runtime = ROOT / entry["source"]["path"]
            manifest = json.loads((runtime / ".codex-plugin/plugin.json").read_text())
            self.assertEqual(entry["name"], manifest["name"])
            self.assertEqual(version, manifest["version"])
