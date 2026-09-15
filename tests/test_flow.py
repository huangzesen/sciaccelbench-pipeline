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
    "shared_infrastructure": [],
    "modules": [{"slug": "demo", "title": "The whole codebase", "paths": ["."],
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
        # The single-module default records itself: no STOP 1, no human words needed.
        self.assertIn("Single-module default recorded", proc.stdout)
        self.assertNotIn("STOP 1", proc.stdout.split("Single-module default recorded")[0])
        mdoc = json.loads((self.pipe / "demo" / "modules.json").read_text())
        self.assertEqual(mdoc["approval"]["modules"], ["demo"])
        self.assertIn("single-module default", mdoc["approval"]["human_ref"])
        self.assertTrue((self.pipe / "demo" / "codebase-metadata.json").is_file())

        # A human approval may still be recorded on top of the default.
        proc = self.cli("codebase", "approve-modules", "--codebase", "demo", "--human-ref", "go ahead")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("approved 1 module(s): ['demo']", proc.stdout)

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

    def test_whole_codebase_prompt_survey_and_scaffold(self):
        source = self.root / "code" / "demo"
        (source / "examples").mkdir(parents=True)
        (source / "examples" / "one.txt").write_text("official example fixture\n")
        (source / "sibling").mkdir()
        (source / "sibling" / "source.txt").write_text("whole-root sentinel\n")
        proc = self.cli("codebase", "init", "--codebase", "demo", "--code-path", str(source),
                        "--repo-url", "https://example.org/demo", "--pin", "0" * 40,
                        "--license", "MIT", "--language", "Python", "--owner", "fixture",
                        "--arxiv", "physics.flu-dyn")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("one whole-codebase module", proc.stdout)
        self.assertIn('"slug": "demo"', proc.stdout)
        self.assertIn('"paths": ["."]', proc.stdout)
        self.assertIn("different physics", proc.stdout)
        self.assertIn("not a reason to split", proc.stdout)
        self.assertIn("naming exception in rationale", proc.stdout)
        (self.pipe / "demo" / "modules.json").write_text(json.dumps(MODULES))
        proc = self.cli("codebase", "propose-modules", "--codebase", "demo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = self.cli("codebase", "approve-modules", "--codebase", "demo", "--human-ref", "fixture approval")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        bypass = ("--allow-unmerged-source", "--human-ref", "fixture bypass")
        proc = self.cli("codebase", "survey-tests", "--codebase", "demo", *bypass)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("no preset check-count target", proc.stdout)
        self.assertIn("non-exhaustiveness alone is not a defect", proc.stdout)
        self.assertNotRegex(proc.stdout, r"(?i)10\s*[-–]\s*30|at least four|about thirty|fewer than fifty")
        test = {"id": "one", "module": "demo", "path": "examples/one.txt", "policy": "pointwise",
                "chaotic": False, "exercises": "whole-codebase fixture", "why": "one complete official example",
                "resources": {"cpus": 1, "memory_gb": 1, "mpi_ranks": 1}, "upstream_runtime_s": 1,
                "runtime_measured": True, "suitable": True, "proposed_check": "one"}
        (self.pipe / "demo" / "tests.json").write_text(json.dumps(
            {"codebase": "demo", "how_tests_are_run": "fixture only", "tests": [test]}))
        proc = self.cli("codebase", "survey-tests", "--codebase", "demo", *bypass)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("THIN", proc.stdout)
        self.assertIn("--module demo", proc.stdout)
        proc = self.cli("task", "scaffold", "--codebase", "demo", "--module", "demo", *bypass)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        leaf = self.root / "tasks" / "demo" / "demo"
        self.assertTrue((leaf / "task.toml").is_file())
        module = json.loads((leaf / "comment" / "pipeline" / "module.json").read_text())["module"]
        self.assertEqual(module["slug"], "demo")
        self.assertEqual(module["paths"], ["."])
        for dockerfile in ("environment/Dockerfile", "tests/Dockerfile"):
            self.assertIn("COPY code/demo/ /workspace/code/", (leaf / dockerfile).read_text())
        self.assertEqual((source / "sibling" / "source.txt").read_text(), "whole-root sentinel\n")

    def test_legacy_slug_and_real_multi_module_shapes_stay_compatible(self):
        self.cli("codebase", "init", "--codebase", "demo", "--code-path", str(self.code))
        # Historical subsystem identity remains accepted, not relabeled as whole-codebase.
        legacy = json.loads(json.dumps(MODULES))
        legacy["modules"][0].update(slug="solver", paths=["solver/"], rationale="legacy approved identity")
        multiple = json.loads(json.dumps(legacy))
        second = dict(multiple["modules"][0], slug="other-physics", paths=["shared/"],
                      rationale="independent equations and scientific I/O")
        multiple["modules"].append(second)
        for proposal in (legacy, multiple):
            (self.pipe / "demo" / "modules.json").write_text(json.dumps(proposal))
            proc = self.cli("codebase", "propose-modules", "--codebase", "demo")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            # Neither a subsystem slug nor a multi-module cut is the default: both stay a human stop.
            self.assertIn("STOP 1", proc.stdout)
            self.assertNotIn("Single-module default recorded", proc.stdout)
            self.assertNotIn("approval", json.loads((self.pipe / "demo" / "modules.json").read_text()))

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
