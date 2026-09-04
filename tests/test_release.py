"""unittest of the landing tools: the generated marker, `vendor_sync.py status`, and tools/release.py."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPORTER = REPO / "tools" / "export_scienceaccelbench.py"
RELEASE = REPO / "tools" / "release.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))


def py(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return run([sys.executable, *cmd], cwd)


def head_sha() -> str:
    return run(["git", "rev-parse", "HEAD"], REPO).stdout.strip()


class LandingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name) / "bench"
        (self.dest / "skills").mkdir(parents=True)
        self.skill = self.dest / "skills" / "package-sciaccel-task"
        self.sync = self.skill / "scripts" / "vendor_sync.py"

    def tearDown(self):
        self.tmp.cleanup()

    def git_init_dest(self):
        for cmd in (["git", "init", "-q", "-b", "main"], ["git", "config", "user.email", "t@example"],
                    ["git", "config", "user.name", "t"], ["git", "add", "-A"],
                    ["git", "commit", "-q", "--allow-empty", "-m", "base"]):
            self.assertEqual(run(cmd, self.dest).returncode, 0)

    def test_marker_readme_is_generated_and_owned(self):
        self.assertEqual(py([str(EXPORTER), "--dest", str(self.dest)], REPO).returncode, 0)
        text = (self.skill / "README.md").read_text(encoding="utf-8")
        self.assertIn("managed by sciaccelbench-pipeline", text)
        self.assertIn("Do not edit these files", text)
        self.assertIn("https://github.com/aitofound/sciaccelbench-pipeline", text)
        (self.skill / "README.md").write_text(text + "\nlocal note\n", encoding="utf-8")
        proc = py([str(self.sync), "verify"], self.dest)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("mutated: README.md", proc.stdout)

    def test_status_behind_then_in_sync(self):
        self.assertEqual(py([str(EXPORTER), "--dest", str(self.dest)], REPO).returncode, 0)
        proc = py([str(self.sync), "status", "--canonical", str(REPO), "--ref", "HEAD"], self.dest)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("BEHIND", proc.stdout)
        self.assertEqual(py([str(EXPORTER), "--dest", str(self.dest), "--revision", head_sha()], REPO).returncode, 0)
        proc = py([str(self.sync), "status", "--canonical", str(REPO), "--ref", "HEAD"], self.dest)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("IN SYNC", proc.stdout)
        proc = py([str(self.sync), "status", "--canonical", str(self.dest)], self.dest)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("UNKNOWN", proc.stdout)

    def test_release_records_head_and_prints_landing_commands(self):
        self.git_init_dest()
        if run(["git", "status", "--porcelain"], REPO).stdout.strip():
            self.skipTest("release refuses a dirty canonical tree; run from a clean checkout")
        proc = py([str(RELEASE), "--dest", str(self.dest), "--allow-unpushed"], REPO)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(f"canonical {head_sha()[:12]}", proc.stdout)
        self.assertIn("vendor_sync: OK", proc.stdout)
        self.assertIn("generated changes on the benchmark side", proc.stdout)
        self.assertIn("git -C", proc.stdout)
        self.assertIn(f"sync/pipeline-{head_sha()[:7]}", proc.stdout)
        # Nothing was committed or branched without --pr.
        self.assertEqual(run(["git", "rev-parse", "--abbrev-ref", "HEAD"], self.dest).stdout.strip(), "main")
        self.assertTrue(run(["git", "status", "--porcelain"], self.dest).stdout.strip())
        # A second release from the same commit, on a committed tree, reports in sync.
        for cmd in (["git", "add", "-A"], ["git", "commit", "-q", "-m", "sync"]):
            self.assertEqual(run(cmd, self.dest).returncode, 0)
        proc = py([str(RELEASE), "--dest", str(self.dest), "--allow-unpushed"], REPO)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("already in sync", proc.stdout)

    def test_release_refuses_dirty_benchmark_boundary(self):
        self.git_init_dest()
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("x", encoding="utf-8")
        proc = py([str(RELEASE), "--dest", str(self.dest), "--allow-unpushed"], REPO)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("uncommitted changes", proc.stderr)


if __name__ == "__main__":
    unittest.main()
