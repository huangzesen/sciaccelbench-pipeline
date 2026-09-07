"""unittest of the review mode: one brief per stop, open and decided (stdlib only, no Docker)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sciaccel_pipeline import config  # noqa: E402
from sciaccel_pipeline.util import contract_fingerprint, fill  # noqa: E402

TEMPLATES = REPO / "src" / "sciaccel_pipeline" / "templates"
FILL = re.compile(r"<FILL:(?:[^<>]|<[^<>]*>)*>")
TOKENS = {"TASK": "solver", "CODEBASE": "demo", "SOURCE": "demo", "MODULE_TITLE": "The solver", "CODEBASE_TITLE": "Demo",
          "SHORT_TITLE": "Demo solver", "REPO_URL": "https://example.org/demo", "REPO_COMMIT": "0123456789abcdef", "LICENSE": "MIT",
          "LANGUAGE_FROM": "Fortran", "DOMAIN": "Fluid dynamics", "OWNER": "someone", "ARXIV": '"physics.flu-dyn"', "CPUS": "2", "MEMORY_GB": "4.0"}
MODULES = {"codebase": "demo", "shared_infrastructure": ["shared/"],
           "modules": [{"slug": "solver", "title": "The solver", "paths": ["solver/"], "entrypoints": ["run"], "expensive_path": "stepping",
                        "rationale": "one physics", "excluded": [], "hazards": []}],
           "not_packaged": [{"what": "docs", "why": "prose"}], "approval": {"modules": ["solver"], "at": "2026-09-04T00:00:00Z", "human_ref": "go"}}


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.pipe, self.root = base / "pipe", base / "root"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "scripts" / "stage-task-source.py").write_text("# stub\n", encoding="utf-8")
        (self.root / "registry").mkdir()
        (self.root / "registry" / "arxiv-categories.json").write_text(
            json.dumps({"categories": [{"code": "physics.flu-dyn", "domain": "Fluid dynamics"}]}), encoding="utf-8")
        code = self.root / "code" / "demo"
        (code / "solver").mkdir(parents=True)
        (code / "shared").mkdir()
        (code / "docs").mkdir()
        (code / "solver" / "step.f90").write_text("a\nb\nc\n", encoding="utf-8")
        (code / "shared" / "util.f90").write_text("x\ny\n", encoding="utf-8")
        (code / "docs" / "guide.md").write_text("one line\n", encoding="utf-8")
        (code / "LICENSE").write_text("MIT\n", encoding="utf-8")
        self.leaf = self.root / "tasks" / "demo" / "solver"
        self.build_leaf()
        git(self.root, "init", "-q")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def build_leaf(self):
        """A leaf stamped from the templates with every marker filled, plus a passing self-validation record."""
        for tpl in sorted(p for p in (TEMPLATES / "task").rglob("*") if p.is_file()):
            dst = self.leaf / tpl.relative_to(TEMPLATES / "task")
            dst.parent.mkdir(parents=True, exist_ok=True)
            text = fill(tpl.read_text(encoding="utf-8"), TOKENS)
            if tpl.name == "task.toml":
                text = re.sub(r'(equivalence_explanation = """\n)<FILL:.*?>\n', r"\1solver-check: pointwise; the final state; 1e-10. Because.\n", text, flags=re.S)
            text = "\n".join(ln for ln in text.splitlines() if "<FILL: append the module" not in ln) + "\n"
            text = FILL.sub("filled", text)
            dst.write_text(text, encoding="utf-8")
            if tpl.stat().st_mode & 0o111:
                dst.chmod(0o755)
        check = self.leaf / "tests" / "checks" / "solver-check"
        check.mkdir(parents=True)
        tokens = {"CHECK": "solver-check", "UPSTREAM_TEST": "code/demo/solver/step.f90", "POLICY": "pointwise", "CHAOTIC": "false"}
        for tpl in sorted((TEMPLATES / "check" / "pointwise").iterdir()):
            text = fill(tpl.read_text(encoding="utf-8"), tokens)
            if tpl.name == "run.sh":
                text = text.replace('knob SAB_STEPS "<FILL: default>" "<FILL: what it scales and how, e.g. time steps; runtime scales linearly>"',
                                    'knob SAB_STEPS "10" "time steps"')
            if tpl.name == "rubric.json":
                text = text.replace('"atol": null', '"atol": 1e-10').replace('"expected_runtime_s": null', '"expected_runtime_s": 5')
                text = text.replace('"self_validation_spread": null', '"self_validation_spread": 1e-13').replace('"floor": null', '"floor": 2e-14')
            text = FILL.sub("filled", text)
            (check / tpl.name).write_text(text, encoding="utf-8")
            if tpl.stat().st_mode & 0o111:
                (check / tpl.name).chmod(0o755)
        (check / "check.json").write_text(json.dumps({"labels": ["acceleration"]}), encoding="utf-8")
        for ic in ("nominal", "variant"):
            (check / "ic" / ic).mkdir(parents=True)
            (check / "ic" / ic / "input.txt").write_text(f"eps = 1.0{'0' if ic == 'nominal' else '1'}\n", encoding="utf-8")
        pipeline = self.leaf / "comment" / "pipeline"
        pipeline.mkdir(parents=True, exist_ok=True)
        (pipeline / "test-survey.json").write_text(json.dumps({"module": "solver", "tests": [{"suitable": True}] * 5}), encoding="utf-8")
        record = {"task": "solver", "contract_fingerprint": contract_fingerprint(self.leaf), "started_at": "2026-09-04T10:00:00Z",
                  "finished_at": "2026-09-04T10:20:00Z", "result": "passed", "host": {"hostname": "box", "arch": "x86_64", "docker_cpus": 8},
                  "consent": {"where": "local", "at": "2026-09-04T09:00:00Z", "consented_on": "box"},
                  "reward": {"reward": 1.0, "passed": 1, "total": 1, "identical_checks": [],
                             "checks": {"solver-check": {"passed": True, "identical": False, "distance": 1e-13}}},
                  "solves": [{"check_seconds": {"solver-check": 21.0}, "build_seconds": {"solver-check": 1.0}}],
                  "check_run_seconds_nominal": {"solver-check": 20.0}, "suite_seconds_nominal": 20.0, "build_seconds_nominal": 1.0,
                  "budget_s": 900.0, "budget": "within", "warnings": [], "problems": []}
        (pipeline / "self-validation.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONPATH=str(REPO / "src"), SAB_PIPE_DIR=str(self.pipe), SAB_ROOT=str(self.root))
        return subprocess.run([sys.executable, "-m", "sciaccel_pipeline", *args], capture_output=True, text=True, cwd=str(self.root), env=env)

    def test_task_brief_then_decision(self):
        proc = self.cli("review", "task", "--task", "tasks/demo/solver", "--base", "HEAD")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertIn("# Task review: tasks/demo/solver at ", out)
        self.assertIn("tree unchanged since the head: yes", out)
        self.assertIn("| solver-check (step.f90) | pointwise; acceleration |", out)
        self.assertIn("**Lint.** 0 error(s), 1 warning(s)", out)
        self.assertIn("warn  1 check(s): fewer than 4 is thin", out)
        self.assertIn("**validate-harbor.** PASS", out)
        self.assertIn("**Record.** passed at 2026-09-04T10:20:00Z, fresh", out)
        self.assertIn("run time 20 s against declared 5 s", out)
        self.assertIn("GATHER, in this order", out)
        self.assertIn("PRESENT to the human, in this shape and this order", out)
        self.assertIn("ASK for two decisions, separately.", out)
        self.assertIn("**Coverage.** 1 checks: 1 from an official test or example, 0 custom; the skill's aim is at least 4, about 30, fewer than 50.", out)
        self.assertIn("survey: 5 official tests recorded, 5 suitable, 0 not; 0 suitable test(s) whose proposed check is absent from the leaf; 5 suitable test(s) with no proposed check; 1 check(s) the survey did not propose: solver-check.", out)
        self.assertIn("Speak plain English throughout.", out)
        self.assertTrue(out.startswith("REVIEW  tasks/demo/solver  (STOP 6, the task PR)"), out[:120])
        self.assertIn("How this review goes, and what is asked of you.", out)
        self.assertIn("Decide the review: approve, request changes, or redesign the checks", out)
        self.assertIn('title prefix\n  "review:"', out)
        rec = self.pipe / "demo" / "reviewer" / "task-solver.json"
        self.assertTrue(rec.is_file())
        self.assertTrue((self.pipe / "demo" / "reviewer" / "task-solver.md").is_file())
        self.assertEqual(len(json.loads(rec.read_text())["runs"]), 1)

        proc = self.cli("review", "review", "task", "--task", "tasks/demo/solver", "--done")
        self.assertEqual(proc.returncode, 2)
        proc = self.cli("review", "task", "--task", "tasks/demo/solver", "--done")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("--done needs --human-ref", proc.stderr)

        presented = Path(self.tmp.name) / "presented.md"
        presented.write_text("what I told the human\n", encoding="utf-8")
        proc = self.cli("review", "task", "--task", "tasks/demo/solver", "--done", "--human-ref", "approve, merge it", "--presented", str(presented))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('decision recorded for task tasks/demo/solver', proc.stdout)
        self.assertIn("rerun: none approved (no --rerun-ref); nothing runs", proc.stdout)
        doc = json.loads(rec.read_text())
        self.assertEqual(doc["decision"]["human_ref"], "approve, merge it")
        self.assertIsNone(doc["decision"]["rerun"])
        self.assertTrue(Path(doc["decision"]["presented"]).is_file())
        proc = self.cli("review", "task", "--task", "tasks/demo/solver", "--done", "--human-ref", "approve, merge it",
                        "--rerun-ref", "yes, rerun on the worker")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('rerun: approved in the human\'s words: "yes, rerun on the worker"', proc.stdout)
        doc = json.loads(rec.read_text())
        self.assertEqual(doc["decision"]["rerun"]["human_ref"], "yes, rerun on the worker")

        proc = self.cli("review", "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("| task tasks/demo/solver |", proc.stdout)
        self.assertIn("| decided ", proc.stdout)
        self.assertIn("approve, merge it | rerun: yes, rerun on the worker", proc.stdout)

    def test_codebase_brief_measures_the_cut(self):
        modules = Path(self.tmp.name) / "modules.json"
        modules.write_text(json.dumps(MODULES), encoding="utf-8")
        proc = self.cli("review", "codebase", "--codebase", "demo", "--modules", str(modules), "--base", "HEAD")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertIn("# Codebase review: demo at ", out)
        self.assertIn("**Tree.** 4 files, 7 lines", out)
        self.assertIn("licence at the root: `LICENSE`", out)
        self.assertIn("**Cut.** 1 module(s) from `", out)
        self.assertIn('approved [\'solver\'] at 2026-09-04T00:00:00Z: "go"', out)
        self.assertIn("| `solver` | The solver | `solver/` | 1 | 3 |", out)
        self.assertIn("| shared infrastructure | | `shared/` | 1 | 2 |", out)
        self.assertIn("| unowned | | `docs` | 1 | 1 |", out)
        self.assertIn("| docs | prose |", out)
        self.assertIn("GATHER, in this order", out)
        self.assertIn("The review decision: merge, send back, or change the cut.", out)
        self.assertTrue(out.startswith("REVIEW  demo  (STOP 2, the source PR)"), out[:120])
        self.assertIn("Decide the review: merge, send back, or change the cut.", out)
        self.assertTrue((self.pipe / "demo" / "reviewer" / "codebase-demo.json").is_file())

    def test_codebase_upstream_diff(self):
        upstream = Path(self.tmp.name) / "upstream"
        (upstream / "solver").mkdir(parents=True)
        (upstream / "solver" / "step.f90").write_text("a\nb\nc\n", encoding="utf-8")
        (upstream / "solver" / "extra.f90").write_text("z\n", encoding="utf-8")
        proc = self.cli("review", "codebase", "--codebase", "demo", "--base", "HEAD", "--upstream", str(upstream))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("vendored tree differs: 3 added, 1 removed, 0 modified", proc.stdout)
        self.assertIn("removed `solver/extra.f90`", proc.stdout)
        self.assertIn("**Cut.** no module cut on this machine", proc.stdout)

    def test_status_without_reviews(self):
        proc = self.cli("review", "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("no reviews under", proc.stdout)

    def test_revision_matches_the_skill(self):
        text = (REPO / "skill" / "package-sciaccel-task" / "SKILL.md").read_text(encoding="utf-8")
        version = re.search(r"^version:\s*(\S+)", text, re.M).group(1)
        self.assertEqual(version, config.REVISION)


if __name__ == "__main__":
    unittest.main()
