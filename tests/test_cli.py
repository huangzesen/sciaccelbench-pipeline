"""unittest smoke of the CLI surface via subprocess (stdlib only)."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    if env:
        full_env.update(env)
    return subprocess.run([sys.executable, "-m", "sciaccel_pipeline", *args],
                         capture_output=True, text=True, cwd=str(cwd or REPO), env=full_env)


class HelpTreeTest(unittest.TestCase):
    def test_top_level_lists_all_modes(self):
        proc = run_cli("--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("{codebase,task,review,brief,status,validate-harbor}", proc.stdout)
        self.assertIn("sab: the ScienceAccelBench packaging CLI (one tool, three modes).", proc.stdout)

    def test_codebase_subcommands(self):
        proc = run_cli("codebase", "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("{init,propose-modules,approve-modules,report,source-merged,survey-tests}", proc.stdout)

    def test_task_subcommands(self):
        proc = run_cli("task", "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("{scaffold,add-check,lint,selfcheck,build,plan,consent,review}", proc.stdout)

    def test_review_subcommands(self):
        proc = run_cli("review", "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("{codebase,task,status}", proc.stdout)

    def test_identity_help_names_whole_codebase_default(self):
        init = run_cli("codebase", "init", "--help")
        self.assertEqual(init.returncode, 0, init.stderr)
        self.assertIn("canonical codebase name", init.stdout)
        self.assertIn("whole codebase source root", init.stdout)
        scaffold = run_cli("task", "scaffold", "--help")
        self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
        self.assertIn("whole-codebase module", scaffold.stdout)
        self.assertNotRegex(init.stdout + scaffold.stdout, r"(?i)10\s*[-–]\s*30|about thirty|fewer than fifty")

    def test_missing_mode_fails(self):
        proc = run_cli()
        self.assertEqual(proc.returncode, 2)

    def test_validate_harbor_reports_missing_dir(self):
        proc = run_cli("validate-harbor", "--all", "does-not-exist")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("tasks directory does not exist", proc.stdout)


class BriefTest(unittest.TestCase):
    def test_generic_brief_prints_duty_line(self):
        proc = run_cli("brief")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Show this to the human in full before reading any code", proc.stdout)
        self.assertIn("(generic; no codebase registered yet)", proc.stdout)


if __name__ == "__main__":
    unittest.main()
