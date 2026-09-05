"""unittest of the stamped produce driver on a check that dies before it prints a build line (5.10.1, no Docker)."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_review import ReviewTest  # noqa: E402


class DriverFailureTest(ReviewTest):
    """The fixture leaf plus a second check whose run.sh exits 1 before any output: the driver must record it and go on."""

    def add_dying_check(self, name: str = "dying-check") -> Path:
        src = self.leaf / "tests" / "checks" / "solver-check"
        dst = self.leaf / "tests" / "checks" / name
        dst.mkdir()
        for p in src.iterdir():
            if p.is_dir():
                subprocess.run(["cp", "-R", str(p), str(dst / p.name)], check=True)
            else:
                (dst / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        run = dst / "run.sh"
        run.write_text("#!/usr/bin/env bash\nset -euo pipefail\n"
                       "if [ \"${1:-}\" = --help ]; then exit 0; fi\n"
                       "exit 1  # dies before any SAB_BUILD_SECONDS line, like a failed configure step\n", encoding="utf-8")
        run.chmod(0o755)
        return dst

    def make_solver_check_write_its_file(self) -> None:
        """The fixture's run.sh is a stub; give it the one graded file its rubric names (three f64 values)."""
        run = self.leaf / "tests" / "checks" / "solver-check" / "run.sh"
        run.write_text(run.read_text(encoding="utf-8") + "\npython3 -c 'import os, struct; open(os.path.join(os.environ[\"OUT_DIR\"], \"filled\"), \"wb\").write(struct.pack(\"<3d\", 1.0, 2.0, 3.0))'\n", encoding="utf-8")

    def produce(self, ic: str, out: Path) -> subprocess.CompletedProcess:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": self.tmp.name, "LANG": "C.UTF-8"}
        return subprocess.run(["bash", "tests/test.sh", "produce", str(self.root / "code" / "demo"), str(out), ic],
                              cwd=str(self.leaf), capture_output=True, text=True, env=env)

    def verify(self, reference: Path, candidate: Path, reward: Path) -> subprocess.CompletedProcess:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": self.tmp.name, "LANG": "C.UTF-8",
               "HARBOR_REFERENCE_DIR": str(reference), "HARBOR_CANDIDATE_DIR": str(candidate), "HARBOR_REWARD_FILE": str(reward)}
        return subprocess.run(["bash", "tests/test.sh"], cwd=str(self.leaf), capture_output=True, text=True, env=env)

    def test_a_check_dying_before_its_build_line_is_recorded_and_the_suite_continues(self):
        self.add_dying_check()
        out = Path(self.tmp.name) / "out-dying"
        proc = self.produce("nominal", out)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertTrue((out / "dying-check" / "run.failed").is_file(), proc.stdout + proc.stderr)
        self.assertIn("build_seconds=0", (out / "dying-check" / "run.failed").read_text(encoding="utf-8"))
        # the loop went on: the healthy check after it in sort order still ran
        self.assertTrue((out / "solver-check" / "run.ok").is_file(), proc.stdout + proc.stderr)
        self.assertIn("FAILED [dying-check]", proc.stderr)
        self.assertIn("OK [solver-check]", proc.stdout)
        self.assertIn("produce: 1 of 2 checks failed: dying-check", proc.stderr)

    def test_the_verifier_still_writes_a_reward_file_for_the_partial_suite(self):
        self.make_solver_check_write_its_file()
        self.add_dying_check()
        ref = Path(self.tmp.name) / "ref"
        cand = Path(self.tmp.name) / "cand"
        # reference: a healthy tree (the dying check has no outputs on either side and fails)
        self.produce("nominal", ref)
        self.produce("nominal", cand)
        reward = Path(self.tmp.name) / "reward.json"
        proc = self.verify(ref, cand, reward)
        self.assertTrue(reward.is_file(), proc.stdout + proc.stderr)
        import json
        doc = json.loads(reward.read_text(encoding="utf-8"))
        self.assertEqual(doc["total"], 2)
        self.assertEqual(doc["passed"], 1)
        self.assertAlmostEqual(doc["reward"], 0.5)
        self.assertIn("dying-check", doc["checks"])
        self.assertFalse(doc["checks"]["dying-check"]["passed"])


if __name__ == "__main__":
    unittest.main()
