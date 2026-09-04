"""unittest of the state flow: init, propose, approve, refusal gates (stdlib only, no Docker)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

MODULES = {
    "codebase": "demo",
    "shared_infrastructure": ["shared/"],
    "modules": [{"slug": "solver", "title": "The solver", "paths": ["solver/"],
                 "entrypoints": ["run"], "expensive_path": "time stepping",
                 "rationale": "one physics", "excluded": [], "hazards": []}],
    "not_packaged": [],
}


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.pipe = base / "pipe"
        self.root = base / "root"
        self.code = base / "checkout"
        (self.code / "solver").mkdir(parents=True)
        (self.code / "shared").mkdir()
        (self.root / "registry").mkdir(parents=True)
        (self.root / "registry" / "arxiv-categories.json").write_text(
            json.dumps({"categories": [{"code": "physics.flu-dyn", "domain": "Fluid dynamics"}]}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONPATH=str(REPO / "src"),
                   SAB_PIPE_DIR=str(self.pipe), SAB_ROOT=str(self.root))
        return subprocess.run([sys.executable, "-m", "sciaccel_pipeline", *args],
                             capture_output=True, text=True, cwd=str(self.root), env=env)

    def test_init_propose_approve_and_gates(self):
        proc = self.cli("codebase", "init", "--codebase", "demo", "--code-path", str(self.code),
                        "--title", "Demo", "--arxiv", "physics.flu-dyn")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Show this briefing to the human in full before reading any code.", proc.stdout)
        state = json.loads((self.pipe / "demo" / "codebase.json").read_text())
        self.assertEqual(state["domain"], "Fluid dynamics")

        proc = self.cli("codebase", "propose-modules", "--codebase", "demo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("STEP 1", proc.stdout)

        (self.pipe / "demo" / "modules.json").write_text(json.dumps(MODULES), encoding="utf-8")
        proc = self.cli("codebase", "propose-modules", "--codebase", "demo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("STOP 1: show this table and overview.md to the human.", proc.stdout)

        proc = self.cli("codebase", "approve-modules", "--codebase", "demo", "--human-ref", "go ahead")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("approved 1 module(s): ['solver']", proc.stdout)
        self.assertTrue((self.pipe / "demo" / "codebase-metadata.json").is_file())

        # Step 1.5 refusal: survey-tests refuses while the source PR is unmerged.
        proc = self.cli("codebase", "survey-tests", "--codebase", "demo")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("STEP 1.5", proc.stdout)
        self.assertIn("refusing:", proc.stderr)

        # scaffold refuses an unapproved module outright.
        proc = self.cli("task", "scaffold", "--codebase", "demo", "--module", "other")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not approved", proc.stderr)

        # The bypass without the human's words refuses too.
        proc = self.cli("codebase", "survey-tests", "--codebase", "demo", "--allow-unmerged-source")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("--allow-unmerged-source needs --human-ref", proc.stderr)

    def test_status_without_state(self):
        proc = self.cli("status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("no codebases under", proc.stdout)

    def test_report_writes_three_artifacts_and_presents(self):
        self.cli("codebase", "init", "--codebase", "demo", "--code-path", str(self.code))
        (self.pipe / "demo" / "modules.json").write_text(json.dumps(MODULES), encoding="utf-8")
        self.cli("codebase", "approve-modules", "--codebase", "demo", "--human-ref", "yes")
        proc = self.cli("codebase", "report", "--codebase", "demo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PRESENT TO THE HUMAN NOW", proc.stdout)
        out = self.root / "codebase-reports" / "demo"
        for name in ("codebase-metadata.json", "codebase-metadata.html", "codebase-metadata.md"):
            self.assertTrue((out / name).is_file(), name)
        doc = json.loads((out / "codebase-metadata.json").read_text())
        self.assertTrue(doc["informational"] and doc["non_blocking"])
        self.assertTrue(doc["classification_and_gaps"]["reconciliation"]["reconciliation_ok"])


if __name__ == "__main__":
    unittest.main()
