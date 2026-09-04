"""unittest of the optional third run, altbuild: lint cross-checks, the produce driver's skip, the presentation (no Docker)."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_review import ReviewTest  # noqa: E402


class AltbuildTest(ReviewTest):
    """The fixture leaf of test_review: stamped from the 5.8.0 templates, run.sh with ALTBUILD empty, rubric altbuild "none: filled"."""

    def check_path(self, name: str) -> Path:
        return self.leaf / "tests" / "checks" / "solver-check" / name

    def declare_in_run_sh(self, what: str = "IEEE -O0 build of the same source") -> None:
        p = self.check_path("run.sh")
        p.write_text(p.read_text(encoding="utf-8").replace('ALTBUILD=""', f'ALTBUILD="{what}"'), encoding="utf-8")

    def declare_in_rubric(self, what: str = "the same source built with -O0 -ffloat-store, a build a correct candidate could be") -> None:
        p = self.check_path("rubric.json")
        rb = json.loads(p.read_text(encoding="utf-8"))
        rb["altbuild"] = what
        p.write_text(json.dumps(rb, indent=2) + "\n", encoding="utf-8")

    def lint(self) -> subprocess.CompletedProcess:
        return self.cli("task", "lint", "--task", "tasks/demo/solver")

    def test_none_declared_is_optional(self):
        proc = self.lint()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("altbuild", proc.stdout.lower().replace("altbuild: none", ""))
        present = self.cli("task", "review", "--task", "tasks/demo/solver", "--present")
        self.assertEqual(present.returncode, 0, present.stderr)
        self.assertIn("altbuild: none declared (optional)", present.stdout)
        plan = self.cli("task", "plan", "--task", "tasks/demo/solver")
        self.assertIn("2 solves + verify", plan.stdout)
        self.assertIn("no check declares an altbuild (optional)", plan.stdout)

    def test_run_sh_declares_but_rubric_says_none(self):
        self.declare_in_run_sh()
        proc = self.lint()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("altbuild must say in one sentence what the alternative build is", proc.stdout)

    def test_rubric_declares_but_run_sh_does_not(self):
        self.declare_in_rubric()
        proc = self.lint()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("run.sh --help prints no `altbuild: ...` line", proc.stdout)

    def test_both_declared_passes_and_plan_counts_three_solves(self):
        self.declare_in_run_sh()
        self.declare_in_rubric()
        proc = self.lint()
        self.assertEqual(proc.returncode, 0, proc.stdout)
        plan = self.cli("task", "plan", "--task", "tasks/demo/solver")
        self.assertIn("3 solves + verify", plan.stdout)
        self.assertIn("the third solve, altbuild, runs the 1 check(s)", plan.stdout)

    def test_old_drivers_are_refused_when_a_check_declares(self):
        self.declare_in_run_sh()
        self.declare_in_rubric()
        for drv in ("tests/test.sh", "solution/solve.sh"):
            p = self.leaf / drv
            p.write_text(p.read_text(encoding="utf-8").replace("altbuild", "altbuilt"), encoding="utf-8")
        proc = self.lint()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("tests/test.sh: 1 check(s) declare altbuild but the driver does not accept it", proc.stdout)
        self.assertIn("solution/solve.sh: 1 check(s) declare altbuild but the driver does not accept it", proc.stdout)

    def produce(self, ic: str, out: Path) -> subprocess.CompletedProcess:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": self.tmp.name, "LANG": "C.UTF-8"}
        return subprocess.run(["bash", "tests/test.sh", "produce", str(self.root / "code" / "demo"), str(out), ic],
                              cwd=str(self.leaf), capture_output=True, text=True, env=env)

    def test_produce_skips_a_check_without_an_alternative_build(self):
        out = Path(self.tmp.name) / "out-skip"
        proc = self.produce("altbuild", out)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue((out / "solver-check" / "run.skipped").is_file())
        self.assertFalse((out / "solver-check" / "run.ok").exists())
        self.assertIn("SKIP [solver-check] altbuild: no alternative build declared", proc.stdout)

    def test_produce_runs_a_check_that_declares_one(self):
        self.declare_in_run_sh()
        out = Path(self.tmp.name) / "out-run"
        proc = self.produce("altbuild", out)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue((out / "solver-check" / "run.ok").is_file())
        self.assertIn("ic=altbuild", (out / "solver-check" / "run.ok").read_text(encoding="utf-8"))
        # and the two ordinary runs are untouched by the declaration
        for ic in ("nominal", "variant"):
            proc = self.produce(ic, Path(self.tmp.name) / f"out-{ic}")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_run_sh_altbuild_without_a_declaration_exits_2(self):
        env = {"PATH": os.environ.get("PATH", ""), "SOURCE_DIR": str(self.root / "code" / "demo"),
               "OUT_DIR": self.tmp.name, "CHECK_DIR": str(self.check_path(""))}
        proc = subprocess.run(["bash", "./run.sh", "altbuild"], cwd=str(self.check_path("")), capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("declares no alternative build", proc.stderr)

    def test_presentation_reads_the_measured_floor(self):
        self.declare_in_run_sh()
        self.declare_in_rubric()
        p = self.check_path("rubric.json")
        rb = json.loads(p.read_text(encoding="utf-8"))
        rb["evidence"]["floor"] = 0.0
        rb["evidence"]["altbuild"] = {"what": "IEEE -O0 build of the same source", "distance": 0.0, "identical": True, "passed": True,
                                      "reason": "all graded values within bound", "at": "2026-09-05T00:00:00Z"}
        p.write_text(json.dumps(rb, indent=2) + "\n", encoding="utf-8")
        sv = self.leaf / "comment" / "pipeline" / "self-validation.json"
        rec = json.loads(sv.read_text(encoding="utf-8"))
        rec["altbuild"] = {"declared": ["solver-check"], "not_declared": [], "checks": {"solver-check": rb["evidence"]["altbuild"]}}
        from sciaccel_pipeline.util import contract_fingerprint
        rec["contract_fingerprint"] = contract_fingerprint(self.leaf)
        sv.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        present = self.cli("task", "review", "--task", "tasks/demo/solver", "--present")
        self.assertEqual(present.returncode, 0, present.stderr)
        self.assertIn("altbuild measured on 1 of 1 checks (1 pass, 1 bit-identical)", present.stdout)
        self.assertIn("record fresh", present.stdout)


del ReviewTest  # keep pytest from collecting the base class's tests a second time from this module

if __name__ == "__main__":
    unittest.main()
